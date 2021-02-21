import discord
from discord.ext import commands

class Core(commands.Cog):
  def __init__(self,client):
    self.client = client

  @commands.Cog.listener()
  async def on_ready(self):
    print("Bot is online...")

  #@client.event
  #async def on_command_error(ctx,error):
  #  if isinstance(error, commands.MissingRequiredArgument):
  #    await ctx.send("Missing Required Argument")
  #if isinstance(error, )

  @commands.command()
  @commands.has_permissions(manage_messages=True)
  async def why(self,ctx):
    await(ctx.send('M O N K E'))

  


def setup(client):
  client.add_cog(Core(client))