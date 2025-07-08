# Auto-generated list of all unique banks from items_combined.json
import json

with open('items_combined.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Exclude "Capes Bank" from the list
BANKS = sorted({item['Bank'] for item in data if item.get('Bank') and item['Bank'] not in (None, '', 'null', 'Capes Bank', 'Monument Pieces Bank')})
