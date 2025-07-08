import json

# Load bazaar_listings.json
with open('bazaar_listings.json', 'r', encoding='utf-8') as f:
    listings = json.load(f)

# Load items_combined.json
with open('items_combined.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Build lookups for item name to episode and bank
item_to_episode = {item['Items']: item.get('Episode', None) for item in items}
item_to_bank = {item['Items']: item.get('Bank', None) for item in items}

# Append episode and bank to each listing
for listing in listings:
    item_name = listing.get('item')
    episode = item_to_episode.get(item_name)
    bank = item_to_bank.get(item_name)
    listing['episode'] = episode
    listing['bank'] = bank

# Save updated bazaar_listings.json
with open('bazaar_listings.json', 'w', encoding='utf-8') as f:
    json.dump(listings, f, ensure_ascii=False, indent=2)

print('Episodes and Bank info merged into bazaar_listings.json.')
