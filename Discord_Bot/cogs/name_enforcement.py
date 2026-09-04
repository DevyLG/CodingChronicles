import discord
from discord import app_commands
from discord.ext import commands, tasks
from cogs.utils import check_is_allowed

class NameEnforcerCog(commands.GroupCog, name="name", description="Manage profile enforcement policies."):
    def __init__(self, bot):
        self.bot = bot

    def cog_load(self):
        if not self.enforce_nicknames_loop.is_running():
            self.enforce_nicknames_loop.start()

    def cog_unload(self):
        self.enforce_nicknames_loop.cancel()

    @tasks.loop(seconds=10)
    async def enforce_nicknames_loop(self):
        """Polls target guilds to ensure enforced nicknames remain consistent."""
        for guild in self.bot.guilds:
            if guild.id not in self.bot.name_enforced_guilds:
                continue
                
            for user_id, forced_nick in list(self.bot.enforced_names.items()):
                if user_id in self.bot.disabled_name_enforcements:
                    continue
                    
                should_enforce = self.bot.name_enforcement_on or (user_id in self.bot.enabled_name_enforcements)
                if not should_enforce:
                    continue
                    
                member = guild.get_member(user_id)
                if member and member.display_name != forced_nick:
                    if member.id == guild.owner_id: continue
                    if member.top_role >= guild.me.top_role: continue
                    
                    try:
                        await member.edit(nick=forced_nick)
                    except discord.Forbidden:
                        pass

    @app_commands.command(name="change", description="Registers a persistent nickname payload.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def name_change(self, interaction: discord.Interaction, member: discord.Member, name: str):
        self.bot.enforced_names[member.id] = name
        self.bot.enabled_name_enforcements.add(member.id)
        await self.bot.save_names() 
        
        if member.id in self.bot.disabled_name_enforcements:
            self.bot.disabled_name_enforcements.remove(member.id)
            
        await self.bot.save_data()

        try:
            await member.edit(nick=name)
            await interaction.response.send_message(f"✅ Executed: Payload **{name}** assigned to {member.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Saved to registry, but inadequate permissions to push update.", ephemeral=True)

    @app_commands.command(name="toggle", description="Modifies enforcement state flags.")
    @app_commands.choices(state=[
        app_commands.Choice(name="On (Force Enable)", value="on"),
        app_commands.Choice(name="Off (Force Disable)", value="off"),
        app_commands.Choice(name="Reset (Default)", value="reset")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def name_toggle(self, interaction: discord.Interaction, state: str, member: discord.Member = None):
        if member:
            if member.id not in self.bot.enforced_names:
                await interaction.response.send_message("Target not found in registry.", ephemeral=True)
                return

            if state == "reset":
                self.bot.enabled_name_enforcements.discard(member.id)
                self.bot.disabled_name_enforcements.discard(member.id)
                await self.bot.save_data()
                await interaction.response.send_message(f"♻️ Reverted state flags for {member.mention}.", ephemeral=True)

            elif state == "on":
                self.bot.enabled_name_enforcements.add(member.id)
                self.bot.disabled_name_enforcements.discard(member.id)
                await self.bot.save_data()
                await interaction.response.send_message(f"🟢 State [Enabled] forced for {member.mention}.", ephemeral=True)
            
            elif state == "off":
                self.bot.disabled_name_enforcements.add(member.id)
                self.bot.enabled_name_enforcements.discard(member.id)
                await self.bot.save_data()
                await interaction.response.send_message(f"🔴 State [Disabled] forced for {member.mention}.", ephemeral=True)
                
        else:
            if state == "reset":
                 await interaction.response.send_message("Invalid operation. Global flag cannot be reset.", ephemeral=True)
            elif state == "on":
                self.bot.name_enforcement_on = True
                await interaction.response.send_message("🟢 Global enforcement flag: TRUE.", ephemeral=True)
            elif state == "off":
                self.bot.name_enforcement_on = False
                await interaction.response.send_message("🔴 Global enforcement flag: FALSE.", ephemeral=True)

    @app_commands.command(name="server", description="Modifies server-level enforcement permissions.")
    @app_commands.choices(state=[
        app_commands.Choice(name="On (Allow)", value="on"),
        app_commands.Choice(name="Off (Block)", value="off")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def name_server(self, interaction: discord.Interaction, state: str):
        if state == "on":
            self.bot.name_enforced_guilds.add(interaction.guild_id)
            await self.bot.save_data()
            await interaction.response.send_message("🟢 Guild added to enforcement pool.", ephemeral=True)
        else:
            self.bot.name_enforced_guilds.discard(interaction.guild_id)
            await self.bot.save_data()
            await interaction.response.send_message("🔴 Guild removed from enforcement pool.", ephemeral=True)

    @app_commands.command(name="list", description="Lists all registered persistent nicknames and their enforcement states.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def name_list(self, interaction: discord.Interaction):
        if not self.bot.enforced_names:
            await interaction.response.send_message("ℹ️ No persistent nicknames are currently registered.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Persistent Nickname Registry",
            description="All registered nickname payloads and their enforcement status:",
            color=discord.Color.blue()
        )
        
        # Limit to 25 fields to fit Discord embeds
        count = 0
        for user_id, nick in list(self.bot.enforced_names.items()):
            if count >= 25:
                embed.set_footer(text="Showing first 25 entries. Registry holds more items.")
                break
                
            if user_id in self.bot.disabled_name_enforcements:
                state_str = "🔴 Force Disabled"
            elif user_id in self.bot.enabled_name_enforcements:
                state_str = "🟢 Force Enabled"
            else:
                state_str = "🟡 Default (Follows Global)"
                
            member = interaction.guild.get_member(user_id)
            user_text = member.mention if member else f"ID: {user_id}"
            user_tag = str(member) if member else f"User ID: {user_id}"
            
            embed.add_field(
                name=user_tag,
                value=f"**Mention**: {user_text}\n**Enforced Name**: `{nick}`\n**Status**: {state_str}",
                inline=False
            )
            count += 1
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Listeners ---

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Immediately enforces name when a registered user leaves and rejoins the server."""
        guild = member.guild
        if guild.id not in self.bot.name_enforced_guilds: return
        if member.id in self.bot.disabled_name_enforcements: return
        
        should_enforce = self.bot.name_enforcement_on or (member.id in self.bot.enabled_name_enforcements)
        if not should_enforce: return
        
        if member.id in self.bot.enforced_names:
            forced_name = self.bot.enforced_names[member.id]
            if member.display_name != forced_name:
                if member.id == guild.owner_id: return
                if member.top_role >= guild.me.top_role: return
                try:
                    await member.edit(nick=forced_name)
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Triggers immediate reversion if a user manually circumvents name enforcement."""
        if after.guild.id not in self.bot.name_enforced_guilds: return
        if after.id in self.bot.disabled_name_enforcements: return
        
        should_enforce = self.bot.name_enforcement_on or (after.id in self.bot.enabled_name_enforcements)
        if not should_enforce: return
        
        if after.id in self.bot.enforced_names:
            forced_name = self.bot.enforced_names[after.id]
            if after.display_name != forced_name:
                if after.id == after.guild.owner_id: return
                if after.top_role >= after.guild.me.top_role: return
                try: 
                    await after.edit(nick=forced_name)
                except discord.Forbidden: 
                    pass

async def setup(bot):
    await bot.add_cog(NameEnforcerCog(bot))
