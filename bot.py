# --- Imports from new modules ---
import discord
import asyncio
import requests
import json
import subprocess
import logging
from discord.ext import commands
from config import TOKEN, intents
from commands import register_commands
from listing_manager import (
    format_price, get_listing_id, load_episode_channels, save_episode_channels,
    load_listing_messages, save_listing_messages, EPISODES
)

# --- Setup logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bazaarbot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bazaarbot")


# --- BazaarBot class defined at top level ---

class BazaarBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Only log init in debug mode if needed
        super().__init__(*args, **kwargs)
        self.startup_complete = False

    async def on_ready(self):
        logger.info("[Bazaar Bot] Bot is ready.")
        try:
            if self.user:
                logger.info(f"[Bazaar Bot] Logged in as {self.user} (ID: {self.user.id})")
            else:
                logger.info(f"[Bazaar Bot] Logged in as Unknown user (self.user is None)")
            logger.info("[Bazaar Bot] Updating listings from API...")
            subprocess.run(['python', 'scrape.py'], check=True)
            logger.info("[Bazaar Bot] Listings updated.")

            async def listings_loop():
                import datetime, time, os
                RESET_FILE = 'last_reset.json'
                RESET_INTERVAL = 24 * 60 * 60  # 24 hours
                while not self.is_closed():
                    try:
                        # --- Daily reset logic ---
                        now_ts = int(time.time())
                        last_reset = 0
                        if os.path.exists(RESET_FILE):
                            try:
                                with open(RESET_FILE, 'r', encoding='utf-8') as f:
                                    import json as _json
                                    last_reset = _json.load(f).get('last_reset', 0)
                            except Exception:
                                last_reset = 0
                        do_reset = now_ts - last_reset > RESET_INTERVAL
                        if do_reset:
                            logger.info('[Bazaar Bot] Performing daily reset: deleting all listing messages...')
                            listing_messages = load_listing_messages()
                            for channel_id, msgdict in listing_messages.items():
                                for key, msg_ids in list(msgdict.items()):
                                    if isinstance(msg_ids, str):
                                        msg_ids = [msg_ids]
                                    for msg_id in msg_ids:
                                        try:
                                            channel = self.get_channel(int(channel_id))
                                            if channel and isinstance(channel, discord.TextChannel):
                                                msg_obj = await channel.fetch_message(int(msg_id))
                                                await msg_obj.delete()
                                                logger.info(f"[Bazaar Bot] Deleted message {msg_id} in channel {channel_id} for daily reset.")
                                        except Exception as e:
                                            logger.warning(f"[Bazaar Bot] Could not delete message {msg_id} in channel {channel_id}: {e}")
                            # Clear all listing messages
                            with open('listing_messages.json', 'w', encoding='utf-8') as f:
                                f.write('{}')
                            with open(RESET_FILE, 'w', encoding='utf-8') as f:
                                _json.dump({'last_reset': now_ts}, f)
                            logger.info('[Bazaar Bot] Daily reset complete.')
                        # --- Normal update logic ---
                        logger.info("[Bazaar Bot] Fetching latest listings from API...")
                        response = requests.get('https://bs-bazaar.com/api/listings')
                        response.raise_for_status()
                        listings = response.json()
                        with open('bazaar_listings.json', 'w', encoding='utf-8') as f:
                            json.dump(listings, f, ensure_ascii=False, indent=2)
                        # Run merge_episodes.py to add episode info (async, non-blocking)
                        try:
                            logger.info("[Bazaar Bot] Adding episode info (merge_episodes.py)...")
                            proc = await asyncio.create_subprocess_exec(
                                'python', 'merge_episodes.py',
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await proc.communicate()
                            if stdout:
                                logger.info(f"[merge_episodes.py]: {stdout.decode().strip()}")
                            if stderr:
                                logger.warning(f"[merge_episodes.py][stderr]: {stderr.decode().strip()}")
                            if proc.returncode == 0:
                                logger.info("[Bazaar Bot] merge_episodes.py completed.")
                            else:
                                logger.error(f"[Bazaar Bot] merge_episodes.py failed (code {proc.returncode})")
                        except Exception as merge_err:
                            logger.error(f"[Bazaar Bot] merge_episodes.py failed: {merge_err}")
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
                        from listing_manager import load_bank_channels
                        bank_channels = load_bank_channels()
                        # --- MAIN LOOP: For each guild and episode, update Discord messages ---
                        for guild in self.guilds:
                            guild_id = str(guild.id)
                            guild_channels = episode_channels.get(guild_id, {})
                            # --- EPISODE CHANNELS ---
                            missing_channels = [ep for ep in EPISODES if not guild_channels.get(ep)]
                            if len(missing_channels) == len(EPISODES):
                                logger.warning(f"[Bazaar Bot] No episode channels are set for guild {guild_id}")
                            else:
                                for episode in EPISODES:
                                    channel_id = guild_channels.get(episode)
                                    episode_listings = [l for l in listings if l.get('episode') == episode]
                                    if not channel_id:
                                        if episode_listings:
                                            logger.warning(f"[Bazaar Bot] No channel set for episode '{episode}' in guild {guild_id}")
                                        continue
                                    try:
                                        channel = self.get_channel(int(channel_id))
                                    except Exception as e:
                                        logger.error(f"[Bazaar Bot] Invalid channel ID {channel_id} for episode '{episode}' in guild {guild_id}: {e}")
                                        continue
                                    if not isinstance(channel, discord.TextChannel):
                                        continue
                                    # SELLING
                                    selling = [l for l in episode_listings if l.get('type', '').upper() == 'SELL']
                                    buying = [l for l in episode_listings if l.get('type', '').upper() == 'BUY']
                                    # --- SELLING ---
                                    await self._update_listings_for_type(
                                        channel, episode, 'SELL', selling, new_listing_messages, all_current_ids, logger
                                    )
                                    # --- BUYING ---
                                    await self._update_listings_for_type(
                                        channel, episode, 'BUY', buying, new_listing_messages, all_current_ids, logger
                                    )
                            # --- BANK CHANNELS ---
                            bank_guild_channels = bank_channels.get(guild_id, {})
                            # Group listings by bank name
                            bank_listings_by_name = {}
                            for l in listings:
                                bank_name = l.get('bank')
                                if bank_name:
                                    bank_listings_by_name.setdefault(bank_name, []).append(l)
                            from bank_names import BANKS
                            for bank_name in BANKS:
                                bank_listings = bank_listings_by_name.get(bank_name, [])
                                channel_id = bank_guild_channels.get(bank_name)
                                if not channel_id:
                                    continue
                                try:
                                    bank_channel = self.get_channel(int(channel_id))
                                except Exception as e:
                                    logger.error(f"[Bazaar Bot] Invalid bank channel ID {channel_id} for bank '{bank_name}' in guild {guild_id}: {e}")
                                    continue
                                if not isinstance(bank_channel, discord.TextChannel):
                                    continue
                                # Only post a header if there are listings for this bank
                                selling = [l for l in bank_listings if l.get('type', '').upper() == 'SELL']
                                buying = [l for l in bank_listings if l.get('type', '').upper() == 'BUY']
                                if selling or buying:
                                    header_key = f"Bank:{bank_name}_header"
                                    channel_id_str = str(bank_channel.id)
                                    if channel_id_str not in new_listing_messages:
                                        new_listing_messages[channel_id_str] = {}
                                    if header_key not in new_listing_messages[channel_id_str]:
                                        try:
                                            header = f"__**{bank_name}**__"
                                            msg = await bank_channel.send(header)
                                            logger.info(f"[Bazaar Bot] Posted bank header for {bank_name} in channel {channel_id_str} (msg id={msg.id})")
                                            new_listing_messages[channel_id_str][header_key] = str(msg.id)
                                            all_current_ids.add(str(msg.id))
                                            await asyncio.sleep(1)
                                        except Exception as send_err:
                                            logger.error(f"[Bazaar Bot] Failed to send bank header to channel {channel_id_str}: {send_err}")
                                # Post listings under the bank header (always attempt, but header will only exist if listings exist)
                                await self._update_listings_for_type(
                                    bank_channel, f'{bank_name}', 'SELL', selling, new_listing_messages, all_current_ids, logger
                                )
                                await self._update_listings_for_type(
                                    bank_channel, f'{bank_name}', 'BUY', buying, new_listing_messages, all_current_ids, logger
                                )
                        save_listing_messages(new_listing_messages)
                    except Exception as e:
                        logger.error(f"[Bazaar Bot] listings_loop error: {e}")
                    sleep_seconds = 180
                    # Calculate time until next daily reset
                    next_reset_in = 0
                    try:
                        with open(RESET_FILE, 'r', encoding='utf-8') as f:
                            import json as _json
                            last_reset = _json.load(f).get('last_reset', 0)
                        now_ts = int(time.time())
                        next_reset_in = max(0, (last_reset + RESET_INTERVAL) - now_ts)
                    except Exception:
                        next_reset_in = RESET_INTERVAL
                    for remaining in range(sleep_seconds, 0, -1):
                        now = datetime.datetime.now().strftime('%H:%M:%S')
                        # Show both update and daily reset countdowns
                        reset_h = next_reset_in // 3600
                        reset_m = (next_reset_in % 3600) // 60
                        reset_s = next_reset_in % 60
                        print(f"[Bazaar Bot][{now}] Next update in {remaining}s | Daily reset in {reset_h:02}:{reset_m:02}:{reset_s:02}   ", end='\r')
                        await asyncio.sleep(1)
                        next_reset_in = max(0, next_reset_in - 1)
                    print()  # Newline after countdown

            # Add helper method for updating listings by type
            async def _update_listings_for_type(self, channel, episode, type_str, listings, new_listing_messages, all_current_ids, logger):
                # One or more messages per bank/episode/type, split if >1500 chars
                key = f"{episode}_{type_str.lower()}_groupmsg"
                channel_id = str(channel.id)
                MAX_LEN = 1500
                # Compose all lines
                if not listings:
                    # No listings: delete all group messages if they exist
                    msg_ids = new_listing_messages.get(channel_id, {}).get(key, [])
                    if isinstance(msg_ids, str):
                        msg_ids = [msg_ids]
                    for old_msg_id in msg_ids:
                        try:
                            msg_obj = await channel.fetch_message(int(old_msg_id))
                            await msg_obj.delete()
                            logger.info(f"[Bazaar Bot] Deleted old {type_str} group message (msg id={old_msg_id}) in channel {channel_id}")
                        except Exception as cleanup_err:
                            logger.error(f"[Bazaar Bot] Failed to delete old {type_str} group message {old_msg_id} in channel {channel_id}: {cleanup_err}")
                    if channel_id in new_listing_messages and key in new_listing_messages[channel_id]:
                        del new_listing_messages[channel_id][key]
                    return
                header = f"**{episode} — {type_str} Listings**"
                lines = []
                for l in listings:
                    line_type = '[WTS]' if type_str == 'SELL' else '[WTB]'
                    price = l['price']
                    price_mode = l.get('priceMode', '').strip().lower()
                    price_str = format_price(price)
                    if price_mode == 'each':
                        price_str += ' EA'
                    elif price_mode == 'total':
                        price_str += ' Total'
                    lines.append(f"{line_type} {l['item']} | {l['quantity']} | {price_str} | {l['contactInfo']}")
                # Split into message parts
                parts = []
                current = header + '\n'
                for line in lines:
                    if len(current) + len(line) + 1 > MAX_LEN:
                        parts.append(current.rstrip())
                        current = ''
                    if not current:
                        current = ''  # No header for subsequent parts
                    if current:
                        current += '\n'
                    current += line
                if current:
                    parts.append(current.rstrip())
                # Post or edit the group messages
                if channel_id not in new_listing_messages:
                    new_listing_messages[channel_id] = {}
                msg_ids = new_listing_messages[channel_id].get(key, [])
                if isinstance(msg_ids, str):
                    msg_ids = [msg_ids]
                # Edit or send messages as needed
                new_msg_ids = []
                for i, part in enumerate(parts):
                    msg_id = msg_ids[i] if i < len(msg_ids) else None
                    if msg_id:
                        try:
                            msg_obj = await channel.fetch_message(int(msg_id))
                            if msg_obj.content != part:
                                await msg_obj.edit(content=part)
                                logger.info(f"[Bazaar Bot] Edited {type_str} group message part {i+1} in channel {channel_id} (msg id={msg_id})")
                            all_current_ids.add(msg_id)
                            new_msg_ids.append(msg_id)
                        except discord.NotFound:
                            logger.info(f"[Bazaar Bot] Will re-post missing {type_str} group message part {i+1} in channel {channel_id}")
                            msg_id = None
                        except Exception as fetch_err:
                            logger.error(f"[Bazaar Bot] Error fetching/editing group message part {i+1} ({msg_id}) in channel {channel_id}: {fetch_err}")
                            msg_id = None
                    if not msg_id:
                        try:
                            msg = await channel.send(part)
                            logger.info(f"[Bazaar Bot] Posted {type_str} group message part {i+1} in channel {channel_id} (msg id={msg.id})")
                            new_msg_ids.append(str(msg.id))
                            all_current_ids.add(str(msg.id))
                            await asyncio.sleep(1)
                        except Exception as send_err:
                            logger.error(f"[Bazaar Bot] Failed to send {type_str} group message part {i+1} to channel {channel_id}: {send_err}")
                # Delete any extra old messages
                for j in range(len(parts), len(msg_ids)):
                    old_msg_id = msg_ids[j]
                    try:
                        msg_obj = await channel.fetch_message(int(old_msg_id))
                        await msg_obj.delete()
                        logger.info(f"[Bazaar Bot] Deleted extra old {type_str} group message part {j+1} (msg id={old_msg_id}) in channel {channel_id}")
                    except Exception as cleanup_err:
                        logger.error(f"[Bazaar Bot] Failed to delete extra old {type_str} group message part {j+1} ({old_msg_id}) in channel {channel_id}: {cleanup_err}")
                new_listing_messages[channel_id][key] = new_msg_ids

            # Attach helper to self for use in loop
            self._update_listings_for_type = _update_listings_for_type.__get__(self)
            self.loop.create_task(listings_loop())
        except Exception as err:
            logger.error(f"[Bazaar Bot] on_ready error: {err}")


# --- Main block ---
if __name__ == '__main__':
    # Minimal startup logs
    from config import COMMAND_PREFIX
    if not TOKEN:
        logger.error("[Bazaar Bot] DISCORD_TOKEN not set in .env!")
    else:
        bot = BazaarBot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
        register_commands(bot)
        print("[Bazaar Bot] register_commands called and commands registered.")
        try:
            bot.run(TOKEN)
        except KeyboardInterrupt:
            logger.info("[Bazaar Bot] Bot stopped by user (Ctrl+C)")
