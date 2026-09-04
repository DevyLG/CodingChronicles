import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class WarningsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Issues a warning to a member.")
    @app_commands.describe(
        member="The member to warn",
        reason="Reason for the warning"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if member.bot:
            await interaction.response.send_message("❌ You cannot warn a bot.", ephemeral=True)
            return

        # Add warning to database
        await self.bot.db.async_add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        
        # Get count of warning
        warns = await self.bot.db.async_get_warnings(interaction.guild_id, member.id)
        warn_count = len(warns)

        # Attempt to DM user
        try:
            embed_dm = discord.Embed(
                title=f"⚠️ Warning issued in {interaction.guild.name}",
                description=f"You have been warned for: **{reason}**\nThis is warning #{warn_count}.",
                color=discord.Color.orange()
            )
            await member.send(embed=embed_dm)
        except discord.HTTPException:
            pass # DM blocked

        # Confirm to moderator
        await interaction.response.send_message(f"⚠️ **{member}** has been warned (Warning #{warn_count}). Reason: {reason}", ephemeral=True)

        # Log to mod logs
        log_channel = self.bot.get_log_channel(interaction.guild)
        if log_channel:
            embed_log = discord.Embed(
                title="⚠️ Warning Issued",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed_log.add_field(name="User", value=f"{member.mention} ({member} / {member.id})", inline=False)
            embed_log.add_field(name="Moderator", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
            embed_log.add_field(name="Reason", value=reason, inline=False)
            embed_log.add_field(name="Total Warnings", value=str(warn_count), inline=False)
            await log_channel.send(embed=embed_log)

    @app_commands.command(name="warns", description="Lists warnings for a specific member.")
    @app_commands.describe(
        member="The member to view warnings for"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def warns(self, interaction: discord.Interaction, member: discord.Member):
        warns = await self.bot.db.async_get_warnings(interaction.guild_id, member.id)
        
        if not warns:
            await interaction.response.send_message(f"✅ **{member}** has 0 active warnings.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            color=discord.Color.yellow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # list warnings (moderator_id, reason, timestamp)
        for i, (mod_id, reason, timestamp) in enumerate(warns, 1):
            mod_user = interaction.guild.get_member(mod_id)
            mod_text = f"<@{mod_id}>" if mod_user else f"ID: {mod_id}"
            embed.add_field(
                name=f"Warning #{len(warns) - i + 1}",
                value=f"**Reason**: {reason}\n**Moderator**: {mod_text}\n**Date**: {timestamp}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarns", description="Clears all warnings for a member.")
    @app_commands.describe(
        member="The member to clear warnings for"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.db.async_clear_warnings(interaction.guild_id, member.id)
        await interaction.response.send_message(f"✅ Cleared all warnings for **{member}**.", ephemeral=True)

        # Log action
        log_channel = self.bot.get_log_channel(interaction.guild)
        if log_channel:
            embed_log = discord.Embed(
                title="🧹 Warnings Cleared",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed_log.add_field(name="User", value=f"{member.mention} ({member} / {member.id})", inline=False)
            embed_log.add_field(name="Moderator", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
            await log_channel.send(embed=embed_log)

async def setup(bot):
    await bot.add_cog(WarningsCog(bot))
