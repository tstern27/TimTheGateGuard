import asyncio
import discord

import sys

from discord.ext import commands, tasks
from discord.utils import get

sys.path.insert(0,"..")
from lib.YTDLSource import YTDLSource

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ctx = None
        self.voice = None
        self.current_bot_chan = None

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def leave(self, ctx):
        """Leaves a voice channel"""
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    async def disconnect(self):
        channel = self.ctx.message.author.voice.channel

        if self.voice.is_connected():
            await self.voice.disconnect()
            print(f"The bot has left {channel}")
        else:
            print("Bot was told to leave voice channel, but was not in one")
            await self.ctx.send("Don't think I am in a voice channel")

    @commands.command(pass_context=True, aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):  # add the arg
        """Plays audio from a youtube url
        - Optional Args:
           -Starting time stamp:
                (-play <URL> <timeStamp>)
           -Start/stop time stamp:
                (-play <URL> <startTime>-<endTime>)"""

        # Check Current Bot status
        if self.voice and self.voice.is_connected():
            # is it in a diff channel

            if self.current_bot_chan != ctx.message.author.voice.channel:
                # if idle - disconnect
                if not self.voice.is_playing() and not self.voice.is_paused():
                    await self.disconnect()
                # if not idle - activty error
                else:
                    # append onto queue
                    await ctx.send("Bot Currently busy in {} channel, your audio will play shortly".format(self.current_bot_chan))
                    return
            else:
                if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
                    # append onto queue
                    return

        # Save context off
        self.ctx = ctx
        self.current_bot_chan = ctx.message.author.voice.channel

        # Parse Time Stamp
        ffmpeg_options = None
        if '-' in timestamp:
            args = timestamp.split('-')
            start = args[0]
            stop = args[1]
            pre_op= f'-ss {start} -to {stop}'
            ffmpeg_options = {'options': f'-vn'}
        else:
            start = timestamp
            pre_op= f'-ss {start}'
            ffmpeg_options = {'options': f'-vn'}

        # Join the channel
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

        # Play the audio
        async with ctx.typing():
            self.voice = ctx.voice_client
            player = await YTDLSource.from_url(url, ffmpeg_options, pre_op, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

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

        await  self.voice.disconnect()

    @commands.command(pass_context=True, aliases=['pa', 'pau'])
    async def pause(self, ctx):

        if self.voice and self.voice.is_playing():
            print("Music paused")
            self.voice.pause()
            await ctx.send("Music paused")
        else:
            print("Music not playing failed pause")
            await ctx.send("Music not playing failed pause")

    @commands.command(pass_context=True, aliases=['r', 'res'])
    async def resume(self, ctx):

        if self.voice and self.voice.is_paused():
            print("Resumed music")
            self.voice.resume()
            await ctx.send("Resumed music")
        else:
            print("Music is not paused")
            await ctx.send("Music is not paused")

    @commands.command(pass_context=True, aliases=['s', 'sto'])
    async def stop(self, ctx):
        #queues.clear()

        if self.voice and self.voice.is_playing():
            print("Music stopped")
            self.voice.stop()
            await ctx.send("Music stopped")
        else:
            print("No music playing failed to stop")
            await ctx.send("No music playing failed to stop")


async def setup(client):
    await client.add_cog(Music(client))
