import asyncio
import discord

import sys

from discord.ext import commands
from discord.utils import get

sys.path.insert(0,"..")
from lib.YTDLSource import YTDLSource

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Change from single vc to dictionary of guild_id -> voice_client
        self.voice_clients = {}
        # Change from single channel to dictionary of guild_id -> channel
        self.current_channels = {}

    def get_voice_client(self, guild_id):
        """Get voice client for specific guild"""
        return self.voice_clients.get(guild_id)

    def set_voice_client(self, guild_id, voice_client):
        """Set voice client for specific guild"""
        self.voice_clients[guild_id] = voice_client

    def remove_voice_client(self, guild_id):
        """Remove voice client for specific guild"""
        if guild_id in self.voice_clients:
            del self.voice_clients[guild_id]
        if guild_id in self.current_channels:
            del self.current_channels[guild_id]

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins channel supplied by user"""
        try:
            # Check if server already has active connection
            current_vc = self.get_voice_client(ctx.guild.id)
            if current_vc and current_vc.is_connected():
                return await ctx.send(f"Already connected to {self.current_channels[ctx.guild.id].name}")
            
            # Direct connection attempt without loop
            voice_client = await channel.connect(timeout=20.0)
            self.set_voice_client(ctx.guild.id, voice_client)
            self.current_channels[ctx.guild.id] = channel
            return await ctx.send(f"Connected to {channel.name}")
            
        except asyncio.TimeoutError:
            return await ctx.send("Connection timed out - please try again")
        except discord.ClientException as e:
            return await ctx.send(f"Failed to connect: {str(e)}")
        except Exception as e:
            print(f"Unexpected error while connecting: {str(e)}")
            return await ctx.send("An unexpected error occurred while connecting")

    @commands.command()
    async def leave(self, ctx):
        """Leaves current voice channel"""
        voice_client = self.get_voice_client(ctx.guild.id)
        if voice_client is not None: 
           await voice_client.disconnect()
           self.remove_voice_client(ctx.guild.id)
           return

    @commands.command(pass_context=True, aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):
        """Plays audio from a youtube url"""
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                return await ctx.send("You need to be in a voice channel to use this command.")

            # Get current voice client for this guild
            voice_client = self.get_voice_client(ctx.guild.id)

            # Connect to voice with timeout if not already connected
            if voice_client is None:
                try:
                    voice_client = await ctx.author.voice.channel.connect(timeout=20.0)
                    self.set_voice_client(ctx.guild.id, voice_client)
                    self.current_channels[ctx.guild.id] = ctx.author.voice.channel
                except asyncio.TimeoutError:
                    return await ctx.send("Connection timed out - please try again")
                except Exception as e:
                    return await ctx.send(f"Failed to connect: {str(e)}")

            # Parse timestamp
            ffmpeg_options = {'options': '-vn'}
            pre_op = '-ss 0'
            if '-' in timestamp:
                start, stop = timestamp.split('-')
                pre_op = f'-ss {start} -to {stop}'
            elif timestamp != '0':
                pre_op = f'-ss {timestamp}'

            # Add status message
            await ctx.send("Fetching audio... This may take a moment.")

            # Create player with timeout
            try:
                async with ctx.typing():
                    async with asyncio.timeout(30):  # 30 second timeout
                        player = await YTDLSource.from_url(url, ffmpeg_options, pre_op, loop=self.bot.loop)
            except asyncio.TimeoutError:
                return await ctx.send("Timed out while fetching the audio. The URL might be invalid or too long.")
            except Exception as e:
                return await ctx.send(f"Error fetching audio: {str(e)}")

            # Play the audio
            voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
            
            return await ctx.send(f'Now playing: {player.title}')

        except Exception as e:
            print(f"Play command error: {str(e)}")
            return await ctx.send("An error occurred while trying to play the audio.")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client is None or not voice_client.is_connected():
            return await ctx.send("Not connected to a voice channel.")

        voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        voice_client = self.get_voice_client(ctx.guild.id)
        if voice_client:
            await voice_client.disconnect()
            self.remove_voice_client(ctx.guild.id)

    @commands.command(pass_context=True, aliases=['pa', 'pau'])
    async def pause(self, ctx):
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client and voice_client.is_playing():
            print(f"Music paused in {ctx.guild.name}")
            voice_client.pause()
            await ctx.send("Music paused")
        else:
            print(f"Music not playing failed pause in {ctx.guild.name}")
            await ctx.send("Music not playing failed pause")

    @commands.command(pass_context=True, aliases=['r', 'res'])
    async def resume(self, ctx):
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client and voice_client.is_paused():
            print(f"Resumed music in {ctx.guild.name}")
            voice_client.resume()
            await ctx.send("Resumed music")
        else:
            print(f"Music is not paused in {ctx.guild.name}")
            await ctx.send("Music is not paused")

    @commands.command(pass_context=True, aliases=['s', 'sto'])
    async def stop(self, ctx):
        voice_client = self.get_voice_client(ctx.guild.id)
        
        if voice_client and voice_client.is_playing():
            print(f"Music stopped in {ctx.guild.name}")
            voice_client.stop()
            await ctx.send("Music stopped")
        else:
            print(f"No music playing failed to stop in {ctx.guild.name}")
            await ctx.send("No music playing failed to stop")

async def setup(client):
    await client.add_cog(Music(client))