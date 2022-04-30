#!/usr/bin/python3

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

client = commands.Bot(command_prefix = '-')

for filename in os.listdir('./cogs'):
  if filename.endswith('.py'):
    client.load_extension(f'cogs.{filename[:-3]}')

load_dotenv()

client.run(os.getenv('TTGG_TOKEN'))
