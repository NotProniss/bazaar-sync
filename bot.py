import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='bazaar', help='Fetches info from bs-bazaar.com API')
async def bazaar(ctx, endpoint: str = ''):
    """
    Example: !bazaar items
    """
    url = f'https://bs-bazaar.com/api/{endpoint}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        await ctx.send(f'API Response: {data}')
    except Exception as e:
        await ctx.send(f'Error: {e}')

if __name__ == '__main__':
    bot.run(TOKEN)
