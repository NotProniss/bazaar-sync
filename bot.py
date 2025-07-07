# --- Imports from new modules ---
import discord
import asyncio
import requests
import json
import subprocess
from discord.ext import commands
from config import TOKEN, intents
from commands import register_commands
from listing_manager import (
    format_price, get_listing_id, load_episode_channels, save_episode_channels,
    load_listing_messages, save_listing_messages, EPISODES
)


# --- BazaarBot class defined at top level ---

class BazaarBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Only log init in debug mode if needed
        super().__init__(*args, **kwargs)
        self.startup_complete = False

    async def on_ready(self):
        print("[Bazaar Bot] Bot is ready.")
        try:
            if self.user:
                print(f"[Bazaar Bot] Logged in as {self.user} (ID: {self.user.id})")
            else:
                print(f"[Bazaar Bot] Logged in as Unknown user (self.user is None)")
            print("[Bazaar Bot] Updating listings from API...")
            subprocess.run(['python', 'scrape.py'], check=True)
            print("[Bazaar Bot] Listings updated.")

            async def listings_loop():
                while not self.is_closed():
                    try:
                        print("[Bazaar Bot] Fetching latest listings from API...")
                        response = requests.get('https://bs-bazaar.com/api/listings')
                        response.raise_for_status()
                        listings = response.json()
                        with open('bazaar_listings.json', 'w', encoding='utf-8') as f:
                            json.dump(listings, f, ensure_ascii=False, indent=2)
                        # Run merge_episodes.py to add episode info (async, non-blocking)
                        try:
                            print("[Bazaar Bot] Adding episode info (merge_episodes.py)...")
                            proc = await asyncio.create_subprocess_exec(
                                'python', 'merge_episodes.py',
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await proc.communicate()
                            if stdout:
                                print(f"[merge_episodes.py]: {stdout.decode().strip()}")
                            if stderr:
                                print(f"[merge_episodes.py][stderr]: {stderr.decode().strip()}")
                            if proc.returncode == 0:
                                print("[Bazaar Bot] merge_episodes.py completed.")
                            else:
                                print(f"[Bazaar Bot] merge_episodes.py failed (code {proc.returncode})")
                        except Exception as merge_err:
                            print(f"[Bazaar Bot] merge_episodes.py failed: {merge_err}")
                        with open('bazaar_listings.json', 'r', encoding='utf-8') as f:
                            listings = json.load(f)
                        for l in listings:
                            if l.get('combatCategory', '').strip():
                                l['episode'] = 'Combat'
                        episode_channels = load_episode_channels()
                        listing_messages = load_listing_messages()
                        new_listing_messages = {k: dict(v) for k, v in listing_messages.items()}
                        all_current_ids = set()
                        any_changes = False
                        for guild in self.guilds:
                            guild_id = str(guild.id)
                            guild_channels = episode_channels.get(guild_id, {})
                            for episode in EPISODES:
                                channel_id = guild_channels.get(episode)
                                episode_listings = [l for l in listings if l.get('episode') == episode]
                                if not channel_id:
                                    # Only log missing channels for the first loop if there are listings
                                    if episode_listings:
                                        print(f"[Bazaar Bot] No channel set for episode '{episode}' in guild {guild_id}")
                                    continue
                                try:
                                    channel = self.get_channel(int(channel_id))
                                except Exception as e:
                                    print(f"[Bazaar Bot] Invalid channel ID {channel_id} for episode '{episode}' in guild {guild_id}: {e}")
                                    continue
                                # if not isinstance(channel, discord.TextChannel):
                                #     print(f"[Bazaar Bot] Channel {channel_id} is not a TextChannel or not found.")
                                if not isinstance(channel, discord.TextChannel):
                                    continue
                                # SELLING
                                selling = [l for l in episode_listings if l.get('type', '').upper() == 'SELL']
                                buying = [l for l in episode_listings if l.get('type', '').upper() == 'BUY']
                                new_listing_ids = []
                                # SELLING
                                if selling:
                                    new_sell_listings = []
                                    for l in selling:
                                        listing_id = get_listing_id(l)
                                        already_posted = False
                                        msgid = None
                                        if str(channel_id) in new_listing_messages:
                                            lidmap = new_listing_messages[str(channel_id)].get(f"{episode}_listing_ids", {})
                                            if isinstance(lidmap, dict) and listing_id in lidmap:
                                                msgid = new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id]
                                                try:
                                                    await channel.fetch_message(int(msgid))
                                                    already_posted = True
                                                except discord.NotFound:
                                                    print(f"[Bazaar Bot] Will re-post missing SELL listing: {l['item']} x{l['quantity']} (id={listing_id}) in channel {channel_id}")
                                                    del new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id]
                                                except Exception as fetch_err:
                                                    print(f"[Bazaar Bot] Error fetching message {msgid} for listing {listing_id}: {fetch_err}")
                                        if already_posted and msgid:
                                            try:
                                                msg_obj = await channel.fetch_message(int(msgid))
                                                # Compose the new content for the listing
                                                type_str = '[WTS]' if l.get('type', '').upper() == 'SELL' else '[WTB]'
                                                price = l['price']
                                                price_mode = l.get('priceMode', '').strip().lower()
                                                price_str = format_price(price)
                                                if price_mode == 'each':
                                                    price_str += ' EA'
                                                elif price_mode == 'total':
                                                    price_str += ' Total'
                                                line = f"{type_str} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}"
                                                if msg_obj.content != line:
                                                    await msg_obj.edit(content=line)
                                                    print(f"[Bazaar Bot] Edited existing listing (msg id={msgid}) in channel {channel_id}: {line}")
                                            except Exception as edit_err:
                                                print(f"[Bazaar Bot] Failed to edit listing message {msgid} in channel {channel_id}: {edit_err}")
                                            new_listing_ids.append(msgid)
                                            all_current_ids.add(msgid)
                                        if not already_posted:
                                            new_sell_listings.append((l, listing_id))
                                    if new_sell_listings:
                                        try:
                                            header = "**SELL** Listings from the [Bazaar](https://bs-bazaar.com)"
                                            msg = await channel.send(header)
                                            print(f"[Bazaar Bot] Posted SELL header in channel {channel_id} (msg id={msg.id})")
                                            new_listing_ids.append(str(msg.id))
                                            all_current_ids.add(str(msg.id))
                                            if str(channel_id) not in new_listing_messages:
                                                new_listing_messages[str(channel_id)] = {}
                                            new_listing_messages[str(channel_id)][f"{episode}_sell_header"] = str(msg.id)
                                            any_changes = True
                                        except Exception as send_err:
                                            print(f"[Bazaar Bot] Failed to send selling header to channel {channel_id}: {send_err}")
                                        for l, listing_id in new_sell_listings:
                                            type_str = '[WTS]'
                                            price = l['price']
                                            price_mode = l.get('priceMode', '').strip().lower()
                                            price_str = format_price(price)
                                            if price_mode == 'each':
                                                price_str += ' EA'
                                            elif price_mode == 'total':
                                                price_str += ' Total'
                                            line = f"{type_str} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}"
                                            try:
                                                msg = await channel.send(line)
                                                print(f"[Bazaar Bot] Posted SELL listing: {line} (msg id={msg.id}) in channel {channel_id}")
                                                new_listing_ids.append(str(msg.id))
                                                all_current_ids.add(str(msg.id))
                                                if str(channel_id) not in new_listing_messages:
                                                    new_listing_messages[str(channel_id)] = {}
                                                if f"{episode}_listing_ids" not in new_listing_messages[str(channel_id)]:
                                                    new_listing_messages[str(channel_id)][f"{episode}_listing_ids"] = {}
                                                new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id] = str(msg.id)
                                                any_changes = True
                                            except Exception as send_err:
                                                print(f"[Bazaar Bot] Failed to send listing to channel {channel_id}: {send_err}")
                                    else:
                                        header_key = f"{episode}_sell_header"
                                        old_header_id = new_listing_messages.get(str(channel_id), {}).get(header_key)
                                        if old_header_id:
                                            try:
                                                msg_obj = await channel.fetch_message(int(old_header_id))
                                                await msg_obj.delete()
                                                print(f"[Bazaar Bot] Deleted old SELL header (msg id={old_header_id}) in channel {channel_id}")
                                            except Exception as cleanup_err:
                                                print(f"[Bazaar Bot] Failed to delete old SELL header {old_header_id} in channel {channel_id}: {cleanup_err}")
                                            del new_listing_messages[str(channel_id)][header_key]
                                # BUYING
                                if buying:
                                    new_buy_listings = []
                                    for l in buying:
                                        listing_id = get_listing_id(l)
                                        already_posted = False
                                        msgid = None
                                        if str(channel_id) in new_listing_messages:
                                            lidmap = new_listing_messages[str(channel_id)].get(f"{episode}_listing_ids", {})
                                            if isinstance(lidmap, dict) and listing_id in lidmap:
                                                msgid = new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id]
                                                try:
                                                    await channel.fetch_message(int(msgid))
                                                    already_posted = True
                                                except discord.NotFound:
                                                    print(f"[Bazaar Bot] Will re-post missing BUY listing: {l['item']} x{l['quantity']} (id={listing_id}) in channel {channel_id}")
                                                    del new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id]
                                                except Exception as fetch_err:
                                                    print(f"[Bazaar Bot] Error fetching message {msgid} for listing {listing_id}: {fetch_err}")
                                        if already_posted and msgid:
                                            try:
                                                msg_obj = await channel.fetch_message(int(msgid))
                                                # Compose the new content for the listing
                                                type_str = '[WTS]' if l.get('type', '').upper() == 'SELL' else '[WTB]'
                                                price = l['price']
                                                price_mode = l.get('priceMode', '').strip().lower()
                                                price_str = format_price(price)
                                                if price_mode == 'each':
                                                    price_str += ' EA'
                                                elif price_mode == 'total':
                                                    price_str += ' Total'
                                                line = f"{type_str} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}"
                                                if msg_obj.content != line:
                                                    await msg_obj.edit(content=line)
                                                    print(f"[Bazaar Bot] Edited existing listing (msg id={msgid}) in channel {channel_id}: {line}")
                                            except Exception as edit_err:
                                                print(f"[Bazaar Bot] Failed to edit listing message {msgid} in channel {channel_id}: {edit_err}")
                                            new_listing_ids.append(msgid)
                                            all_current_ids.add(msgid)
                                        if not already_posted:
                                            new_buy_listings.append((l, listing_id))
                                    if new_buy_listings:
                                        try:
                                            header = "**BUY** Listings from the [Bazaar](https://bs-bazaar.com)"
                                            msg = await channel.send(header)
                                            print(f"[Bazaar Bot] Posted BUY header in channel {channel_id} (msg id={msg.id})")
                                            new_listing_ids.append(str(msg.id))
                                            all_current_ids.add(str(msg.id))
                                            if str(channel_id) not in new_listing_messages:
                                                new_listing_messages[str(channel_id)] = {}
                                            new_listing_messages[str(channel_id)][f"{episode}_buy_header"] = str(msg.id)
                                            any_changes = True
                                        except Exception as send_err:
                                            print(f"[Bazaar Bot] Failed to send buying header to channel {channel_id}: {send_err}")
                                        for l, listing_id in new_buy_listings:
                                            type_str = '[WTB]'
                                            price = l['price']
                                            price_mode = l.get('priceMode', '').strip().lower()
                                            price_str = format_price(price)
                                            if price_mode == 'each':
                                                price_str += ' EA'
                                            elif price_mode == 'total':
                                                price_str += ' Total'
                                            line = f"{type_str} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}"
                                            try:
                                                msg = await channel.send(line)
                                                print(f"[Bazaar Bot] Posted BUY listing: {line} (msg id={msg.id}) in channel {channel_id}")
                                                new_listing_ids.append(str(msg.id))
                                                all_current_ids.add(str(msg.id))
                                                if str(channel_id) not in new_listing_messages:
                                                    new_listing_messages[str(channel_id)] = {}
                                                if f"{episode}_listing_ids" not in new_listing_messages[str(channel_id)]:
                                                    new_listing_messages[str(channel_id)][f"{episode}_listing_ids"] = {}
                                                new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][listing_id] = str(msg.id)
                                                any_changes = True
                                            except Exception as send_err:
                                                print(f"[Bazaar Bot] Failed to send listing to channel {channel_id}: {send_err}")
                                    else:
                                        header_key = f"{episode}_buy_header"
                                        old_header_id = new_listing_messages.get(str(channel_id), {}).get(header_key)
                                        if old_header_id:
                                            try:
                                                msg_obj = await channel.fetch_message(int(old_header_id))
                                                await msg_obj.delete()
                                                print(f"[Bazaar Bot] Deleted old BUY header (msg id={old_header_id}) in channel {channel_id}")
                                            except Exception as cleanup_err:
                                                print(f"[Bazaar Bot] Failed to delete old BUY header {old_header_id} in channel {channel_id}: {cleanup_err}")
                                            del new_listing_messages[str(channel_id)][header_key]
                                # CLEANUP: Remove old messages for listings that are no longer present
                                # --- BEGIN CLEANUP LOGIC (by listing_id) ---
                                lidmap = new_listing_messages.get(str(channel_id), {}).get(f"{episode}_listing_ids", {})
                                # Build set of current valid listing_ids for this episode
                                current_listing_ids = set(get_listing_id(l) for l in episode_listings)
                                ids_to_remove = []
                                for old_listing_id, old_msg_id in list(lidmap.items()):
                                    if old_listing_id not in current_listing_ids:
                                        ids_to_remove.append((old_listing_id, old_msg_id))
                                for old_listing_id, old_msg_id in ids_to_remove:
                                    try:
                                        msg_obj = await channel.fetch_message(int(old_msg_id))
                                        await msg_obj.delete()
                                        print(f"[Bazaar Bot] Deleted old listing (msg id={old_msg_id}) for id={old_listing_id} in channel {channel_id}")
                                    except Exception as cleanup_err:
                                        print(f"[Bazaar Bot] Failed to delete old message {old_msg_id} in channel {channel_id}: {cleanup_err}")
                                    del new_listing_messages[str(channel_id)][f"{episode}_listing_ids"][old_listing_id]
                                # --- END CLEANUP LOGIC ---
                        save_listing_messages(new_listing_messages)
                    except Exception as e:
                        print(f"[Bazaar Bot] listings_loop error: {e}")
                    import datetime
                    sleep_seconds = 180
                    for remaining in range(sleep_seconds, 0, -1):
                        if remaining % 30 == 0 or remaining <= 5:
                            now = datetime.datetime.now().strftime('%H:%M:%S')
                            print(f"[Bazaar Bot][{now}] Next update in {remaining} seconds...")
                        else:
                            print(f"[Bazaar Bot] Next update in {remaining} seconds...", end='\r')
                        await asyncio.sleep(1)
                    print()  # Newline after countdown

            self.loop.create_task(listings_loop())
        except Exception as err:
            print(f"[Bazaar Bot] on_ready error: {err}")


# --- Main block ---
if __name__ == '__main__':
    # Minimal startup logs
    if not TOKEN:
        print("[Bazaar Bot] DISCORD_TOKEN not set in .env!")
    else:
        bot = BazaarBot(command_prefix='!', intents=intents, help_command=None)
        register_commands(bot)
        try:
            bot.run(TOKEN)
        except KeyboardInterrupt:
            print("[Bazaar Bot] Bot stopped by user (Ctrl+C)")
