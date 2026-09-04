import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import re
import logging

class RemindersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger = logging.getLogger("RemindersCog")
        logger.setLevel(logging.INFO)
        self.logger = logger

    async def cog_load(self):
        self.reminder_check_loop.start()

    async def cog_unload(self):
        self.reminder_check_loop.cancel()

    def parse_time(self, time_str: str) -> int:
        """Parses a time string like '10m', '2h', '1d' into seconds."""
        time_str = time_str.lower().strip()
        pattern = re.compile(r"^(\d+)([shmd])$")
        match = pattern.match(time_str)
        if not match:
            return -1
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 's':
            return amount
        elif unit == 'm':
            return amount * 60
        elif unit == 'h':
            return amount * 3600
        elif unit == 'd':
            return amount * 86400
        return -1

    @app_commands.command(name="remind", description="Schedules a personal reminder.")
    @app_commands.describe(
        duration="Time duration (e.g. 10m, 2h, 1d)",
        message="The reminder message"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def remind(self, interaction: discord.Interaction, duration: str, message: str):
        seconds = self.parse_time(duration)
        if seconds <= 0:
            await interaction.response.send_message("❌ Invalid duration format. Please use format like `10m`, `2h`, `1d`.", ephemeral=True)
            return
            
        if seconds > 31536000: # Max 1 year
            await interaction.response.send_message("❌ Reminder duration is too long. Max duration is 1 year.", ephemeral=True)
            return

        due_time = int(time.time()) + seconds
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        user_id = interaction.user.id

        await self.bot.db.async_add_reminder(guild_id, user_id, channel_id, message, due_time)
        
        embed = discord.Embed(
            title="⏰ Reminder Scheduled",
            description=f"I will remind you about: **{message}**\nDue: <t:{due_time}:F> (<t:{due_time}:R>)",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @tasks.loop(seconds=10)
    async def reminder_check_loop(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        try:
            due_reminders = await self.bot.db.async_get_due_reminders(now)
            for reminder in due_reminders:
                reminder_id, guild_id, user_id, channel_id, message = reminder
                
                # Fetch target user
                user = self.bot.get_user(user_id)
                if not user:
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except discord.HTTPException:
                        await self.bot.db.async_delete_reminder(reminder_id)
                        continue

                # Try sending in channel first
                sent = False
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        try:
                            embed = discord.Embed(
                                title="⏰ Reminder!",
                                description=message,
                                color=discord.Color.gold()
                            )
                            await channel.send(content=f"{user.mention}", embed=embed)
                            sent = True
                        except discord.HTTPException:
                            pass 

                # Fallback to DM if not sent
                if not sent:
                    try:
                        embed = discord.Embed(
                            title="⏰ Reminder!",
                            description=message,
                            color=discord.Color.gold()
                        )
                        await user.send(embed=embed)
                    except discord.HTTPException:
                        self.logger.warning(f"Could not deliver reminder {reminder_id} to user {user_id} via channel or DM.")

                # Delete from DB
                await self.bot.db.async_delete_reminder(reminder_id)
                
        except Exception as e:
            self.logger.error(f"Error in reminder check loop: {e}")

async def setup(bot):
    await bot.add_cog(RemindersCog(bot))
