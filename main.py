#!/usr/bin/python3

import discord
from discord.ext import commands
import sys
import os
import argparse
import json
import asyncio

parser = argparse.ArgumentParser(description='Youtube Discord Bot')
CONFIG_KEYS = ["TOKEN", "project_path"] # Expected config keys

intents = discord.Intents.all()

client = commands.Bot(command_prefix = '-', intents = intents ) # Declare bot

def parse_args():
  print("Parsing command line args...")
  parser.add_argument('config_file', type=str,
                    help='Required configuration file')
  args = parser.parse_args()
  return args.config_file

def parse_config(config_file_path):
  print('Parsing config file \"{}\"'.format(config_file_path))

  # Parse config file for path/token
  try: 
    with open(config_file_path, 'r') as f:
      config_json = json.load(f)
      missing_keys = list(set(CONFIG_KEYS) - set(config_json.keys()))
      if missing_keys: 
        print("Missing following keys from config: {}".format(missing_keys))
        exit(-1)
      return config_json["TOKEN"], config_json["project_path"]
  except IOError:
    print('Failed to open config file: {}'.format(config_file_path))
    exit(-1)

async def parse_cogs(project_path):
  print("Parsing cogs...")
  # Parse cog files
  count = 0
  for filename in os.listdir('{}/cogs'.format(project_path)):
    if filename.endswith('.py'):
      count += 1
      await client.load_extension(f'cogs.{filename[:-3]}')
  print("   parsed {} cogs".format(count))


async def main():
  async with client:
    config_file_path = parse_args()

    TOKEN, project_path = parse_config(config_file_path)

    await parse_cogs(project_path)
    await client.start(TOKEN)

if __name__ == "__main__":
  asyncio.run(main())
