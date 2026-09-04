import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class AutoRolesCog(commands.GroupCog, name="autorole", description="Manage automatic role assignment on member join."):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add", description="Adds a role to be automatically assigned to new members.")
    @app_commands.describe(role="The role to automatically grant")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def autorole_add(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = interaction.guild_id
        
        # Prevent adding @everyone or managed roles
        if role.is_default() or role.managed:
            await interaction.response.send_message(
                "❌ You cannot add the default role or a bot-managed role to Auto-Roles.",
                ephemeral=True
            )
            return

        # Save to database
        await self.bot.db.async_add_autorole(guild_id, role.id)

        # Update in-memory state
        if guild_id not in self.bot.autoroles:
            self.bot.autoroles[guild_id] = set()
        self.bot.autoroles[guild_id].add(role.id)

        await interaction.response.send_message(
            f"✅ Added {role.mention} to Auto-Roles. New members will receive this role on join.",
            ephemeral=True
        )

    @app_commands.command(name="remove", description="Removes a role from the automatic join assignment list.")
    @app_commands.describe(role="The role to stop automatically granting")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def autorole_remove(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = interaction.guild_id

        # Delete from database
        await self.bot.db.async_remove_autorole(guild_id, role.id)

        # Update in-memory state
        if guild_id in self.bot.autoroles:
            self.bot.autoroles[guild_id].discard(role.id)

        await interaction.response.send_message(
            f"✅ Removed {role.mention} from Auto-Roles.",
            ephemeral=True
        )

    @app_commands.command(name="list", description="Lists all roles currently configured for auto-assignment.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def autorole_list(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        role_ids = self.bot.autoroles.get(guild_id, set())

        if not role_ids:
            await interaction.response.send_message(
                "ℹ️ No auto-assign roles are configured for this server.",
                ephemeral=True
            )
            return

        mentions = ", ".join(f"<@&{r_id}>" for r_id in role_ids)
        
        embed = discord.Embed(
            title="📋 Configured Auto-Roles",
            description=f"New members will be granted these roles on join:\n\n{mentions}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Listens for new member joins and automatically grants configured roles."""
        guild = member.guild
        role_ids = self.bot.autoroles.get(guild.id, set())
        if not role_ids:
            return

        # Wait a brief moment to let other join processes (like Join Shield kicks) execute
        await asyncio.sleep(2)

        # Check if the member is still in the server
        if not guild.get_member(member.id):
            return

        roles_to_add = []
        for r_id in role_ids:
            role = guild.get_role(r_id)
            if role:
                roles_to_add.append(role)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Auto-Roles on Join")
            except discord.Forbidden:
                print(f"❌ Auto-Roles: Lacks permissions to assign roles to {member} in {guild.name}")
            except discord.HTTPException as e:
                print(f"❌ Auto-Roles: Failed to add roles to {member}: {e}")

async def setup(bot):
    await bot.add_cog(AutoRolesCog(bot))
