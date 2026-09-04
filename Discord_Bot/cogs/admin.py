import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addadmin", description="Grants administrative clearance to a user ID for this server.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def addadmin(self, interaction: discord.Interaction, user: discord.User):
        guild_id = interaction.guild_id
        if guild_id not in self.bot.bot_admins:
            self.bot.bot_admins[guild_id] = set()
        self.bot.bot_admins[guild_id].add(user.id)
        await self.bot.save_data()
        await interaction.response.send_message(f"✅ Authorization granted for this server: {user.name}", ephemeral=True)

    @app_commands.command(name="removeadmin", description="Revokes administrative clearance from a user ID for this server.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def removeadmin(self, interaction: discord.Interaction, user: discord.User):
        guild_id = interaction.guild_id
        guild_admins = self.bot.bot_admins.get(guild_id, set())
        if user.id in guild_admins:
            guild_admins.remove(user.id)
            await self.bot.save_data()
            await interaction.response.send_message(f"🗑️ Authorization revoked for this server: {user.name}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ User is not an admin on this server.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
