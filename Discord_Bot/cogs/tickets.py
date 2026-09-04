import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import sqlite3
from cogs.utils import check_is_allowed

class TicketWelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_welcome_close")
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("TicketsCog") or interaction.client.get_cog("ticket")
        if cog:
            await cog.execute_close(interaction)
        else:
            await interaction.response.send_message("❌ Error: Tickets cog not loaded.", ephemeral=True)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.secondary, emoji="❌", custom_id="ticket_welcome_delete")
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("TicketsCog") or interaction.client.get_cog("ticket")
        if cog:
            await cog.execute_delete(interaction)
        else:
            await interaction.response.send_message("❌ Error: Tickets cog not loaded.", ephemeral=True)

class TicketsCog(commands.GroupCog, name="ticket", description="Moderation Support Ticket System"):
    def __init__(self, bot):
        self.bot = bot

    async def execute_close(self, interaction: discord.Interaction):
        """Generates transcript, logs it to mod logs channel, and deletes the channel."""
        db = self.bot.db
        
        # Verify it's a ticket channel
        is_ticket = await db.async_is_ticket_channel(interaction.channel_id)
        if not is_ticket:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ This is not an active support ticket channel.", ephemeral=True)
            else:
                await interaction.followup.send("❌ This is not an active support ticket channel.", ephemeral=True)
            return

        if not interaction.response.is_done():
            await interaction.response.defer()

        # 1. Fetch channel messages to build transcript
        messages = []
        async for msg in interaction.channel.history(limit=5000, oldest_first=True):
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            attachment_text = f" (Attachments: {', '.join(a.url for a in msg.attachments)})" if msg.attachments else ""
            messages.append(f"[{timestamp}] {msg.author} ({msg.author.id}): {msg.content}{attachment_text}")

        transcript_content = "\n".join(messages)
        transcript_file = discord.File(
            io.BytesIO(transcript_content.encode('utf-8')),
            filename=f"transcript-{interaction.channel.name}.txt"
        )

        # 2. Get mod log channel
        log_channel = self.bot.get_log_channel(interaction.guild)
        
        # 3. Post to logs
        if log_channel:
            embed = discord.Embed(
                title="🎟️ Ticket Closed & Logged",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Ticket Channel", value=interaction.channel.name, inline=True)
            embed.add_field(name="Closed By", value=f"{interaction.user.mention} ({interaction.user})", inline=True)
            
            try:
                await log_channel.send(embed=embed, file=transcript_file)
            except Exception as e:
                print(f"Failed to post ticket log: {e}")

        # 4. Clean up database
        await db.async_delete_ticket(interaction.channel_id)

        # 5. Alert and Delete Channel
        await interaction.followup.send("🔒 **Ticket Closed**: Generating transcript and deleting channel in 5 seconds...")
        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete(reason=f"Support ticket closed by {interaction.user}")
        except discord.Forbidden:
            print(f"❌ Tickets: Bot failed to delete channel {interaction.channel.name} due to missing permissions.")

    async def execute_delete(self, interaction: discord.Interaction):
        """Deletes the ticket channel instantly with no logs or transcripts."""
        db = self.bot.db
        
        # Verify it's a ticket channel
        is_ticket = await db.async_is_ticket_channel(interaction.channel_id)
        if not is_ticket:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ This is not an active support ticket channel.", ephemeral=True)
            else:
                await interaction.followup.send("❌ This is not an active support ticket channel.", ephemeral=True)
            return

        if not interaction.response.is_done():
            await interaction.response.defer()

        # 1. Clean up database
        await db.async_delete_ticket(interaction.channel_id)

        # 2. Alert and delete channel immediately
        await interaction.followup.send("❌ **Ticket Deleted**: Deleting channel immediately...")
        await asyncio.sleep(1)
        
        try:
            await interaction.channel.delete(reason=f"Support ticket deleted by {interaction.user}")
        except discord.Forbidden:
            print(f"❌ Tickets: Bot failed to delete channel {interaction.channel.name} due to missing permissions.")

    @app_commands.command(name="open", description="Opens a private support ticket.")
    @app_commands.describe(topic="Brief description of your support request")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    async def open_ticket(self, interaction: discord.Interaction, topic: str = None):
        guild = interaction.guild
        user = interaction.user
        db = self.bot.db

        # 1. Check if user already has an active ticket
        existing_chan_id = await db.async_get_user_ticket(guild.id, user.id)
        if existing_chan_id:
            existing_chan = guild.get_channel(existing_chan_id)
            if existing_chan:
                await interaction.response.send_message(
                    f"❌ You already have an active support ticket in {existing_chan.mention}.",
                    ephemeral=True
                )
                return
            else:
                # Channel was deleted manually. Clean database.
                await db.async_delete_ticket(existing_chan_id)

        # 2. Get support roles
        staff_role_ids = self.bot.ticket_staff_roles.get(guild.id, set())
        if not staff_role_ids:
            await interaction.response.send_message(
                "❌ No support staff roles are configured for this server. Ask an administrator to run `/ticket config_role`.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # 3. Create overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)
        }
        
        # Grant view access to all configured staff roles
        for r_id in staff_role_ids:
            staff_role = guild.get_role(r_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)

        # 4. Create channel
        clean_name = "".join(c for c in user.name if c.isalnum() or c in ("-", "_")).lower()
        ticket_chan = await guild.create_text_channel(
            name=f"ticket-{clean_name}",
            overwrites=overwrites,
            reason=f"Support ticket opened by {user}"
        )

        # 5. Save in database
        await db.async_create_ticket(ticket_chan.id, guild.id, user.id)

        # 6. Send welcome embed
        welcome_embed = discord.Embed(
            title=f"🎟️ Ticket opened by {user.display_name}",
            description=(
                f"**Topic**: {topic if topic else 'General Support'}\n\n"
                "Our support staff will be with you shortly.\n"
                "To manage this ticket, click a button below or type `/ticket close` / `/ticket delete`."
            ),
            color=discord.Color.blue()
        )
        welcome_embed.set_thumbnail(url=user.display_avatar.url)
        
        view = TicketWelcomeView()
        await ticket_chan.send(embed=welcome_embed, view=view)

        await interaction.followup.send(f"✅ Support ticket opened! Join here: {ticket_chan.mention}", ephemeral=True)

    @app_commands.command(name="close", description="Generates transcript, logs it, and deletes the support channel.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    async def close_ticket(self, interaction: discord.Interaction):
        await self.execute_close(interaction)

    @app_commands.command(name="delete", description="Instantly deletes the support channel with no logs or transcripts.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    async def delete_ticket(self, interaction: discord.Interaction):
        await self.execute_delete(interaction)

    @app_commands.command(name="config_role", description="Configures the support staff roles who can view ticket channels.")
    @app_commands.describe(
        action="Whether to add, remove, or list staff roles",
        role="The staff role to add or remove (Not required for 'list')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Staff Role", value="add"),
        app_commands.Choice(name="Remove Staff Role", value="remove"),
        app_commands.Choice(name="List Configured Roles", value="list")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def config_role(self, interaction: discord.Interaction, action: str, role: discord.Role = None):
        guild_id = interaction.guild_id
        
        if action == "list":
            roles = self.bot.ticket_staff_roles.get(guild_id, set())
            if not roles:
                await interaction.response.send_message("ℹ️ No support staff roles are currently configured.", ephemeral=True)
                return
            mentions = ", ".join(f"<@&{r_id}>" for r_id in roles)
            await interaction.response.send_message(f"📋 **Configured Support Staff Roles**: {mentions}", ephemeral=True)
            return

        if not role:
            await interaction.response.send_message("❌ A role must be provided to add or remove.", ephemeral=True)
            return

        if action == "add":
            await self.bot.db.async_add_ticket_staff_role(guild_id, role.id)
            if guild_id not in self.bot.ticket_staff_roles:
                self.bot.ticket_staff_roles[guild_id] = set()
            self.bot.ticket_staff_roles[guild_id].add(role.id)
            await interaction.response.send_message(
                f"✅ **Support Role Added**: Members with the role {role.mention} can now see new support ticket channels.",
                ephemeral=True
            )
        elif action == "remove":
            await self.bot.db.async_remove_ticket_staff_role(guild_id, role.id)
            if guild_id in self.bot.ticket_staff_roles:
                self.bot.ticket_staff_roles[guild_id].discard(role.id)
            await interaction.response.send_message(
                f"✅ **Support Role Removed**: Members with the role {role.mention} will no longer see new support ticket channels.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
