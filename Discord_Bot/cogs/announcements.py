import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

class AnnouncementModal(discord.ui.Modal):
    """Interactive Modal for building announcements."""
    def __init__(self, channel: discord.TextChannel, ping: str = None):
        super().__init__(title="Create Announcement")
        self.channel = channel
        self.ping = ping

        self.announce_title = discord.ui.TextInput(
            label="Announcement Title",
            style=discord.TextStyle.short,
            placeholder="e.g. Server Maintenance Notice",
            required=True,
            max_length=256
        )
        self.add_item(self.announce_title)

        self.announce_body = discord.ui.TextInput(
            label="Announcement Body",
            style=discord.TextStyle.long,
            placeholder="Type your announcement message here...",
            required=True,
            max_length=4000
        )
        self.add_item(self.announce_body)

        self.embed_color = discord.ui.TextInput(
            label="Embed Color (Hex Code)",
            style=discord.TextStyle.short,
            placeholder="e.g. #ff0000 or 00ff00 (Defaults to blue)",
            required=False,
            max_length=7
        )
        self.add_item(self.embed_color)

        self.footer_text = discord.ui.TextInput(
            label="Footer Text",
            style=discord.TextStyle.short,
            placeholder="e.g. Sent by Server Staff",
            required=False,
            max_length=2048
        )
        self.add_item(self.footer_text)

        self.image_url = discord.ui.TextInput(
            label="Image/GIF URL",
            style=discord.TextStyle.short,
            placeholder="e.g. https://domain.com/image.png (Optional)",
            required=False,
            max_length=1024
        )
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Parse Color
        color_val = discord.Color.blue()
        color_str = self.embed_color.value.strip().lstrip('#')
        if color_str:
            try:
                color_val = discord.Color(int(color_str, 16))
            except ValueError:
                pass  # Fallback to blue on invalid hex code

        # 2. Build Embed
        embed = discord.Embed(
            title=self.announce_title.value,
            description=self.announce_body.value,
            color=color_val
        )

        if self.footer_text.value.strip():
            embed.set_footer(text=self.footer_text.value.strip())

        if self.image_url.value.strip():
            url = self.image_url.value.strip()
            if url.startswith("http://") or url.startswith("https://"):
                embed.set_image(url=url)

        # 3. Send Announcement
        ping_content = None
        if self.ping == "everyone":
            ping_content = "@everyone"
        elif self.ping == "here":
            ping_content = "@here"

        try:
            await self.channel.send(content=ping_content, embed=embed)
            await interaction.response.send_message(f"✅ Success: Announcement posted in {self.channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Error: Bot lacks permissions to send messages in {self.channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error posting announcement: {e}", ephemeral=True)


class AnnouncementsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Opens an interactive modal to build and post announcement embeds.")
    @app_commands.describe(
        channel="The target channel to send the announcement to",
        ping="Optional role mention to accompany the announcement embed"
    )
    @app_commands.choices(ping=[
        app_commands.Choice(name="None", value="none"),
        app_commands.Choice(name="Pings @everyone", value="everyone"),
        app_commands.Choice(name="Pings @here", value="here")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, ping: app_commands.Choice[str] = None):
        ping_val = ping.value if ping else "none"
        modal = AnnouncementModal(channel=channel, ping=ping_val)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(AnnouncementsCog(bot))
