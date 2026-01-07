#!/usr/bin/env python3

import discord
from discord.ext import commands
import os
import argparse
import json
import asyncio
import shutil 
import sys 

parser = argparse.ArgumentParser(description='Youtube Discord Bot')
CONFIG_KEYS = ["TOKEN", "project_path"] # Expected config keys

intents = discord.Intents.all()

client = commands.Bot(command_prefix = '-', intents = intents ) # Declare bot

if not shutil.which('ffmpeg'):
    print("ERROR: FFmpeg is not installed on this system.")
    print("Please install FFmpeg using: sudo apt install ffmpeg")
    sys.exit(1)

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
        sys.exit(1)
      
      project_path = config_json["project_path"]
      # Validate project_path exists
      if not os.path.isdir(project_path):
        print("Error: project_path '{}' does not exist or is not a directory".format(project_path))
        sys.exit(1)
      
      return config_json["TOKEN"], project_path
  except IOError as e:
    print('Failed to open config file: {} - {}'.format(config_file_path, str(e)))
    sys.exit(1)
  except json.JSONDecodeError as e:
    print('Failed to parse config file: {} - {}'.format(config_file_path, str(e)))
    sys.exit(1)

async def parse_cogs(project_path):
  print("Parsing cogs...")
  # Parse cog files
  cogs_dir = os.path.join(project_path, 'cogs')
  if not os.path.isdir(cogs_dir):
    print("Error: cogs directory '{}' does not exist".format(cogs_dir))
    sys.exit(1)
  
  count = 0
  for filename in os.listdir(cogs_dir):
    if filename.endswith('.py') and not filename.startswith('__'):
      try:
        await client.load_extension(f'cogs.{filename[:-3]}')
        count += 1
      except Exception as e:
        print("Warning: Failed to load cog '{}': {}".format(filename, str(e)))
  print("   parsed {} cogs".format(count))


async def main():
  async with client:
    config_file_path = parse_args()

    TOKEN, project_path = parse_config(config_file_path)

    await parse_cogs(project_path)
    await client.start(TOKEN)

if __name__ == "__main__":
  asyncio.run(main())
