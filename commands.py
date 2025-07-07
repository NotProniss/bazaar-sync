# DEBUG: Print at top of commands.py to detect import/run issues
print("[Bazaar Bot] commands.py loaded")
from discord.ext import commands
import requests
from listing_manager import EPISODES, load_episode_channels, save_episode_channels


def register_commands(bot_instance):
    # Removed @bot_instance.event async def on_ready to avoid conflict with class-based on_ready

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
            channel_obj = ctx.guild.get_channel(int(channel_id))
            if not channel_obj or not hasattr(channel_obj, 'mention'):
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
