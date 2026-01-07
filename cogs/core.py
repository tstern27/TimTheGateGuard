import discord
from discord.ext import commands
import time
import sys
import asyncio
from datetime import timedelta

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
    elapsed = et - self.st
    td = timedelta(seconds=int(elapsed))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    msg = "Bot has been up for {:d} Days {:d} Hours {:d} Minutes {:d} Seconds".format(days, hours, minutes, seconds)
    await ctx.send(msg)

  @commands.command(aliases=['reset'])
  async def restart(self, ctx):
    """Soft restart: Clears voice connections and resets state"""
    await ctx.send("Restarting bot... Clearing voice connections...")
    
    # Get Music cog and clear all voice connections
    music_cog = self.client.get_cog('Music')
    if music_cog:
      try:
        disconnected = await music_cog.clear_all_voice_connections()
        # Reset uptime counter
        self.st = time.time()
        await ctx.send(f"Restart complete. Disconnected from {disconnected} voice channel(s). Uptime counter reset.")
      except Exception as e:
        await ctx.send(f"Error during restart: {str(e)}")
    else:
      # Reset uptime counter even if Music cog not found
      self.st = time.time()
      await ctx.send("Music cog not found. State cleared. Uptime counter reset.")

  @commands.command()
  @commands.has_permissions(administrator=True)
  async def shutdown(self, ctx):
    """Hard restart: Exits bot process (systemd restarts if configured)"""
    await ctx.send("Shutting down bot... (systemd will restart if configured)")
    
    # Clear voice connections first
    music_cog = self.client.get_cog('Music')
    if music_cog:
      try:
        await music_cog.clear_all_voice_connections()
      except Exception as e:
        print(f"Error clearing voice connections during shutdown: {e}")
    
    # Give a moment for the message to send
    await asyncio.sleep(1)
    
    # Close the bot connection gracefully
    await self.client.close()
    
    # Exit with code 0 (systemd will restart if Restart=always is set)
    sys.exit(0)

  @commands.command()
  @commands.has_permissions(administrator=True)
  async def cleanup(self, ctx, *, channel: discord.TextChannel = None):
    """Deletes all bot messages in specified channel (or current if none)"""
    # Use current channel if none specified
    if channel is None:
      channel = ctx.channel
    
    # Check bot permissions
    if not channel.permissions_for(ctx.guild.me).read_message_history:
      return await ctx.send("I don't have permission to read message history in that channel.")
    
    if not channel.permissions_for(ctx.guild.me).manage_messages:
      return await ctx.send("I don't have permission to delete messages in that channel.")
    
    await ctx.send(f"Cleaning up bot messages in {channel.mention}... This may take a moment.")
    
    deleted_count = 0
    try:
      # Fetch messages in batches and delete bot's messages
      async for message in channel.history(limit=None):
        if message.author == self.client.user:
          try:
            await message.delete()
            deleted_count += 1
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
          except discord.errors.NotFound:
            # Message already deleted, skip
            pass
          except discord.errors.Forbidden:
            # No permission to delete this message, skip
            pass
          except Exception as e:
            # Log other errors but continue
            print(f"Error deleting message {message.id}: {e}")
      
      await ctx.send(f"Cleanup complete! Deleted {deleted_count} message(s) from {channel.mention}.")
    except Exception as e:
      await ctx.send(f"Error during cleanup: {str(e)}")
      print(f"Cleanup error: {e}")

  
async def setup(client):
  await client.add_cog(Core(client))