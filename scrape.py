import requests
import pandas as pd
import glob
import json
import os

####### URL's to download the .csv files from and saving the files as parts########

url_1 = ('https://brightershoreswiki.org/w/Special:Ask/format%3Dcsv/link%3Dall/headers%3Dshow/searchlabel%3DCSV/class%3Dsortable-20wikitable-20smwtable/prefix%3Dnone/sort%3DProfession-20Level-20A/order%3Dasc/offset%3D0/limit%3D500/-5B-5BInfobox::Item-5D-5D/-3F/-3FImage-23-2D/-3FEpisode/-3FVariant-20of/-3FProfession-20A/-3FProfession-20Level-20A/-3FProfession-20B/-3FProfession-20Level-20B/-3FTradeable/mainlabel%3D/prettyprint%3Dtrue/unescape%3Dtrue')
filename1 = 'itemsPart1.csv'
url_2 = ('https://brightershoreswiki.org/w/Special:Ask/format%3Dcsv/link%3Dall/headers%3Dshow/searchlabel%3DCSV/class%3Dsortable-20wikitable-20smwtable/prefix%3Dnone/sort%3DProfession-20Level-20A/order%3Dasc/offset%3D500/limit%3D500/-5B-5BInfobox::Item-5D-5D/-3F/-3FImage-23-2D/-3FEpisode/-3FVariant-20of/-3FProfession-20A/-3FProfession-20Level-20A/-3FProfession-20B/-3FProfession-20Level-20B/-3FTradeable/mainlabel%3D/prettyprint%3Dtrue/unescape%3Dtrue')
filename2 = 'itemsPart2.csv'
url_3 = ('https://brightershoreswiki.org/w/Special:Ask/format%3Dcsv/link%3Dall/headers%3Dshow/searchlabel%3DCSV/class%3Dsortable-20wikitable-20smwtable/prefix%3Dnone/sort%3DProfession-20Level-20A/order%3Dasc/offset%3D1000/limit%3D500/-5B-5BInfobox::Item-5D-5D/-3F/-3FImage-23-2D/-3FEpisode/-3FVariant-20of/-3FProfession-20A/-3FProfession-20Level-20A/-3FProfession-20B/-3FProfession-20Level-20B/-3FTradeable/mainlabel%3D/prettyprint%3Dtrue/unescape%3Dtrue')
filename3 = 'itemsPart3.csv'
url_4 = ('https://brightershoreswiki.org/w/Special:Ask/format%3Dcsv/link%3Dall/headers%3Dshow/searchlabel%3DCSV/class%3Dsortable-20wikitable-20smwtable/prefix%3Dnone/sort%3DProfession-20Level-20A/order%3Dasc/offset%3D1500/limit%3D500/-5B-5BInfobox::Item-5D-5D/-3F/-3FImage-23-2D/-3FEpisode/-3FVariant-20of/-3FProfession-20A/-3FProfession-20Level-20A/-3FProfession-20B/-3FProfession-20Level-20B/-3FTradeable/mainlabel%3D/prettyprint%3Dtrue/unescape%3Dtrue')
filename4 = 'itemsPart4.csv'
url_5 = ('https://brightershoreswiki.org/w/Special:Ask/format%3Dcsv/link%3Dall/headers%3Dshow/searchlabel%3DCSV/class%3Dsortable-20wikitable-20smwtable/prefix%3Dnone/sort%3DProfession-20Level-20A/order%3Dasc/offset%3D2000/limit%3D500/-5B-5BInfobox::Item-5D-5D/-3F/-3FImage-23-2D/-3FEpisode/-3FVariant-20of/-3FProfession-20A/-3FProfession-20Level-20A/-3FProfession-20B/-3FProfession-20Level-20B/-3FTradeable/mainlabel%3D/prettyprint%3Dtrue/unescape%3Dtrue')
filename5 = 'itemsPart5.csv'

### Download the CSV files and save them ###

query_parameters = {"downloadformat": "csv"}
response = requests.get(url_1, params=query_parameters)
if response.status_code == 200:
    with open(filename1, 'wb') as f:
        f.write(response.content)

response = requests.get(url_2, params=query_parameters)
if response.status_code == 200:
    with open(filename2, 'wb') as f:
        f.write(response.content)

response = requests.get(url_3, params=query_parameters)
if response.status_code == 200:
    with open(filename3, 'wb') as f:
        f.write(response.content)

response = requests.get(url_4, params=query_parameters)
if response.status_code == 200:
    with open(filename4, 'wb') as f:
        f.write(response.content)

response = requests.get(url_5, params=query_parameters)
if response.status_code == 200:
    with open(filename5, 'wb') as f:
        f.write(response.content)

### merge the CSV files into one for easier data clean up ###

csv_files = glob.glob('*.csv')
dfs = []
for filename in csv_files:
    df = pd.read_csv(filename, encoding='utf-8')
    dfs.append(df)
combined_df = pd.concat(dfs, ignore_index=True)
combined_df.to_csv('items_combined.csv', index=False, encoding='utf-8')

### Open and clean the merged .csv ###
filename6 = 'items_combined.csv'
df = pd.read_csv(filename6, usecols=['Unnamed: 0', 'Image', 'Episode', 'Variant of', 'Profession A', 'Profession Level A', 'Profession B', 'Profession Level B', 'Tradeable'], encoding='utf-8')
df.rename(columns={'Unnamed: 0': 'Items'}, inplace=True) #replace empty column name with 'Items'
df['Image'] = df['Image'].str.replace('File:', 'https://brightershoreswiki.org/images/')# preplace file prefix with wiki link to the image
df['Image'] = df['Image'].str.replace(' ', '_') # remove spaces from url

## Fill NaN values with 'None' or 'unknown' for better readability
df['Episode'] = df['Episode'].fillna('None')
df['Variant of'] = df['Variant of'].fillna('None')
df['Profession A'] = df['Profession A'].fillna('None')
df['Profession Level A'] = df['Profession Level A'].fillna('None')
df['Profession B'] = df['Profession B'].fillna('None')
df['Profession Level B'] = df['Profession Level B'].fillna('None')
df['Tradeable'] = df['Tradeable'].fillna('unknown')

df = df[df.Tradeable != 'False']

df.to_csv('items_combined.csv', index=False, encoding='utf-8')

### Convert the cleaned CSV to JSON ###
df_json = df.to_json(orient='records', indent=2)
with open('items_combined.json', 'w', encoding='utf-8') as json_file:
    json_file.write(df_json)

# Remove all .csv files after processing
def remove_csv_files():
    for file in glob.glob('*.csv'):
        try:
            os.remove(file)
            print(f"Removed: {file}")
        except Exception as e:
            print(f"Failed to remove {file}: {e}")
remove_csv_files()

print("Data processing complete!")
print(f"CSV file saved: items_combined.csv ({len(df)} rows)")
print(f"JSON file saved: items_combined.json ({len(df)} rows)")
