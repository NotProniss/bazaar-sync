BANK_CHANNELS_FILE = 'bank_channels.json'

def load_bank_channels():
    if os.path.exists(BANK_CHANNELS_FILE):
        with open(BANK_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_bank_channels(mapping):
    with open(BANK_CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
import hashlib
import json
import os

def format_price(copper):
    """
    Converts a price in copper to a string with platinum, gold, silver, and copper, using emoji.
    """
    try:
        copper = int(copper)
    except Exception:
        return str(copper)
    from config import EMOJI_PLATINUM, EMOJI_GOLD, EMOJI_SILVER, EMOJI_COPPER
    parts = []
    platinum = copper // 1000000000
    if platinum:
        parts.append(f"{platinum} {EMOJI_PLATINUM}")
    copper = copper % 1000000000
    gold = copper // 1000000
    if gold:
        parts.append(f"{gold} {EMOJI_GOLD}")
    copper = copper % 1000000
    silver = copper // 1000
    if silver:
        parts.append(f"{silver} {EMOJI_SILVER}")
    copper = copper % 1000
    if copper or not parts:
        parts.append(f"{copper} {EMOJI_COPPER}")
    return ' '.join(parts)

def get_listing_id(entry):
    # Use a hash of the relevant fields as a unique ID
    key = f"{entry.get('type','')}|{entry.get('item','')}|{entry.get('quantity','')}|{entry.get('price','')}|{entry.get('contactInfo','')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

CHANNELS_FILE = 'episode_channels.json'
LISTING_MESSAGES_FILE = 'listing_messages.json'

EPISODES = [
    "Hopeport",
    "Hopeforest",
    "Mine of Mantuban",
    "Crenopolis",
    "Stonemaw Hill",
    "Combat"
]

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
