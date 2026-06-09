import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addadmin", description="Grants administrative clearance to a user ID.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def addadmin(self, interaction: discord.Interaction, user: discord.User):
        self.bot.bot_admins.add(user.id)
        await self.bot.save_data()
        await interaction.response.send_message(f"✅ Authorization granted: {user.name}", ephemeral=True)

    @app_commands.command(name="removeadmin", description="Revokes administrative clearance from a user ID.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def removeadmin(self, interaction: discord.Interaction, user: discord.User):
        self.bot.bot_admins.discard(user.id)
        await self.bot.save_data()
        await interaction.response.send_message(f"🗑️ Authorization revoked: {user.name}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
