import discord
from discord.ext import commands
import logging
import asyncio
import sys
import json
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('MusicBot')

# Import YTDLSource with error handling
try:
    from lib.YTDLSource import YTDLSource
    logger.info("Successfully imported YTDLSource")
except ImportError as e:
    logger.error(f"Failed to import YTDLSource: {e}")
    sys.exit(1)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.current_channels = {}
        # Use absolute path for stats file in project root
        # Get the directory where this file is located (cogs/)
        cogs_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(cogs_dir)  # Go up one level from cogs/ to project root
        self.stats_file = os.path.join(project_root, 'play_stats.json')
        
        # Verify the project root directory exists and is writable
        if not os.path.isdir(project_root):
            logger.error(f"Project root directory does not exist: {project_root}")
        elif not os.access(project_root, os.W_OK):
            logger.warning(f"Project root directory is not writable: {project_root}. Stats may not save correctly.")
        else:
            logger.info(f"Music cog initialized. Stats file: {self.stats_file}")
    
    def _load_stats(self):
        """Load play statistics from JSON file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    logger.debug(f"Loaded stats from {self.stats_file}")
                    return stats
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing stats file (corrupted?): {e}. Creating backup and starting fresh.")
                # Backup corrupted file
                backup_file = self.stats_file + '.corrupted'
                try:
                    os.rename(self.stats_file, backup_file)
                    logger.info(f"Backed up corrupted stats to {backup_file}")
                except:
                    pass
                return {}
            except IOError as e:
                logger.error(f"Error reading stats file: {e}")
                return {}
        return {}
    
    def _save_stats(self, stats):
        """Save play statistics to JSON file with atomic write"""
        try:
            # Use atomic write: write to temp file first, then rename
            temp_file = self.stats_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic rename (works on Unix and Windows)
            os.replace(temp_file, self.stats_file)
            logger.debug(f"Saved stats to {self.stats_file}")
        except IOError as e:
            logger.error(f"Error saving stats to {self.stats_file}: {e}", exc_info=True)
            # Try to clean up temp file if it exists
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def _track_play(self, channel_id, track_title):
        """Track a play for a specific channel and track"""
        stats = self._load_stats()
        channel_id_str = str(channel_id)
        
        if channel_id_str not in stats:
            stats[channel_id_str] = {}
        
        if track_title not in stats[channel_id_str]:
            stats[channel_id_str][track_title] = 0
        
        stats[channel_id_str][track_title] += 1
        self._save_stats(stats)
        logger.debug(f"Tracked play: {track_title} in channel {channel_id_str}")

    def get_voice_client(self, guild_id):
        """Get voice client for specific guild"""
        vc = self.voice_clients.get(guild_id)
        if vc:
            logger.debug(f"Retrieved voice client for guild {guild_id}: connected={vc.is_connected()}")
        return vc

    def set_voice_client(self, guild_id, voice_client):
        """Set voice client for specific guild"""
        self.voice_clients[guild_id] = voice_client
        logger.info(f"Set voice client for guild {guild_id}")

    def remove_voice_client(self, guild_id):
        """Remove voice client for specific guild"""
        if guild_id in self.voice_clients:
            del self.voice_clients[guild_id]
            logger.info(f"Removed voice client for guild {guild_id}")
        if guild_id in self.current_channels:
            del self.current_channels[guild_id]
            logger.info(f"Removed current channel for guild {guild_id}")

    async def clear_all_voice_connections(self):
        """Disconnect from all voice channels and clear state aggressively"""
        logger.info("Clearing all voice connections (aggressive mode)")
        disconnected_count = 0
        
        # First, disconnect all tracked voice clients
        for guild_id, voice_client in list(self.voice_clients.items()):
            try:
                if voice_client:
                    try:
                        await voice_client.disconnect(force=True)
                        disconnected_count += 1
                        logger.info(f"Disconnected tracked voice client in guild {guild_id}")
                    except Exception as e:
                        logger.warning(f"Error disconnecting tracked client for guild {guild_id}: {e}")
            except Exception as e:
                logger.error(f"Error with voice client for guild {guild_id}: {str(e)}", exc_info=True)
            finally:
                self.remove_voice_client(guild_id)
        
        # Second, check all guilds the bot is in and disconnect from any voice channels
        # This catches cases where the bot is in a channel but not tracked in voice_clients
        for guild in self.bot.guilds:
            try:
                bot_voice_state = guild.me.voice
                if bot_voice_state and bot_voice_state.channel:
                    # Bot is in a voice channel, force disconnect
                    vc = guild.voice_client
                    if vc:
                        try:
                            await vc.disconnect(force=True)
                            if guild.id not in self.voice_clients:
                                disconnected_count += 1
                            logger.info(f"Force disconnected from voice channel in guild {guild.name} (id: {guild.id})")
                        except Exception as e:
                            logger.warning(f"Error force disconnecting from guild {guild.name}: {e}")
                    # Clean up tracking even if disconnect failed
                    self.remove_voice_client(guild.id)
            except Exception as e:
                logger.error(f"Error checking/clearing voice state for guild {guild.name}: {e}")
        
        # Small delay to let disconnects settle
        await asyncio.sleep(0.5)
        
        logger.info(f"Cleared {disconnected_count} voice connection(s)")
        return disconnected_count

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Monitor voice state changes and auto-disconnect when alone"""
        # Handle bot's own voice state changes
        if member == self.bot.user:
            logger.info(f"Bot voice state changed - Before: {before.channel}, After: {after.channel}")
            if before.channel and not after.channel:
                logger.warning(f"Bot was disconnected from voice channel: {before.channel.name}")
                # Clean up our tracking
                guild_id = before.channel.guild.id
                if guild_id in self.voice_clients:
                    logger.info(f"Cleaning up voice client tracking for guild {guild_id}")
                    self.remove_voice_client(guild_id)
            return
        
        # Handle other members leaving channels the bot is in
        # Only check when someone leaves a channel (not when they join or switch)
        if before.channel is None:
            return  # Member didn't leave any channel
        
        voice_client = self.get_voice_client(member.guild.id)
        if voice_client and voice_client.is_connected():
            channel = voice_client.channel
            # Only check if they left the channel the bot is in
            if channel and before.channel.id == channel.id:
                # Count members in channel (excluding bots)
                members_in_channel = [m for m in channel.members if not m.bot]
                
                # If only the bot remains, disconnect
                if len(members_in_channel) == 0:
                    logger.info(f"Bot is alone in {channel.name}, disconnecting...")
                    try:
                        await voice_client.disconnect()
                        self.remove_voice_client(member.guild.id)
                        logger.info(f"Disconnected from {channel.name} due to being alone")
                    except Exception as e:
                        logger.error(f"Error disconnecting when alone: {str(e)}", exc_info=True)
                        # Force cleanup even if disconnect failed
                        self.remove_voice_client(member.guild.id)

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins channel supplied by user"""
        logger.info(f"Join command called by {ctx.author} in guild {ctx.guild.name} for channel {channel.name}")
        
        try:
            # Check if server already has active connection
            current_vc = self.get_voice_client(ctx.guild.id)
            if current_vc:
                if current_vc.is_connected():
                    channel_name = self.current_channels.get(ctx.guild.id, "unknown channel")
                    if isinstance(channel_name, discord.VoiceChannel):
                        channel_name = channel_name.name
                    logger.info(f"Already connected to {channel_name}")
                    return await ctx.send(f"Already connected to {channel_name}")
                else:
                    logger.warning(f"Voice client exists but not connected, cleaning up")
                    self.remove_voice_client(ctx.guild.id)
            
            # Check bot permissions
            if not channel.permissions_for(ctx.guild.me).connect:
                logger.error(f"Bot lacks connect permission for {channel.name}")
                return await ctx.send("I don't have permission to connect to that channel.")
            
            if not channel.permissions_for(ctx.guild.me).speak:
                logger.error(f"Bot lacks speak permission for {channel.name}")
                return await ctx.send("I don't have permission to speak in that channel.")
            
            logger.info(f"Attempting to connect to {channel.name}")
            
            # Direct connection attempt with timeout
            voice_client = await channel.connect(timeout=20.0)
            self.set_voice_client(ctx.guild.id, voice_client)
            self.current_channels[ctx.guild.id] = channel
            
            logger.info(f"Successfully connected to {channel.name}")
            return await ctx.send(f"Connected to {channel.name}")
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timed out for channel {channel.name}")
            return await ctx.send("Connection timed out - please try again")
        except discord.ClientException as e:
            logger.error(f"Discord client exception while connecting: {str(e)}")
            return await ctx.send(f"Failed to connect: {str(e)}")
        except discord.OpusNotLoaded:
            logger.error("Opus library not loaded")
            return await ctx.send("Audio codec not available - please contact bot administrator")
        except Exception as e:
            logger.error(f"Unexpected error while connecting: {str(e)}", exc_info=True)
            return await ctx.send("An unexpected error occurred while connecting")

    @commands.command()
    async def leave(self, ctx):
        """Leaves current voice channel"""
        logger.info(f"Leave command called by {ctx.author} in guild {ctx.guild.name}")
        
        voice_client = self.get_voice_client(ctx.guild.id)
        bot_voice_state = ctx.guild.me.voice
        
        # Check if bot is actually in a voice channel (even if voice_client is stale)
        if bot_voice_state and bot_voice_state.channel:
            # Bot is in a channel, disconnect it
            try:
                # Try to use tracked voice_client first
                if voice_client:
                    try:
                        await voice_client.disconnect(force=True)
                        logger.info(f"Successfully disconnected tracked voice client in {ctx.guild.name}")
                    except Exception as e:
                        logger.warning(f"Error disconnecting tracked client: {e}, trying guild.voice_client")
                        # Fall back to guild.voice_client
                        vc = ctx.guild.voice_client
                        if vc:
                            await vc.disconnect(force=True)
                            logger.info(f"Successfully disconnected via guild.voice_client in {ctx.guild.name}")
                else:
                    # No tracked client, use guild.voice_client
                    vc = ctx.guild.voice_client
                    if vc:
                        await vc.disconnect(force=True)
                        logger.info(f"Successfully disconnected via guild.voice_client in {ctx.guild.name}")
                    else:
                        logger.warning("Bot in channel but no voice_client found, forcing cleanup")
                
                self.remove_voice_client(ctx.guild.id)
                await ctx.send("Left voice channel")
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}", exc_info=True)
                # Force cleanup even if disconnect failed
                self.remove_voice_client(ctx.guild.id)
                await ctx.send("Forced disconnect due to error")
        elif voice_client is not None:
            # Have a tracked client but bot not in channel (stale state)
            logger.warning(f"Stale voice client found when leave called in {ctx.guild.name}, cleaning up")
            self.remove_voice_client(ctx.guild.id)
            await ctx.send("Cleaned up stale connection")
        else:
            logger.info(f"No voice client found when leave called in {ctx.guild.name}")
            await ctx.send("Not connected to a voice channel")

    @commands.command(aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):
        """Plays audio from a URL (YouTube, etc.)"""
        logger.info(f"Play command called by {ctx.author} in guild {ctx.guild.name} with URL: {url}")
        
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                logger.warning(f"User {ctx.author} not in voice channel")
                return await ctx.send("You need to be in a voice channel to use this command.")

            # Get current voice client for this guild
            voice_client = self.get_voice_client(ctx.guild.id)
            
            # Check actual Discord state - bot might be in a channel even if voice_client is stale
            bot_voice_state = ctx.guild.me.voice
            target_channel = ctx.author.voice.channel
            
            # If bot is in a different channel, disconnect first
            if bot_voice_state and bot_voice_state.channel:
                if bot_voice_state.channel.id != target_channel.id:
                    logger.info(f"Bot is in different channel ({bot_voice_state.channel.name}), disconnecting first")
                    try:
                        if voice_client:
                            await voice_client.disconnect(force=True)
                        else:
                            # Try to get the voice client from the guild
                            vc = ctx.guild.voice_client
                            if vc:
                                await vc.disconnect(force=True)
                    except Exception as e:
                        logger.warning(f"Error disconnecting from old channel: {e}")
                    finally:
                        self.remove_voice_client(ctx.guild.id)
                        await asyncio.sleep(0.5)
                elif voice_client is None or not voice_client.is_connected():
                    # Bot is in the right channel but voice_client is stale, clean up
                    logger.warning("Bot is in channel but voice_client is stale, cleaning up")
                    try:
                        vc = ctx.guild.voice_client
                        if vc:
                            await vc.disconnect(force=True)
                    except Exception as e:
                        logger.warning(f"Error cleaning up stale connection: {e}")
                    finally:
                        self.remove_voice_client(ctx.guild.id)
                        await asyncio.sleep(0.5)

            # Connect to voice with timeout if not already connected
            if voice_client is None or not voice_client.is_connected():
                logger.info(f"Connecting to voice channel {target_channel.name}")
                
                try:
                    # Double-check we're not already connected (handle race conditions)
                    bot_voice_state = ctx.guild.me.voice
                    if bot_voice_state and bot_voice_state.channel and bot_voice_state.channel.id == target_channel.id:
                        # We're already in the right channel, get the voice client
                        voice_client = ctx.guild.voice_client
                        if voice_client and voice_client.is_connected():
                            logger.info("Already connected to target channel, using existing connection")
                            self.set_voice_client(ctx.guild.id, voice_client)
                            self.current_channels[ctx.guild.id] = target_channel
                        else:
                            # Stale connection, force disconnect and reconnect
                            logger.warning("Stale connection detected, forcing disconnect")
                            try:
                                if voice_client:
                                    await voice_client.disconnect(force=True)
                                vc = ctx.guild.voice_client
                                if vc:
                                    await vc.disconnect(force=True)
                            except:
                                pass
                            self.remove_voice_client(ctx.guild.id)
                            await asyncio.sleep(0.5)
                            voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                            self.set_voice_client(ctx.guild.id, voice_client)
                            self.current_channels[ctx.guild.id] = target_channel
                            logger.info(f"Reconnected to {target_channel.name} for playback")
                    else:
                        # Not connected, connect fresh
                        voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                        self.set_voice_client(ctx.guild.id, voice_client)
                        self.current_channels[ctx.guild.id] = target_channel
                        logger.info(f"Connected to {target_channel.name} for playback")
                    
                except discord.ClientException as e:
                    # Handle "Already connected" error by checking actual state
                    if "Already connected" in str(e):
                        logger.warning("Got 'Already connected' error, checking actual state")
                        bot_voice_state = ctx.guild.me.voice
                        if bot_voice_state and bot_voice_state.channel:
                            if bot_voice_state.channel.id == target_channel.id:
                                # We're in the right channel, use existing connection
                                voice_client = ctx.guild.voice_client
                                if voice_client:
                                    self.set_voice_client(ctx.guild.id, voice_client)
                                    self.current_channels[ctx.guild.id] = target_channel
                                    logger.info("Using existing connection after 'Already connected' error")
                                else:
                                    # Discord says we're connected but no voice_client, force cleanup
                                    logger.error("Discord says connected but no voice_client, forcing cleanup")
                                    try:
                                        vc = ctx.guild.voice_client
                                        if vc:
                                            await vc.disconnect(force=True)
                                    except:
                                        pass
                                    self.remove_voice_client(ctx.guild.id)
                                    await asyncio.sleep(0.5)
                                    voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                                    self.set_voice_client(ctx.guild.id, voice_client)
                                    self.current_channels[ctx.guild.id] = target_channel
                            else:
                                # We're in wrong channel, disconnect and reconnect
                                logger.info("Bot in wrong channel, disconnecting and reconnecting")
                                try:
                                    vc = ctx.guild.voice_client
                                    if vc:
                                        await vc.disconnect(force=True)
                                except:
                                    pass
                                self.remove_voice_client(ctx.guild.id)
                                await asyncio.sleep(0.5)
                                voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                                self.set_voice_client(ctx.guild.id, voice_client)
                                self.current_channels[ctx.guild.id] = target_channel
                        else:
                            # Discord says we're connected but bot_voice_state is None, force cleanup
                            logger.error("Discord error but bot not in channel, forcing cleanup")
                            try:
                                vc = ctx.guild.voice_client
                                if vc:
                                    await vc.disconnect(force=True)
                            except:
                                pass
                            self.remove_voice_client(ctx.guild.id)
                            await asyncio.sleep(0.5)
                            voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                            self.set_voice_client(ctx.guild.id, voice_client)
                            self.current_channels[ctx.guild.id] = target_channel
                    else:
                        raise
                except asyncio.TimeoutError:
                    logger.error("Connection timed out during play command")
                    return await ctx.send("Connection timed out - please try again")
                except Exception as e:
                    logger.error(f"Failed to connect during play: {str(e)}", exc_info=True)
                    return await ctx.send(f"Failed to connect: {str(e)}")

            # Check if already playing
            if voice_client.is_playing():
                logger.info("Already playing audio, stopping current playback")
                voice_client.stop()
                await asyncio.sleep(1)  # Give it a moment to stop

            # Parse timestamp
            ffmpeg_options = {'options': '-vn'}
            pre_op = '-ss 0'
            if timestamp and timestamp != '0':
                # Validate timestamp format (basic check)
                timestamp = timestamp.strip()
                if '-' in timestamp:
                    parts = timestamp.split('-', 1)  # Split only on first dash
                    if len(parts) == 2:
                        start, stop = parts[0].strip(), parts[1].strip()
                        if start and stop:
                            pre_op = f'-ss {start} -to {stop}'
                            logger.info(f"Using timestamp range: {start} to {stop}")
                        else:
                            logger.warning(f"Invalid timestamp range format: {timestamp}")
                    else:
                        logger.warning(f"Invalid timestamp range format: {timestamp}")
                else:
                    pre_op = f'-ss {timestamp}'
                    logger.info(f"Using timestamp: {timestamp}")

            # Add status message
            await ctx.send("Fetching audio... This may take a moment.")
            logger.info(f"Fetching audio from URL: {url}")

            # Create player with timeout
            try:
                async with ctx.typing():
                    async with asyncio.timeout(30):  # 30 second timeout
                        player = await YTDLSource.from_url(url, ffmpeg_options, pre_op, loop=self.bot.loop)
                        logger.info(f"Successfully created player for: {player.title}")
            except asyncio.TimeoutError:
                logger.error("Timed out while fetching audio")
                return await ctx.send("Timed out while fetching the audio. The URL might be invalid or too long.")
            except Exception as e:
                logger.error(f"Error creating player: {str(e)}", exc_info=True)
                return await ctx.send(f"Error fetching audio: {str(e)}")

            # Play the audio with error callback
            def after_playing(error):
                if error:
                    logger.error(f'Player error: {error}')
                else:
                    logger.info('Playback completed successfully')

            voice_client.play(player, after=after_playing)
            logger.info(f'Started playing: {player.title}')
            
            # Track the play for statistics
            self._track_play(ctx.channel.id, player.title)
            
            return await ctx.send(f'Now playing: {player.title}')

        except Exception as e:
            logger.error(f"Play command error: {str(e)}", exc_info=True)
            return await ctx.send("An error occurred while trying to play the audio.")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        logger.info(f"Volume command called by {ctx.author} in guild {ctx.guild.name} with volume: {volume}")
        
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client is None or not voice_client.is_connected():
            logger.warning("Volume command called but not connected to voice channel")
            return await ctx.send("Not connected to a voice channel.")

        if not (0 <= volume <= 100):
            logger.warning(f"Invalid volume level: {volume}")
            return await ctx.send("Volume must be between 0 and 100.")

        try:
            if not voice_client.source:
                logger.warning("No audio source available to change volume")
                return await ctx.send("No audio is currently playing.")
            voice_client.source.volume = volume / 100
            logger.info(f"Changed volume to {volume}%")
            await ctx.send("Changed volume to {}%".format(volume))
        except AttributeError:
            logger.warning("Audio source does not support volume control")
            await ctx.send("Current audio source does not support volume control.")
        except Exception as e:
            logger.error(f"Error changing volume: {str(e)}", exc_info=True)
            await ctx.send("Error changing volume.")

    @commands.command(aliases=['pa', 'pau'])
    async def pause(self, ctx):
        """Pause the current audio"""
        logger.info(f"Pause command called by {ctx.author} in guild {ctx.guild.name}")
        
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client and voice_client.is_playing():
            logger.info(f"Music paused in {ctx.guild.name}")
            voice_client.pause()
            await ctx.send("Music paused")
        else:
            logger.info(f"Music not playing when pause called in {ctx.guild.name}")
            await ctx.send("Music not playing")

    @commands.command(aliases=['r', 'res'])
    async def resume(self, ctx):
        """Resume the current audio"""
        logger.info(f"Resume command called by {ctx.author} in guild {ctx.guild.name}")
        
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client and voice_client.is_paused():
            logger.info(f"Resumed music in {ctx.guild.name}")
            voice_client.resume()
            await ctx.send("Resumed music")
        else:
            logger.info(f"Music is not paused in {ctx.guild.name}")
            await ctx.send("Music is not paused")

    @commands.command(aliases=['s', 'sto'])
    async def stop(self, ctx):
        """Stop the current audio"""
        logger.info(f"Stop command called by {ctx.author} in guild {ctx.guild.name}")
        
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client:
            if voice_client.is_playing() or voice_client.is_paused():
                logger.info(f"Music stopped in {ctx.guild.name}")
                voice_client.stop()
                await ctx.send("Music stopped")
            else:
                logger.info(f"No music playing when stop called in {ctx.guild.name}")
                await ctx.send("No music playing")
        else:
            logger.info(f"No voice client when stop called in {ctx.guild.name}")
            await ctx.send("Not connected to a voice channel")

    @commands.command()
    async def debug(self, ctx):
        """Debug command to check bot status"""
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client:
            status = f"Connected: {voice_client.is_connected()}\n"
            status += f"Playing: {voice_client.is_playing()}\n"
            status += f"Paused: {voice_client.is_paused()}\n"
            if ctx.guild.id in self.current_channels:
                status += f"Channel: {self.current_channels[ctx.guild.id].name}\n"
            status += f"Latency: {voice_client.latency}ms"
        else:
            status = "No voice client found"
        
        await ctx.send(f"```\nBot Status:\n{status}\n```")

    async def _parse_channel_history(self, channel):
        """Parse channel message history to build play statistics"""
        logger.info(f"Parsing message history for channel {channel.id}")
        stats = {}
        
        try:
            # Check bot permissions
            if not channel.permissions_for(channel.guild.me).read_message_history:
                logger.warning(f"No permission to read message history in {channel.name}")
                return None
            
            # Look for "Now playing:" messages from the bot
            async for message in channel.history(limit=None):
                if message.author == self.bot.user:
                    # Check if this is a "Now playing:" message
                    content = message.content
                    if content.startswith("Now playing:"):
                        # Extract track name (everything after "Now playing: ")
                        track_name = content.replace("Now playing:", "").strip()
                        if track_name:
                            if track_name not in stats:
                                stats[track_name] = 0
                            stats[track_name] += 1
            
            logger.info(f"Parsed {sum(stats.values())} total plays from {len(stats)} unique tracks")
            return stats
        except Exception as e:
            logger.error(f"Error parsing channel history: {e}", exc_info=True)
            return None

    @commands.command(aliases=['top', 'stats'])
    async def toptracks(self, ctx, *, args: str = None):
        """Shows top 10 most played tracks in specified channel (or current). Use 'rescan' to force rescan."""
        # Parse arguments - check for "rescan" keyword
        force_rescan = False
        channel = None
        
        if args:
            args_lower = args.lower().strip()
            # Check if "rescan" is in the arguments
            if 'rescan' in args_lower:
                force_rescan = True
                # Try to extract channel name if provided (remove "rescan" keyword)
                channel_str = args_lower.replace('rescan', '').strip()
                if channel_str:
                    # Try to parse as channel
                    try:
                        channel = await commands.TextChannelConverter().convert(ctx, channel_str)
                    except commands.BadArgument:
                        # Not a valid channel, ignore
                        pass
            else:
                # Try to parse as channel
                try:
                    channel = await commands.TextChannelConverter().convert(ctx, args)
                except commands.BadArgument:
                    # Not a valid channel, ignore
                    pass
        
        # Use current channel if none specified
        if channel is None:
            channel = ctx.channel
        
        stats = self._load_stats()
        channel_id_str = str(channel.id)
        
        # Force rescan if requested, or if no stats exist
        should_rescan = force_rescan or (channel_id_str not in stats or not stats[channel_id_str])
        
        if should_rescan:
            if force_rescan:
                await ctx.send(f"Rescanning message history for {channel.mention}... This may take a moment.")
            else:
                await ctx.send(f"No statistics found. Parsing message history for {channel.mention}... This may take a moment.")
            
            parsed_stats = await self._parse_channel_history(channel)
            
            if parsed_stats is None:
                return await ctx.send(f"Could not parse message history. Make sure I have permission to read message history in {channel.mention}")
            
            if not parsed_stats:
                return await ctx.send(f"No play history found in {channel.mention}")
            
            # Save the parsed stats (replace entirely on force rescan to avoid double-counting)
            stats[channel_id_str] = parsed_stats
            
            self._save_stats(stats)
            total_plays = sum(stats[channel_id_str].values())
            await ctx.send(f"Parsed {sum(parsed_stats.values())} plays from message history. Total: {total_plays} plays.")
        
        # Get tracks for this channel and sort by play count
        channel_stats = stats[channel_id_str]
        sorted_tracks = sorted(channel_stats.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 10
        top_tracks = sorted_tracks[:10]
        
        if not top_tracks:
            return await ctx.send(f"No play statistics found for {channel.mention}")
        
        # Format output
        lines = [f"Top tracks in {channel.mention}:"]
        lines.append("```")
        for rank, (track_name, play_count) in enumerate(top_tracks, 1):
            # Truncate long track names
            display_name = track_name[:60] + "..." if len(track_name) > 60 else track_name
            lines.append(f"{rank}. {display_name} - {play_count} play(s)")
        lines.append("```")
        
        await ctx.send("\n".join(lines))

async def setup(client):
    await client.add_cog(Music(client))
    logger.info("Music cog loaded successfully")