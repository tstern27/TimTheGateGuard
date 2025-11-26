import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta
import logging
import asyncio
import sys
from discord.utils import get

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
    sys.path.insert(0, "..")
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
        logger.info("Music cog initialized")

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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Monitor voice state changes for debugging"""
        if member == self.bot.user:
            logger.info(f"Bot voice state changed - Before: {before.channel}, After: {after.channel}")
            if before.channel and not after.channel:
                logger.warning(f"Bot was disconnected from voice channel: {before.channel.name}")
                # Clean up our tracking
                guild_id = before.channel.guild.id
                if guild_id in self.voice_clients:
                    logger.info(f"Cleaning up voice client tracking for guild {guild_id}")
                    self.remove_voice_client(guild_id)

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins channel supplied by user"""
        logger.info(f"Join command called by {ctx.author} in guild {ctx.guild.name} for channel {channel.name}")
        
        try:
            # Check if server already has active connection
            current_vc = self.get_voice_client(ctx.guild.id)
            if current_vc:
                if current_vc.is_connected():
                    logger.info(f"Already connected to {self.current_channels[ctx.guild.id].name}")
                    return await ctx.send(f"Already connected to {self.current_channels[ctx.guild.id].name}")
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
        if voice_client is not None:
            try:
                if voice_client.is_connected():
                    await voice_client.disconnect()
                    logger.info(f"Successfully disconnected from voice channel in {ctx.guild.name}")
                else:
                    logger.warning(f"Voice client not connected when leave called in {ctx.guild.name}")
                
                self.remove_voice_client(ctx.guild.id)
                await ctx.send("Left voice channel")
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}", exc_info=True)
                # Force cleanup even if disconnect failed
                self.remove_voice_client(ctx.guild.id)
                await ctx.send("Forced disconnect due to error")
        else:
            logger.info(f"No voice client found when leave called in {ctx.guild.name}")
            await ctx.send("Not connected to a voice channel")

    @commands.command(pass_context=True, aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):
        """Plays audio from a youtube url"""
        logger.info(f"Play command called by {ctx.author} in guild {ctx.guild.name} with URL: {url}")
        
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                logger.warning(f"User {ctx.author} not in voice channel")
                return await ctx.send("You need to be in a voice channel to use this command.")

            # Get current voice client for this guild
            voice_client = self.get_voice_client(ctx.guild.id)

            # Connect to voice with timeout if not already connected
            if voice_client is None or not voice_client.is_connected():
                logger.info(f"Connecting to voice channel {ctx.author.voice.channel.name}")
                
                try:
                    # Clean up any existing non-connected client
                    if voice_client and not voice_client.is_connected():
                        self.remove_voice_client(ctx.guild.id)
                    await asyncio.sleep(1)
                    voice_client = await ctx.author.voice.channel.connect(timeout=20.0)
                    await asyncio.sleep(1)
                    self.set_voice_client(ctx.guild.id, voice_client)
                    self.current_channels[ctx.guild.id] = ctx.author.voice.channel
                    logger.info(f"Connected to {ctx.author.voice.channel.name} for playback")
                    
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
            if '-' in timestamp:
                start, stop = timestamp.split('-')
                pre_op = f'-ss {start} -to {stop}'
                logger.info(f"Using timestamp range: {start} to {stop}")
            elif timestamp != '0':
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
            voice_client.source.volume = volume / 100
            logger.info(f"Changed volume to {volume}%")
            await ctx.send("Changed volume to {}%".format(volume))
        except Exception as e:
            logger.error(f"Error changing volume: {str(e)}", exc_info=True)
            await ctx.send("Error changing volume.")

    @commands.command(pass_context=True, aliases=['pa', 'pau'])
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

    @commands.command(pass_context=True, aliases=['r', 'res'])
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

    @commands.command(pass_context=True, aliases=['s', 'sto'])
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

async def setup(client):
    await client.add_cog(Music(client))
    logger.info("Music cog loaded successfully")