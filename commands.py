# DEBUG: Print at top of commands.py to detect import/run issues
print("[Bazaar Bot] commands.py loaded")
from discord.ext import commands
import requests
from listing_manager import EPISODES, load_episode_channels, save_episode_channels
from listing_manager import load_bank_channels, save_bank_channels


def register_commands(bot_instance):
    # ...existing code...

    # ...existing code...


# Place the resetchannels command here, after bz and all its subcommands are defined

# Place the resetchannels command at the very end of register_commands, after all bz subcommands
    # Purge command must be defined after bz is defined
    # Only define bz_purge once, after bz and other subcommands
    # Removed @bot_instance.event async def on_ready to avoid conflict with class-based on_ready

    @bot_instance.command(name='testemoji', help='Test custom emoji rendering')
    async def testemoji(ctx):
        test_str = (
            'Test: 1<:Platinum:1127690490117990511> 2<:Gold:1127690488586244177> '
            '3<:Silver:1127690486971498576> 4<:Copper:1127690485272062002>'
        )
        await ctx.send(test_str)

    @bot_instance.command(name='WTS', help='Post a new sell listing to bs-bazaar.com API')
    async def WTS(ctx, item: str, quantity: int, price: int, contact: str):
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
    async def WTB(ctx, item: str, quantity: int, price: int, contact: str):
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

    @bot_instance.command(name='post', help='Post a new listing to bs-bazaar.com API')
    async def post(ctx, order_type: str, item: str, quantity: int, price: int, contact: str, episode: str):
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

    @bot_instance.group(name='bz', invoke_without_command=True, help='Bazaar admin and info commands')
    async def bz(ctx):
        if ctx.invoked_subcommand is None:
            from bank_names import BANKS
            help_text = (
                '**Bazaar Bot Info Commands:**\n'
                '`!bz help` — Show this help message.\n\n'
                '**Bazaar Bot Admin Commands:**\n'
                '`!bz purge` — Delete all messages posted by the bot in this server. Admin only.\n'
                '`!bz resetchannels` — Remove all episode and bank channel assignments for this server. Admin only.\n'
                '`!bz channels` — list the Discord channels for each episode or bank in this server. Admin only.\n'
                '`!bz channels <episode|bank:BankName> <#channel>` — Set the Discord channel for an episode or bank in this server. Admin only.\n\n'
                '- Example: `!bz channels Hopeport #bazaar-hopeport`\n'
                '- Example: `!bz channels "bank:Potions Bank" #potions-bank`\n'
                '\n**Episodes:** ' + ', '.join(EPISODES) + '\n'
                '\n**Banks:** ' + ', '.join(BANKS) + '\n\n'
                '\n*For bank names with spaces, use double quotes, e.g.* `!bz channels "bank:Bones Bank" #channel`'
            )
            await ctx.send(help_text)

    @bz.command(name='help', help='Show help for Bazaar bot')
    async def bz_help(ctx):
        from bank_names import BANKS
        help_text = (
                '**Bazaar Bot Info Commands:**\n'
                '`!bz help` — Show this help message.\n\n'
                '**Bazaar Bot Admin Commands:**\n'
                '`!bz purge` — Delete all messages posted by the bot in this server. Admin only.\n'
                '`!bz resetchannels` — Remove all episode and bank channel assignments for this server. Admin only.\n'
                '`!bz channels` — list the Discord channels for each episode or bank in this server. Admin only.\n'
                '`!bz channels <episode|bank:BankName> <#channel>` — Set the Discord channel for an episode or bank in this server. Admin only.\n\n'
                '- Example: `!bz channels Hopeport #bazaar-hopeport`\n'
                '- Example: `!bz channels "bank:Potions Bank" #potions-bank`\n'
                '\n**Episodes:** ' + ', '.join(EPISODES) + '\n'
                '\n**Banks:** ' + ', '.join(BANKS) + '\n\n'
                '\n*For bank names with spaces, use double quotes, e.g.* `!bz channels "bank:Bones Bank" #channel`'
            )
        await ctx.send(help_text)

    from typing import Optional
    @bz.command(name='channels', help='Set or list episode/bank channel assignments (admin only)')
    async def bz_channels(ctx, target: Optional[str] = None, channel: Optional[str] = None):
        # If no arguments, list all episodes and all bank names and their assigned channels for this guild
        if target is None:
            episode_channels = load_episode_channels()
            bank_channels = load_bank_channels()
            guild_id = str(ctx.guild.id)
            guild_channels = episode_channels.get(guild_id, {})
            bank_guild_channels = bank_channels.get(guild_id, {})
            from bank_names import BANKS
            lines = []
            lines.append("__**Episode Channels:**__")
            for ep in EPISODES:
                ch_id = guild_channels.get(ep)
                if ch_id:
                    ch_obj = ctx.guild.get_channel(int(ch_id))
                    ch_display = ch_obj.mention if ch_obj else f'ID: {ch_id} (not found)'
                else:
                    ch_display = 'Not set'
                lines.append(f'**{ep}**: {ch_display}')
            lines.append("\n__**Bank Channels:**__")
            for bank_name in BANKS:
                ch_id = bank_guild_channels.get(bank_name)
                if ch_id:
                    ch_obj = ctx.guild.get_channel(int(ch_id))
                    ch_display = ch_obj.mention if ch_obj else f'ID: {ch_id} (not found)'
                else:
                    ch_display = 'Not set'
                lines.append(f'**{bank_name}**: {ch_display}')
            lines.append('\n*Note: For bank names with spaces, use double quotes around the full argument, e.g.*')
            lines.append('`!bz channels "bank:Bones Bank" #channel`')
            await ctx.send('**Current channel assignments:**\n' + '\n'.join(lines))
            return

        # If arguments are provided, handle setting the channel
        if not ctx.author.guild_permissions.administrator:
            await ctx.send('You must be a server administrator to use this command.')
            return
        # Accept both #channel mention and channel ID
        if channel is None:
            await ctx.send('Please specify a channel (mention or ID).')
            return
        if channel.startswith('<#') and channel.endswith('>'):
            channel_id = channel[2:-1]
        else:
            channel_id = channel
        try:
            channel_obj = ctx.guild.get_channel(int(channel_id))
        except Exception:
            channel_obj = None
        if not channel_obj or not hasattr(channel_obj, 'mention'):
            await ctx.send('Invalid channel. Please mention a text channel or provide a valid channel ID.')
            return
        episode_channels = load_episode_channels()
        bank_channels = load_bank_channels()
        guild_id = str(ctx.guild.id)
        if target in EPISODES:
            if guild_id not in episode_channels:
                episode_channels[guild_id] = {}
            episode_channels[guild_id][target] = str(channel_obj.id)
            save_episode_channels(episode_channels)
            await ctx.send(f'Channel for episode **{target}** set to {channel_obj.mention} for this server.')
            return
        elif target.lower().startswith('bank:'):
            bank_name = target[5:].strip()
            if not bank_name:
                await ctx.send('Please specify a bank name after bank:.')
                return
            if guild_id not in bank_channels:
                bank_channels[guild_id] = {}
            bank_channels[guild_id][bank_name] = str(channel_obj.id)
            save_bank_channels(bank_channels)
            await ctx.send(f'Channel for bank **{bank_name}** set to {channel_obj.mention} for this server.')
            return
        else:
            await ctx.send(f'Invalid target. Use an episode name or bank:BankName.')
            return

    @bz.command(name='purge', help='Delete all messages posted by the bot in this server (admin only)')
    @commands.has_permissions(administrator=True)
    async def bz_purge(ctx):
        await ctx.send('Purging all bot messages in this server...')
        deleted_count = 0
        import asyncio
        for channel in ctx.guild.text_channels:
            try:
                async for msg in channel.history(limit=None):
                    if msg.author == ctx.me:
                        try:
                            await msg.delete()
                            deleted_count += 1
                            await asyncio.sleep(1)  # Prevent Discord rate limits
                        except Exception:
                            pass
            except Exception:
                continue
        await ctx.send(f'Purge complete. Deleted {deleted_count} messages.')

    @bz.command(name='resetchannels', help='Remove all episode and bank channel assignments for this server (admin only)')
    @commands.has_permissions(administrator=True)
    async def bz_resetchannels(ctx):
        guild_id = str(ctx.guild.id)
        episode_channels = load_episode_channels()
        bank_channels = load_bank_channels()
        changed = False
        if guild_id in episode_channels:
            del episode_channels[guild_id]
            save_episode_channels(episode_channels)
            changed = True
        if guild_id in bank_channels:
            del bank_channels[guild_id]
            save_bank_channels(bank_channels)
            changed = True
        if changed:
            await ctx.send('All episode and bank channel assignments for this server have been reset.')
        else:
            await ctx.send('No channel assignments found for this server.')

    # --- Channel assignment logic for bz_channels ---
    # (Moved into bz_channels command above)
