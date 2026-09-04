import discord
from discord import app_commands
from discord.ext import commands

class HoneypotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banning_in_progress = set()

    @app_commands.command(name="honeypot", description="Sets up a honeypot channel to catch and ban self-bots/raiders.")
    @app_commands.describe(channel="The channel to set as a honeypot")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def honeypot(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Ensure only Server Administrators, Owner, or Developer can execute
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id or interaction.user.id == self.bot.dev_id):
            await interaction.response.send_message("❌ Authorization failed: Administrator permissions required.", ephemeral=True)
            return

        self.bot.honeypot_channels[interaction.guild_id] = channel.id
        await self.bot.save_data()

        # Stylized warning message
        warning_text = (
            "⚠️ WARNING: This is a Honeypot channel. DO NOT message in here. "
            "If you type a message in this channel, your account will be automatically banned "
            "and your message history from the past 24 hours will be purged server-wide. "
            "If you are a human and did this by mistake, contact an Admin to appeal. "
            "Repeat offenders will remain banned permanently."
        )

        embed = discord.Embed(
            title="🚨 SECURITY WARNING: HONEYPOT ZONE",
            description=warning_text,
            color=discord.Color.red()
        )
        embed.set_footer(text="Automated Defense Protocol Active")

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Honeypot set to {channel.mention} and warning embed deployed successfully.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"⚠️ Saved channel, but bot lacks permissions to message in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="honeypot_logs", description="Sets up the designated log channel for honeypot events.")
    @app_commands.describe(channel="The channel to send honeypot logs to")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def honeypot_logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Ensure only Server Administrators, Owner, or Developer can execute
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id or interaction.user.id == self.bot.dev_id):
            await interaction.response.send_message("❌ Authorization failed: Administrator permissions required.", ephemeral=True)
            return

        self.bot.honeypot_log_channels[interaction.guild_id] = channel.id
        await self.bot.save_data()
        await interaction.response.send_message(f"✅ Success: Honeypot logs will now be sent to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="honeypot_disable", description="Disables honeypot monitoring on this server.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def honeypot_disable(self, interaction: discord.Interaction):
        # Ensure only Server Administrators, Owner, or Developer can execute
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id or interaction.user.id == self.bot.dev_id):
            await interaction.response.send_message("❌ Authorization failed: Administrator permissions required.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        if guild_id in self.bot.honeypot_channels:
            del self.bot.honeypot_channels[guild_id]
            await self.bot.save_data()
            await interaction.response.send_message("✅ Success: Honeypot monitoring has been disabled for this server.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ There is no active honeypot channel configured on this server.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages outside a server context
        if not message.guild:
            return

        # Check if this channel is the guild's active honeypot channel
        honeypot_chan_id = self.bot.honeypot_channels.get(message.guild.id)
        if not honeypot_chan_id or message.channel.id != honeypot_chan_id:
            return

        # Ignore Bots, Server Owner, Bot Developer, or Administrators
        if message.author.bot:
            return
        
        if message.author.id == message.guild.owner_id:
            return

        if message.author.id == self.bot.dev_id:
            return

        if isinstance(message.author, discord.Member) and message.author.guild_permissions.administrator:
            return

        # Double trigger safety check
        if message.author.id in self.banning_in_progress:
            return
        self.banning_in_progress.add(message.author.id)

        try:
            # Instantly delete the triggering message
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            # Execute the Ban Hammer Sequence
            try:
                reason = "Triggered Honeypot security channel."
                # delete_message_seconds=86400 (24 hours of messages to delete)
                await message.guild.ban(message.author, delete_message_seconds=86400, reason=reason)
                
                # Prepare the log embed
                global_name = getattr(message.author, "global_name", None) or "None"
                log_embed = discord.Embed(
                    title="🚨 Honeypot Trap Triggered",
                    description="An unauthorized user sent a message in the honeypot channel and has been banned.",
                    color=discord.Color.dark_red()
                )
                log_embed.add_field(name="Username", value=message.author.name, inline=True)
                log_embed.add_field(name="Global Name", value=global_name, inline=True)
                log_embed.add_field(name="Discord ID", value=str(message.author.id), inline=False)
                log_embed.add_field(name="Status", value="✅ Account banned. Message history from the past 24 hours has been purged server-wide.", inline=False)
                
                # Determine destination log channel
                log_chan_id = self.bot.honeypot_log_channels.get(message.guild.id)
                log_channel = message.guild.get_channel(log_chan_id) if log_chan_id else None
                
                sent = False
                if log_channel:
                    try:
                        await log_channel.send(embed=log_embed)
                        sent = True
                    except Exception as e:
                        print(f"Error: Lacking permissions or failed to send log to log channel: {e}")
                
                # Console fallback if log channel is not configured or bot failed to send there
                if not sent:
                    print("=====================================================")
                    print("🚨 HONEYPOT BAN TRIGGERED (CONSOLE LOG FALLBACK)")
                    print(f"Username: {message.author.name}")
                    print(f"Global Name: {global_name}")
                    print(f"Discord ID: {message.author.id}")
                    print("Status: Account banned. 24h message history purged server-wide.")
                    print("=====================================================")

            except discord.Forbidden:
                fail_msg = f"❌ Failed to ban {message.author} - Bot lacks Ban Members permissions."
                print(fail_msg)
                # Try system channel fallback as an emergency notification
                if message.guild.system_channel:
                    try:
                        await message.guild.system_channel.send(fail_msg)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Exception during honeypot ban: {e}")
        finally:
            self.banning_in_progress.discard(message.author.id)

async def setup(bot):
    await bot.add_cog(HoneypotCog(bot))
