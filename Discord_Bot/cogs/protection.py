import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class ProtectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="lockdown", description="Freezes or unfreezes a text channel (prevents members from messaging).")
    @app_commands.describe(
        channel="The text channel to target (Defaults to current channel)",
        state="Freeze the channel (on) or unfreeze it (off)"
    )
    @app_commands.choices(state=[
        app_commands.Choice(name="On (Freeze)", value="on"),
        app_commands.Choice(name="Off (Unfreeze)", value="off")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def lockdown(self, interaction: discord.Interaction, state: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        guild = interaction.guild
        everyone_role = guild.default_role

        if state == "on":
            # Set send_messages override to False for @everyone
            try:
                await target_channel.set_permissions(everyone_role, send_messages=False, reason="Emergency channel lockdown.")
                await interaction.response.send_message(f"🔒 **Lockdown Active**: {target_channel.mention} has been frozen.", ephemeral=True)
                
                # Send alert to channel
                embed = discord.Embed(
                    title="🔒 Channel Lockdown",
                    description="This channel has been temporarily frozen by staff. Regular members cannot send messages until further notice.",
                    color=discord.Color.red()
                )
                await target_channel.send(embed=embed)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Error: Bot lacks permissions to manage channel permissions.", ephemeral=True)
        else:
            # Revert send_messages override for @everyone
            try:
                await target_channel.set_permissions(everyone_role, send_messages=None, reason="Lockdown lifted.")
                await interaction.response.send_message(f"🔓 **Lockdown Lifted**: {target_channel.mention} has been unfrozen.", ephemeral=True)
                
                # Send alert to channel
                embed = discord.Embed(
                    title="🔓 Lockdown Lifted",
                    description="This channel has been unfrozen. You may send messages again.",
                    color=discord.Color.green()
                )
                await target_channel.send(embed=embed)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Error: Bot lacks permissions to manage channel permissions.", ephemeral=True)

    @app_commands.command(name="joinshield", description="Sets up age-gate protection for new accounts joining the server.")
    @app_commands.describe(
        min_age_days="Minimum account age in days (Set to 0 to disable)"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def joinshield(self, interaction: discord.Interaction, min_age_days: int):
        if min_age_days < 0:
            await interaction.response.send_message("❌ Minimum age must be 0 or higher.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        if min_age_days == 0:
            self.bot.joinshield_settings.pop(guild_id, None)
            await self.bot.db.async_set_joinshield(guild_id, 0)
            await interaction.response.send_message("🛡️ **Join Shield**: Disabled for this server.", ephemeral=True)
        else:
            self.bot.joinshield_settings[guild_id] = min_age_days
            await self.bot.db.async_set_joinshield(guild_id, min_age_days)
            await interaction.response.send_message(f"🛡️ **Join Shield**: Active. Accounts must be at least **{min_age_days}** days old to join.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        min_days = self.bot.joinshield_settings.get(guild.id, 0)
        
        if min_days <= 0:
            return  # Joinshield is disabled
            
        # Calculate account age
        account_age_days = (discord.utils.utcnow() - member.created_at).days
        
        if account_age_days < min_days:
            # 1. Direct Message Warning
            warning_text = (
                f"❌ You have been kicked from **{guild.name}** because your Discord account is too new.\n"
                f"This server requires accounts to be at least **{min_days} days old** to prevent raids.\n"
                f"Your account is currently **{account_age_days} days old**. You may join again once your account meets the threshold."
            )
            try:
                await member.send(warning_text)
            except discord.HTTPException:
                pass  # Ignore if DMs are closed
                
            # 2. Kick Member
            try:
                await member.kick(reason=f"Joinshield: Account age ({account_age_days}d) below threshold ({min_days}d).")
                
                # 3. Log incident to logging channel or system channel
                log_embed = discord.Embed(
                    title="🛡️ Join Shield Triggered",
                    description=f"**User**: {member.mention} ({member} / ID: {member.id})\n**Account Age**: `{account_age_days}` days\n**Required Age**: `{min_days}` days\n**Action**: Automatically kicked.",
                    color=discord.Color.orange()
                )
                log_embed.set_footer(text="Join Shield Defense Active")
                
                log_channel = self.bot.get_log_channel(guild)
                if log_channel:
                    await log_channel.send(embed=log_embed)
            except discord.Forbidden:
                print(f"❌ Join Shield: Bot failed to kick {member} due to missing permissions.")

async def setup(bot):
    await bot.add_cog(ProtectionCog(bot))
