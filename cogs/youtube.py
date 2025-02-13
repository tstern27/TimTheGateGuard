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
        self.vc = None
        self.current_bot_chan = None

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins channel supplied by user"""
        try:
            if len(self.bot.voice_clients) > 1:
                return await ctx.send("Too Many Connections -- contact tim")
            
            # Direct connection attempt without loop
            self.vc = await channel.connect(timeout=20.0)  # Add timeout
            self.current_bot_chan = channel
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
        if self.vc is not None: 
           await self.vc.disconnect()
           self.vc = None
           return

    @commands.command(pass_context=True, aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):
        """Plays audio from a youtube url"""
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                return await ctx.send("You need to be in a voice channel to use this command.")

            # Connect to voice with timeout
            if self.vc is None:
                try:
                    self.vc = await ctx.author.voice.channel.connect(timeout=20.0)
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
            self.vc.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
            
            return await ctx.send(f'Now playing: {player.title}')

        except Exception as e:
            print(f"Play command error: {str(e)}")
            return await ctx.send("An error occurred while trying to play the audio.")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await  self.vc.disconnect()

    @commands.command(pass_context=True, aliases=['pa', 'pau'])
    async def pause(self, ctx):

        if self.vc and self.vc.is_playing():
            print("Music paused")
            self.vc.pause()
            await ctx.send("Music paused")
        else:
            print("Music not playing failed pause")
            await ctx.send("Music not playing failed pause")

    @commands.command(pass_context=True, aliases=['r', 'res'])
    async def resume(self, ctx):

        if self.vc and self.vc.is_paused():
            print("Resumed music")
            self.vc.resume()
            await ctx.send("Resumed music")
        else:
            print("Music is not paused")
            await ctx.send("Music is not paused")

    @commands.command(pass_context=True, aliases=['s', 'sto'])
    async def stop(self, ctx):
        #queues.clear()

        if self.vc and self.vc.is_playing():
            print("Music stopped")
            self.vc.stop()
            await ctx.send("Music stopped")
        else:
            print("No music playing failed to stop")
            await ctx.send("No music playing failed to stop")


async def setup(client):
    await client.add_cog(Music(client))
