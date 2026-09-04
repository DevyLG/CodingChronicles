import discord
from discord import app_commands
from discord.ext import commands
import re
from cogs.utils import check_is_allowed

def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing, substituting leetspeak, stripping symbols, and collapsing repeating characters."""
    text = text.lower()
    
    # Leetspeak substitutions
    leet_map = {
        '3': 'e', '4': 'a', '@': 'a', '1': 'i', '!': 'i', '|': 'i', 
        '0': 'o', '$': 's', '5': 's', '7': 't', '9': 'g', '8': 'b',
        'u': 'u', 'v': 'u'
    }
    for leet, normal in leet_map.items():
        text = text.replace(leet, normal)
        
    # Strip all non-alphabetic characters
    text = re.sub(r'[^a-z]', '', text)
    
    # Collapse repeating characters (e.g., "feeeck" -> "feck")
    text = re.sub(r'(.)\1+', r'\1', text)
    
    return text

class FilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    filter_group = app_commands.Group(
        name="filter",
        description="Manage the chat word filter."
    )

    @filter_group.command(name="add", description="Adds a word to the chat filter list.")
    @app_commands.describe(word="The word or phrase to block")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def filter_add(self, interaction: discord.Interaction, word: str):
        guild_id = interaction.guild_id
        word_clean = word.lower().strip()
        if not word_clean:
            await interaction.response.send_message("❌ Cannot filter an empty word.", ephemeral=True)
            return

        # Write to Database
        await self.bot.db.async_add_blocked_word(guild_id, word_clean)

        # Update in-memory cache
        if guild_id not in self.bot.blocked_words:
            self.bot.blocked_words[guild_id] = set()
        self.bot.blocked_words[guild_id].add(word_clean)

        await interaction.response.send_message(f"✅ Added ||{word_clean}|| to the blocked word filter.", ephemeral=True)

    @filter_group.command(name="remove", description="Removes a word from the chat filter list.")
    @app_commands.describe(word="The word or phrase to unblock")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def filter_remove(self, interaction: discord.Interaction, word: str):
        guild_id = interaction.guild_id
        word_clean = word.lower().strip()

        # Delete from Database
        await self.bot.db.async_remove_blocked_word(guild_id, word_clean)

        # Update in-memory cache
        if guild_id in self.bot.blocked_words:
            self.bot.blocked_words[guild_id].discard(word_clean)

        await interaction.response.send_message(f"✅ Removed ||{word_clean}|| from the blocked word filter.", ephemeral=True)

    @filter_group.command(name="list", description="Lists all blocked words for this server.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def filter_list(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        words = self.bot.blocked_words.get(guild_id, set())

        if not words:
            await interaction.response.send_message("✅ No words are currently filtered in this server.", ephemeral=True)
            return

        sorted_words = sorted(list(words))
        
        # Split into blocks if list is too long
        word_list_str = ", ".join(f"||{w}||" for w in sorted_words)
        if len(word_list_str) > 1000:
            word_list_str = word_list_str[:997] + "..."

        embed = discord.Embed(
            title="🛡️ Blocked Word Filter List",
            description=f"Messages containing these words will be deleted, and authors warned.\n\n**Filtered Words**:\n{word_list_str}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @filter_group.command(name="exempt_role", description="Manages role exemptions from the chat filter.")
    @app_commands.describe(
        action="Whether to add or remove the exemption",
        role="The role to exempt or unexempt"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Exemption", value="add"),
        app_commands.Choice(name="Remove Exemption", value="remove")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def exempt_role(self, interaction: discord.Interaction, action: str, role: discord.Role):
        guild_id = interaction.guild_id
        if action == "add":
            await self.bot.db.async_add_filter_exempt_role(guild_id, role.id)
            if guild_id not in self.bot.filter_exempt_roles:
                self.bot.filter_exempt_roles[guild_id] = set()
            self.bot.filter_exempt_roles[guild_id].add(role.id)
            await interaction.response.send_message(f"✅ Users with the role **{role.name}** are now exempt from the word filter.", ephemeral=True)
        else:
            await self.bot.db.async_remove_filter_exempt_role(guild_id, role.id)
            if guild_id in self.bot.filter_exempt_roles:
                self.bot.filter_exempt_roles[guild_id].discard(role.id)
            await interaction.response.send_message(f"✅ Users with the role **{role.name}** are no longer exempt from the word filter.", ephemeral=True)

    @filter_group.command(name="exempt_channel", description="Manages channel exemptions from the chat filter.")
    @app_commands.describe(
        action="Whether to add or remove the exemption",
        channel="The text channel to exempt or unexempt"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Exemption", value="add"),
        app_commands.Choice(name="Remove Exemption", value="remove")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def exempt_channel(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel):
        guild_id = interaction.guild_id
        if action == "add":
            await self.bot.db.async_add_filter_exempt_channel(guild_id, channel.id)
            if guild_id not in self.bot.filter_exempt_channels:
                self.bot.filter_exempt_channels[guild_id] = set()
            self.bot.filter_exempt_channels[guild_id].add(channel.id)
            await interaction.response.send_message(f"✅ Messages in {channel.mention} are now exempt from the word filter.", ephemeral=True)
        else:
            await self.bot.db.async_remove_filter_exempt_channel(guild_id, channel.id)
            if guild_id in self.bot.filter_exempt_channels:
                self.bot.filter_exempt_channels[guild_id].discard(channel.id)
            await interaction.response.send_message(f"✅ Messages in {channel.mention} are no longer exempt from the word filter.", ephemeral=True)

    @filter_group.command(name="exemptions", description="Lists all roles and channels exempt from the word filter.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def exemptions(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        exempt_roles = self.bot.filter_exempt_roles.get(guild_id, set())
        exempt_chans = self.bot.filter_exempt_channels.get(guild_id, set())

        roles_str = ", ".join(f"<@&{r_id}>" for r_id in exempt_roles) if exempt_roles else "None"
        chans_str = ", ".join(f"<#{c_id}>" for c_id in exempt_chans) if exempt_chans else "None"

        embed = discord.Embed(
            title="🛡️ Auto-Mod Filter Exemptions",
            color=discord.Color.blue()
        )
        embed.add_field(name="Exempt Roles", value=roles_str, inline=False)
        embed.add_field(name="Exempt Channels", value=chans_str, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setlogchannel", description="Sets the custom moderation logging channel.")
    @app_commands.describe(channel="The channel to send moderation and auto-mod logs to")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild_id
        await self.bot.db.async_set_mod_log_channel(guild_id, channel.id)
        self.bot.mod_log_channels[guild_id] = channel.id
        await interaction.response.send_message(f"📝 **Moderation Logs**: Configured to log events in {channel.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        
        # Check channel exemptions
        exempt_channels = self.bot.filter_exempt_channels.get(guild_id, set())
        if message.channel.id in exempt_channels:
            return
            
        # Check role exemptions
        exempt_roles = self.bot.filter_exempt_roles.get(guild_id, set())
        if any(role.id in exempt_roles for role in message.author.roles):
            return

        words = self.bot.blocked_words.get(guild_id, set())
        if not words:
            return

        matched_words = []
        
        # Tokenize content to check individual words (splits by spaces and symbols)
        tokens = re.split(r'[^\w\d_]', message.content)
        normalized_tokens = [normalize_text(t) for t in tokens if t]
        
        # Fully normalized entire message for spaced-out bypass checks
        normalized_full = normalize_text(message.content)

        for blocked_word in words:
            norm_blocked = normalize_text(blocked_word)
            if not norm_blocked:
                continue
                
            # Check 1: Exact word match on normalized tokens (avoids Scunthorpe false-positives)
            if norm_blocked in normalized_tokens:
                matched_words.append(blocked_word)
                continue
                
            # Check 2: Substring match on the entire collapsed message (only for words >= 4 chars)
            # Catches spacing bypasses like "f e c k" or "f.e.c.k"
            if len(norm_blocked) >= 4 and norm_blocked in normalized_full:
                matched_words.append(blocked_word)

        if matched_words:
            # Delete message first
            try:
                await message.delete()
            except discord.Forbidden:
                # Log error in terminal but still proceed to issue warning/log
                print(f"❌ Auto-Mod: Lacks MANAGE_MESSAGES permission to delete message by {message.author} in {message.guild.name}")
            except discord.NotFound:
                pass

            # Log a warning to the database
            reason = f"Auto-Mod: Sent message containing blocked word(s): {', '.join(matched_words)}"
            await self.bot.db.async_add_warning(guild_id, message.author.id, self.bot.user.id, reason)

            # Inform user via DM
            try:
                embed_dm = discord.Embed(
                    title="⚠️ Message Deleted",
                    description=f"Your message in **{message.guild.name}** was deleted because it contained blocked words.\n**Blocked Word(s)**: {', '.join(f'||{w}||' for w in matched_words)}",
                    color=discord.Color.red()
                )
                await message.author.send(embed=embed_dm)
            except discord.HTTPException:
                pass  # Author has DMs disabled

            # Send alert to mod logs
            log_channel = self.bot.get_log_channel(message.guild)
            if log_channel:
                embed_log = discord.Embed(
                    title="🛡️ Auto-Mod Filter Triggered",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                embed_log.add_field(name="User", value=f"{message.author.mention} ({message.author} / {message.author.id})", inline=False)
                embed_log.add_field(name="Channel", value=message.channel.mention, inline=False)
                embed_log.add_field(name="Trigger Word(s)", value=", ".join(matched_words), inline=False)
                embed_log.add_field(name="Original Content", value=message.content[:1024], inline=False)
                await log_channel.send(embed=embed_log)

async def setup(bot):
    await bot.add_cog(FilterCog(bot))
