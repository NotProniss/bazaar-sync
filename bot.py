def format_price(copper):
    """
    Converts a price in copper to a string with platinum, gold, silver, and copper, using emoji.
    """
    try:
        copper = int(copper)
    except Exception:
        return str(copper)
    parts = []
    platinum = copper // 1000000000
    if platinum:
        parts.append(f"{platinum} <:Platinum:1389673877164261377>")
    copper = copper % 1000000000
    gold = copper // 1000000
    if gold:
        parts.append(f"{gold} <:Gold:1389673853109801081>")
    copper = copper % 1000000
    silver = copper // 1000
    if silver:
        parts.append(f"{silver} <:Silver:1389673819257704579>")
    copper = copper % 1000
    if copper or not parts:
        parts.append(f"{copper} <:Copper:1389673774953140305>")
    return ' '.join(parts)



import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import json
import hashlib
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')




intents = discord.Intents.default()
intents.message_content = True

# Placeholder for bot, will be set to BazaarBot instance in main
bot = None



# All command decorators will be attached to the bot instance after it is created
def register_commands(bot_instance):
    # Redefine all commands here, replacing @bot.command with @bot_instance.command
    @bot_instance.event
    async def on_ready():
        print(f'Logged in as {bot_instance.user}')

    @bot_instance.command(name='testemoji', help='Test custom emoji rendering')
    async def testemoji(ctx):
        test_str = (
            'Test: 1<:Platinum:1127690490117990511> 2<:Gold:1127690488586244177> '
            '3<:Silver:1127690486971498576> 4<:Copper:1127690485272062002>'
        )
        await ctx.send(test_str)

    @bot_instance.command(name='WTS', help='Post a new sell listing to bs-bazaar.com API')
    async def wts(ctx, item: str, quantity: int, price: int, contact: str):
        url = 'https://bs-bazaar.com/api/listings'
        payload = {
            "type": "sell",
            "item": item,
            "quantity": quantity,
            "price": price,
            "contactInfo": contact
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            await ctx.send(f"Sell listing posted successfully! Response: {response.text}")
        except Exception as e:
            await ctx.send(f"Failed to post sell listing: {e}")

    @bot_instance.command(name='WTB', help='Post a new buy listing to bs-bazaar.com API')
    async def wtb(ctx, item: str, quantity: int, price: int, contact: str):
        url = 'https://bs-bazaar.com/api/listings'
        payload = {
            "type": "buy",
            "item": item,
            "quantity": quantity,
            "price": price,
            "contactInfo": contact
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            await ctx.send(f"Buy listing posted successfully! Response: {response.text}")
        except Exception as e:
            await ctx.send(f"Failed to post buy listing: {e}")

    @bot_instance.command(name='bazaar_post', help='Post a new listing to bs-bazaar.com API')
    async def bazaar_post(ctx, order_type: str, item: str, quantity: int, price: int, contact: str, episode: str):
        url = 'https://bs-bazaar.com/api/listings'
        payload = {
            "type": order_type,
            "item": item,
            "quantity": quantity,
            "price": price,
            "contactInfo": contact,
            "episode": episode
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            await ctx.send(f"Listing posted successfully! Response: {response.text}")
        except Exception as e:
            await ctx.send(f"Failed to post listing: {e}")

    @bot_instance.command(name='bazaar', help='Bazaar admin and info commands')
    async def bazaar(ctx, endpoint: str = '', *args):
        if endpoint.lower() == 'help' or endpoint == '':
            help_text = (
                '**Bazaar Bot Admin & Info Commands:**\n'
                '`!bazaar help` — Show this help message.\n'
                '`!bazaar channels <episode> <#channel>` — Set the Discord channel for an episode in this server. Admin only.\n'
                '  Example: `!bazaar channels Hopeport #bazaar-hopeport`\n'
                '\nEpisodes: ' + ', '.join(EPISODES)
            )
            await ctx.send(help_text)
            return
        if endpoint.lower() == 'channels':
            # If no arguments, list all episodes and their assigned channels for this guild
            if len(args) == 0:
                episode_channels = load_episode_channels()
                guild_id = str(ctx.guild.id)
                guild_channels = episode_channels.get(guild_id, {})
                lines = []
                for ep in EPISODES:
                    ch_id = guild_channels.get(ep)
                    if ch_id:
                        ch_obj = ctx.guild.get_channel(int(ch_id))
                        ch_display = ch_obj.mention if ch_obj else f'ID: {ch_id} (not found)'
                    else:
                        ch_display = 'Not set'
                    lines.append(f'**{ep}**: {ch_display}')
                await ctx.send('**Current episode channel assignments:**\n' + '\n'.join(lines))
                return
            # Usage: !bazaar channels <episode> <#channel>
            if not ctx.author.guild_permissions.administrator:
                await ctx.send('You must be a server administrator to use this command.')
                return
            if len(args) != 2:
                await ctx.send(f'Usage: !bazaar channels <episode> <#channel>')
                return
            episode = args[0]
            channel = args[1]
            if episode not in EPISODES:
                await ctx.send(f'Invalid episode. Valid episodes: {", ".join(EPISODES)}')
                return
            # Accept both #channel mention and channel ID
            if channel.startswith('<#') and channel.endswith('>'):
                channel_id = channel[2:-1]
            else:
                channel_id = channel
            try:
                channel_obj = ctx.guild.get_channel(int(channel_id))
            except Exception:
                channel_obj = None
            if not channel_obj or not isinstance(channel_obj, discord.TextChannel):
                await ctx.send('Invalid channel. Please mention a text channel or provide a valid channel ID.')
                return
            # Load, update, and save mapping
            episode_channels = load_episode_channels()
            guild_id = str(ctx.guild.id)
            if guild_id not in episode_channels:
                episode_channels[guild_id] = {}
            episode_channels[guild_id][episode] = str(channel_obj.id)
            save_episode_channels(episode_channels)
            await ctx.send(f'Channel for episode **{episode}** set to {channel_obj.mention} for this server.')
            return
        # Optionally, add more subcommands here
        await ctx.send('Unknown or incomplete command. For channel setup: !bazaar channels <episode> <#channel>')

    pass

EPISODES = [
    "Hopeport",
    "Hopeforest",
    "Mine of Mantuban",
    "Crenopolis",
    "Stonemaw Hill",
    "Combat"
]
CHANNELS_FILE = 'episode_channels.json'
LISTING_MESSAGES_FILE = 'listing_messages.json'

def load_episode_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Backward compatibility: if flat mapping, convert to per-guild
            if all(isinstance(v, (str, type(None))) for v in data.values()):
                # Assume single-server, migrate to new format with dummy guild id 'global'
                return {'global': data}
            return data
    return {}

def save_episode_channels(mapping):
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def load_listing_messages():
    if os.path.exists(LISTING_MESSAGES_FILE):
        with open(LISTING_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_listing_messages(mapping):
    with open(LISTING_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def get_listing_id(entry):
    # Use a hash of the relevant fields as a unique ID
    key = f"{entry.get('type','')}|{entry.get('item','')}|{entry.get('quantity','')}|{entry.get('price','')}|{entry.get('contactInfo','')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()



if __name__ == '__main__':
    import asyncio
    import subprocess




    class BazaarBot(commands.Bot):
        async def setup_hook(self):
            print("[Bazaar Bot] setup_hook called")
            try:
                print("[Bazaar Bot] Running scrape.py...")
                subprocess.run(['python', 'scrape.py'], check=True)
                print("[Bazaar Bot] scrape.py completed.")
            except Exception as e:
                print(f"[Bazaar Bot] scrape.py failed: {e}")

            async def listings_loop():
                print("[Bazaar Bot] listings_loop started")
                await self.wait_until_ready()
                print("[Bazaar Bot] listings_loop: bot ready")
                while not self.is_closed():
                    try:
                        print("[Bazaar Bot] listings_loop: fetching listings...")
                        response = requests.get('https://bs-bazaar.com/api/listings')
                        response.raise_for_status()
                        listings = response.json()
                        with open('bazaar_listings.json', 'w', encoding='utf-8') as f:
                            json.dump(listings, f, ensure_ascii=False, indent=2)
                        # Run merge_episodes.py to add episode info (async, non-blocking)
                        try:
                            print("[Bazaar Bot] Running merge_episodes.py to add episode info (async)...")
                            proc = await asyncio.create_subprocess_exec(
                                'python', 'merge_episodes.py',
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await proc.communicate()
                            if proc.returncode == 0:
                                print("[Bazaar Bot] merge_episodes.py completed.")
                            else:
                                print(f"[Bazaar Bot] merge_episodes.py failed with code {proc.returncode}: {stderr.decode().strip()}")
                        except Exception as merge_err:
                            print(f"[Bazaar Bot] merge_episodes.py failed: {merge_err}")
                        # Reload listings with episode info
                        with open('bazaar_listings.json', 'r', encoding='utf-8') as f:
                            listings = json.load(f)
                        # If combatCategory is not empty, set episode to 'Combat'
                        for l in listings:
                            if l.get('combatCategory', '').strip():
                                l['episode'] = 'Combat'
                        episode_channels = load_episode_channels()
                        listing_messages = load_listing_messages()
                        # Track summary messages by channel and episode: {channel_id: {episode: msg_id}}
                        new_listing_messages = {k: dict(v) for k, v in listing_messages.items()}
                        all_current_ids = set()
                        any_changes = False
                        # Multi-guild support: iterate over all guilds and their episode-channel mappings
                        for guild in self.guilds:
                            guild_id = str(guild.id)
                            guild_channels = episode_channels.get(guild_id, {})
                            for episode in EPISODES:
                                channel_id = guild_channels.get(episode)
                                if not channel_id:
                                    print(f"[Bazaar Bot] No channel set for episode '{episode}' in guild {guild_id}")
                                    continue
                                try:
                                    channel = self.get_channel(int(channel_id))
                                except Exception as e:
                                    print(f"[Bazaar Bot] Invalid channel ID {channel_id} for episode '{episode}' in guild {guild_id}: {e}")
                                    continue
                                print(f"[Bazaar Bot] Guild {guild_id} Episode '{episode}' channel_id: {channel_id}, channel: {channel}")
                                if not isinstance(channel, discord.TextChannel):
                                    print(f"[Bazaar Bot] Channel {channel_id} is not a TextChannel or not found.")
                                    continue
                                episode_listings = [l for l in listings if l.get('episode') == episode]
                                prev_msgs = listing_messages.get(str(channel_id), {})
                                prev_msg_id = prev_msgs.get(episode)
                                prev_content = None
                                if episode_listings:
                                    # Group and sort listings
                                    selling = [l for l in episode_listings if l.get('type', '').lower() == 'sell']
                                    buying = [l for l in episode_listings if l.get('type', '').lower() == 'buy']
                                    selling.sort(key=lambda l: l.get('item', ''))
                                    buying.sort(key=lambda l: l.get('item', ''))
                                    def listing_line(l):
                                        type_str = '[WTS]' if l['type'].lower() == 'sell' else '[WTB]'
                                        price = l['price']
                                        price_mode = l.get('priceMode', '').strip().lower()
                                        price_str = format_price(price)
                                        if price_mode == 'each':
                                            price_str += ' EA'
                                        elif price_mode == 'total':
                                            price_str += ' Total'
                                        return f"{type_str} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}"
                                    summary = f"**Listings from [the Bazaar](https://bs-bazaar.com)**\n"
                                    if selling:
                                        summary += "\n**Selling**\n" + "\n".join(listing_line(l) for l in selling)
                                    if buying:
                                        summary += "\n**Buying**\n" + "\n".join(listing_line(l) for l in buying)
                                    if prev_msg_id:
                                        try:
                                            prev_msg = await channel.fetch_message(prev_msg_id)
                                            prev_content = prev_msg.content
                                        except Exception:
                                            prev_content = None
                                    if summary.strip() != (prev_content or '').strip():
                                        any_changes = True
                                        # Content changed, post new summary and delete old if exists
                                        if prev_msg_id and prev_content:
                                            try:
                                                await prev_msg.delete()
                                            except Exception as del_err:
                                                print(f"[Bazaar Bot] Could not delete old summary message {prev_msg_id} in channel {channel_id}: {del_err}")
                                        try:
                                            msg = await channel.send(summary)
                                            print(f"[Bazaar Bot] Posted/updated summary to channel {channel_id}")
                                            if str(channel_id) not in new_listing_messages:
                                                new_listing_messages[str(channel_id)] = {}
                                            new_listing_messages[str(channel_id)][episode] = str(msg.id)
                                            all_current_ids.add(str(msg.id))
                                        except Exception as send_err:
                                            print(f"[Bazaar Bot] Failed to send summary to channel {channel_id}: {send_err}")
                                    else:
                                        # No change, keep the old message id
                                        if prev_msg_id:
                                            if str(channel_id) not in new_listing_messages:
                                                new_listing_messages[str(channel_id)] = {}
                                            new_listing_messages[str(channel_id)][episode] = str(prev_msg_id)
                                            all_current_ids.add(str(prev_msg_id))
                                # If there are no listings for this episode, delete summary if it exists
                                if not episode_listings and prev_msg_id:
                                    try:
                                        if isinstance(channel, discord.TextChannel):
                                            old_msg = await channel.fetch_message(prev_msg_id)
                                            await old_msg.delete()
                                            print(f"[Bazaar Bot] Deleted old message {prev_msg_id} in channel {channel_id}")
                                            # Remove from tracking since it was deleted
                                            if str(channel_id) in new_listing_messages and episode in new_listing_messages[str(channel_id)]:
                                                del new_listing_messages[str(channel_id)][episode]
                                                if not new_listing_messages[str(channel_id)]:
                                                    del new_listing_messages[str(channel_id)]
                                    except Exception as del_err:
                                        print(f"[Bazaar Bot] Could not delete message {prev_msg_id} in channel {channel_id}: {del_err}")
                        # Only delete old messages if there were changes
                        if any_changes:
                            for channel_id, channel_msgs in listing_messages.items():
                                channel = self.get_channel(int(channel_id))
                                if not channel:
                                    continue
                                for episode, old_msg_id in channel_msgs.items():
                                    if str(old_msg_id) not in all_current_ids:
                                        try:
                                            old_msg = await channel.fetch_message(old_msg_id)
                                            await old_msg.delete()
                                            print(f"[Bazaar Bot] Deleted old message {old_msg_id} in channel {channel_id}")
                                        except Exception as del_err:
                                            print(f"[Bazaar Bot] Could not delete message {old_msg_id} in channel {channel_id}: {del_err}")
                        save_listing_messages(new_listing_messages)
                    except Exception as e:
                        print(f"[Bazaar Bot] listings_loop error: {e}")
                    # Always sleep at the end of the loop, even after exceptions
                    await asyncio.sleep(60)  # 1 minute (shortened for testing)

            self.loop.create_task(listings_loop())

    if not TOKEN:
        print("[Bazaar Bot] DISCORD_TOKEN not set in .env!")
    else:
        bot = BazaarBot(command_prefix='!', intents=intents, help_command=None)
        register_commands(bot)
        try:
            asyncio.run(bot.start(TOKEN))
        except KeyboardInterrupt:
            print("[Bazaar Bot] Bot stopped by user (Ctrl+C)")
