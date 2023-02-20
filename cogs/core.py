import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta

class Core(commands.Cog):
  def __init__(self,client):
    self.client = client
    self.st = time.time() # Get start time for ping info

  @commands.Cog.listener()
  async def on_ready(self):
    print("Bot is online...")

  @commands.command()
  @commands.has_permissions(manage_messages=True)
  async def ping(self,ctx):
    """Ping Test"""
    et = time.time()
    d = datetime.fromtimestamp(int(et-self.st))
    msg = "Bot has been up for {:d} Days {:d} Hours {:d} Minutes {:d} Seconds".format(d.day-1, d.hour, d.minute, d.second)
    await(ctx.send(msg))

  
async def setup(client):
  await client.add_cog(Core(client))