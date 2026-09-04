import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import time
import random
# Database connections handled via DatabaseManager
from cogs.utils import check_is_allowed

def parse_hex_color(color_str: str) -> discord.Color:
    """Parses standard hex colors (e.g. #FF5733 or 0xFF5733) or color names into discord.Color."""
    if not color_str:
        return discord.Color.blurple()
    
    color_str = color_str.strip().lstrip('#').lower()
    
    color_map = {
        "red": discord.Color.red(),
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "gold": discord.Color.gold(),
        "orange": discord.Color.orange(),
        "purple": discord.Color.purple(),
        "magenta": discord.Color.magenta(),
        "teal": discord.Color.teal()
    }
    
    if color_str in color_map:
        return color_map[color_str]
        
    try:
        val = int(color_str, 16)
        return discord.Color(val)
    except ValueError:
        return discord.Color.blurple()

class GiveawayButton(discord.ui.Button):
    def __init__(self, giveaway_id: int):
        super().__init__(
            label="🎉 Enter Giveaway",
            style=discord.ButtonStyle.blurple,
            custom_id=f"giveaway_enter:{giveaway_id}"
        )
        self.giveaway_id = giveaway_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = interaction.client.db
        
        # 1. Fetch required role from database
        required_role_id = await db.async_get_giveaway_requirement(self.giveaway_id)
        
        if required_role_id:
            # Check if user has required role
            role = interaction.guild.get_role(required_role_id)
            if role and role not in interaction.user.roles:
                await interaction.followup.send(
                    f"❌ You do not meet the requirement to join this giveaway! You must have the **{role.name}** role.",
                    ephemeral=True
                )
                return
        
        # 2. Toggle Entry
        entries = await db.async_get_giveaway_entries(self.giveaway_id)
        user_id = interaction.user.id
        
        if user_id in entries:
            # Leave
            await db.async_remove_giveaway_entry(self.giveaway_id, user_id)
            response_msg = "❌ You have left the giveaway."
        else:
            # Join
            await db.async_add_giveaway_entry(self.giveaway_id, user_id)
            response_msg = "🎉 You have entered the giveaway!"
            
        # Get updated count
        entries = await db.async_get_giveaway_entries(self.giveaway_id)
        
        # Update original message embed footer
        try:
            message = interaction.message
            if message and message.embeds:
                embed = message.embeds[0]
                embed.set_footer(text=f"Entrants: {len(entries)}")
                await message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating giveaway message: {e}")
            
        await interaction.followup.send(response_msg, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.add_item(GiveawayButton(giveaway_id))

class GiveawaysCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_check_loop.start()

    def cog_unload(self):
        self.giveaway_check_loop.cancel()

    def parse_duration(self, duration_str: str) -> int:
        duration_str = duration_str.lower().strip()
        if not duration_str:
            raise ValueError("Empty duration")
        
        unit = duration_str[-1]
        amount = duration_str[:-1]
        
        if not amount.isdigit():
            if duration_str.isdigit():
                return int(duration_str)
            raise ValueError("Invalid duration format")
            
        val = int(amount)
        if unit == 's':
            return val
        elif unit == 'm':
            return val * 60
        elif unit == 'h':
            return val * 3600
        elif unit == 'd':
            return val * 86400
        else:
            raise ValueError("Invalid time unit (use s/m/h/d)")

    @app_commands.command(name="giveaway", description="Starts a giveaway in a channel.")
    @app_commands.describe(
        duration="Duration of giveaway (e.g. 30s, 10m, 2h, 1d)",
        winners="Number of winners",
        prize="The prize to give away",
        channel="The channel for the giveaway (Defaults to current channel)",
        required_role="Role required to enter this giveaway",
        color="Embed color (Hex code e.g. #FF5733 or name e.g. red)"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str, channel: discord.TextChannel = None, required_role: discord.Role = None, color: str = None):
        target_channel = channel or interaction.channel
        
        try:
            duration_seconds = self.parse_duration(duration)
        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid duration format: {e}", ephemeral=True)
            return

        if winners <= 0:
            await interaction.response.send_message("❌ Winners count must be at least 1.", ephemeral=True)
            return

        # Calculate end Unix timestamp
        end_time = int(time.time()) + duration_seconds
        
        # Defer interaction
        await interaction.response.defer(ephemeral=True)
        
        # Parse embed color
        embed_color = parse_hex_color(color)
        
        # Description text
        desc = f"**Prize**: **{prize}**\n\n**Ends**: <t:{end_time}:F> (<t:{end_time}:R>)\n**Hosted by**: {interaction.user.mention}\n**Winners**: {winners}"
        if required_role:
            desc += f"\n\n🔒 **Requirement**: Only users with {required_role.mention} can enter!"
            
        # Send initial embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=desc,
            color=embed_color
        )
        embed.set_footer(text="Entrants: 0")
        
        try:
            # Create the giveaway record in the DB and get the autoincrement ID
            giveaway_id = await self.bot.db.async_create_giveaway(
                interaction.guild_id, target_channel.id, 0, prize, winners, end_time, required_role.id if required_role else None
            )
            
            # Instantiate View & Send message
            view = GiveawayView(giveaway_id)
            msg = await target_channel.send(embed=embed, view=view)
            
            # Update message_id in DB
            await self.bot.db.async_update_giveaway_message(giveaway_id, msg.id)
            
            # Register the view with the bot
            self.bot.add_view(view)
            
            await interaction.followup.send(f"✅ Giveaway started in {target_channel.mention}!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to start giveaway: {e}", ephemeral=True)
            print(f"Error starting giveaway: {e}")

    @tasks.loop(seconds=10)
    async def giveaway_check_loop(self):
        try:
            active_giveaways = await self.bot.db.async_load_active_giveaways()
            now = int(time.time())
            
            for giveaway in active_giveaways:
                # giveaway row format is: giveaway_id, guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id
                giveaway_id, guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id = giveaway
                
                if now >= end_time:
                    # End the giveaway!
                    await self.bot.db.async_end_giveaway(giveaway_id)
                    
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                        
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        continue
                        
                    try:
                        message = await channel.fetch_message(message_id)
                    except (discord.NotFound, discord.HTTPException):
                        message = None
                        
                    entries = await self.bot.db.async_get_giveaway_entries(giveaway_id)
                    
                    if not entries:
                        # No entrants
                        if message:
                            embed = message.embeds[0] if message.embeds else discord.Embed(title="Giveaway")
                            embed.title = "🎉 GIVEAWAY ENDED 🎉"
                            embed.description = f"**Prize**: {prize}\n\n**Winners**: No entries!"
                            embed.color = discord.Color.red()
                            embed.set_footer(text="Entrants: 0")
                            await message.edit(embed=embed, view=None)
                            
                        await channel.send(f"😢 The giveaway for **{prize}** ended, but no one entered!")
                    else:
                        # Pick winners
                        winners_list = random.sample(entries, k=min(len(entries), winner_count))
                        winner_mentions = ", ".join(f"<@{w_id}>" for w_id in winners_list)
                        
                        if message:
                            embed = message.embeds[0] if message.embeds else discord.Embed(title="Giveaway")
                            embed.title = "🎉 GIVEAWAY ENDED 🎉"
                            embed.description = f"**Prize**: **{prize}**\n\n**Winner(s)**: {winner_mentions}\n**Total Entrants**: {len(entries)}"
                            embed.color = discord.Color.gold()
                            embed.set_footer(text=f"Entrants: {len(entries)}")
                            await message.edit(embed=embed, view=None)
                            
                        await channel.send(f"🎉 **Congratulations** to {winner_mentions}! You won the giveaway for **{prize}**!")
                        
        except Exception as e:
            print(f"Error in giveaway check loop: {e}")

    @giveaway_check_loop.before_loop
    async def before_giveaway_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(GiveawaysCog(bot))
