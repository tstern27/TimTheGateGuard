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
        self.vc = None
        self.current_bot_chan = None
    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins channel supplied by user"""

        if len(self.bot.voice_clients) > 1:
            return await ctx.send("Too Many Connections -- contact tim")
        else:
            for c in ctx.guild.voice_channels:
                if c is channel:
                    await c.connect()
                    if len(self.bot.voice_clients) != 1:
                        return await ctx.send("Couldn't Parse Voice Client -- contact tim")
                    self.vc = self.bot.voice_clients[0]
                    self.current_bot_chan = channel
                    return

            return await ctx.send("Didn't work -- contact tim")

    @commands.command()
    async def leave(self, ctx):
        """Leaves current voice channel"""
        if self.vc is not None: 
           await self.vc.disconnect()
           self.vc = None
           return

    @commands.command(pass_context=True, aliases=['p'])
    async def play(self, ctx, url, timestamp='0'):  # add the arg
        """Plays audio from a youtube url
        - Optional Args:
           -Starting time stamp:
                (-play <URL> <timeStamp>)
           -Start/stop time stamp:
                (-play <URL> <startTime>-<endTime>)"""

        # Check Current Bot status
        if self.vc and self.vc.is_connected():
            # is it in a diff channel
            if self.current_bot_chan != ctx.message.author.voice.channel:
                # if idle - disconnect
                if not self.vc.is_playing() and not self.vc.is_paused():
                    await self.vc.disconnect()
                    self.vc = None
                # if not idle - activty error
                else:
                    # append onto queue
                    await ctx.send("Bot Currently busy in {} channel, your audio will play shortly".format(self.current_bot_chan))
                    return
            else:
                if self.vc and (self.vc.is_playing() or self.vc.is_paused()):
                    # append onto queue
                    return

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
        if self.vc is None:
            if ctx.author.voice and ctx.author.voice.channel:
                await ctx.author.voice.channel.connect()
                if len(self.bot.voice_clients) != 1:
                    return await ctx.send("Couldn't Parse Voice Client -- contact tim")
                self.vc = self.bot.voice_clients[0]

            else:
                await ctx.send("Bot not connected to a voice channel. Please use join command first")
                return

        # Play the audio
        async with ctx.typing():
            player = await YTDLSource.from_url(url, ffmpeg_options, pre_op, loop=self.bot.loop)
            self.vc.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        return await ctx.send('Now playing: {}'.format(player.title))

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
