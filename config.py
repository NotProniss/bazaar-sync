import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Discord bot intents
import discord
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

# Constants
COMMAND_PREFIX = '!'
HELP_COMMAND = None

# Environment (dev or prod)
BAZAAR_ENV = os.getenv('BAZAAR_ENV', 'prod').lower()

# Emoji config (set both dev and prod in .env)
EMOJI_SILVER = os.getenv('EMOJI_SILVER_DEV') if BAZAAR_ENV == 'dev' else os.getenv('EMOJI_SILVER_PROD')
EMOJI_GOLD = os.getenv('EMOJI_GOLD_DEV') if BAZAAR_ENV == 'dev' else os.getenv('EMOJI_GOLD_PROD')
EMOJI_PLATINUM = os.getenv('EMOJI_PLATINUM_DEV') if BAZAAR_ENV == 'dev' else os.getenv('EMOJI_PLATINUM_PROD')
EMOJI_COPPER = os.getenv('EMOJI_COPPER_DEV') if BAZAAR_ENV == 'dev' else os.getenv('EMOJI_COPPER_PROD')
