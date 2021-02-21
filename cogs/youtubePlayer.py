import discord
import youtube_dl
import os
from discord.ext import commands
from discord.utils import get

class YoutubePlayer(commands.Cog):
  def __init__(self,client):
    self.client = client
    self.players = None
    self.voice = None

  @commands.command()
  async def play(self,ctx, url: str):
    #join
    channel = ctx.message.author.voice.channel
    self.voice = get(self.client.voice_clients, guild=ctx.guild)

    if self.voice and self.voice.is_connected():
      await self.voice.move_to(channel)
    else:
      self.voice = await channel.connect()

    #play 
    aud_there = os.path.isfile("aud.mp3")
    try:
      if aud_there:
        os.remove("aud.mp3")
        print("Removed old song")
    except PermissionError:
      print("Song Currently Being Played")
    await ctx.send("Playing: " + url)
    
    ydl_opts = {
      'format': 'bestaudio/best',
      'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
      }]
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
      print("Downloading audio")
      ydl.download([url])

    for file in os.listdir("./"):
      if file.endswith(".mp3"):
        name = file
        print("Renamed File: " + str(file))
        os.rename(file, "aud.mp3")

    self.voice.play(discord.FFmpegPCMAudio("aud.mp3"), after=lambda e: print(str(name) + " has finished playing"))
    self.voice.source = discord.PCMVolumeTransformer(self.voice.source)
    self.voice.source.volume = 0.07

def setup(client):
  client.add_cog(YoutubePlayer(client))
