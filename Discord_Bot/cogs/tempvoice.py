import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging

class TempVoiceCog(commands.GroupCog, name="tempvoice"):
    def __init__(self, bot):
        self.bot = bot
        self.active_temp_channels = {}
        logger = logging.getLogger("TempVoiceCog")
        logger.setLevel(logging.INFO)
        self.logger = logger

    async def cog_load(self):
        try:
            voices = await self.bot.db.async_get_all_temp_voices()
            self.active_temp_channels = {row[0]: {"guild_id": row[1], "owner_id": row[2]} for row in voices}
            
            # Start background cleanup of orphaned or empty channels
            asyncio.create_task(self.cleanup_orphaned_channels())
        except Exception as e:
            self.logger.error(f"Error in cog_load: {e}")

    async def cleanup_orphaned_channels(self):
        await self.bot.wait_until_ready()
        
        self.logger.info("Starting temporary voice channel cleanup...")
        for channel_id, info in list(self.active_temp_channels.items()):
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Already manually deleted, clean from DB
                await self.bot.db.async_delete_temp_voice(channel_id)
                self.active_temp_channels.pop(channel_id, None)
                self.logger.info(f"Cleaned up deleted channel ID {channel_id} from database.")
                continue
            
            try:
                if len(channel.members) == 0:
                    await channel.delete(reason="Temporary voice channel cleanup on startup.")
                    await self.bot.db.async_delete_temp_voice(channel_id)
                    self.active_temp_channels.pop(channel_id, None)
                    self.logger.info(f"Deleted empty channel {channel.name} ({channel_id}) on startup.")
            except discord.HTTPException as e:
                self.logger.error(f"Failed to delete channel {channel_id}: {e}")

    @app_commands.command(name="setup", description="Sets up a master 'Join to Create' voice channel.")
    @app_commands.describe(channel="The voice channel that users join to create dynamic channels")
    @app_commands.allowed_installs(guilds=True)
    @app_commands.allowed_contexts(guilds=True)
    async def setup_tempvoice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        if not interaction.client.is_allowed(interaction):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        await self.bot.db.async_add_temp_generator(channel.id, interaction.guild.id)
        self.bot.temp_generators.add(channel.id)
        
        embed = discord.Embed(
            title="🔊 Temp Voice Setup",
            description=f"Successfully configured {channel.mention} as a dynamic voice generator channel.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remove", description="Removes a 'Join to Create' voice channel setup.")
    @app_commands.describe(channel="The voice channel to remove from setup")
    @app_commands.allowed_installs(guilds=True)
    @app_commands.allowed_contexts(guilds=True)
    async def remove_tempvoice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        if not interaction.client.is_allowed(interaction):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        if channel.id not in self.bot.temp_generators:
            await interaction.response.send_message("❌ That channel is not configured as a dynamic voice generator.", ephemeral=True)
            return

        await self.bot.db.async_remove_temp_generator(channel.id)
        self.bot.temp_generators.discard(channel.id)
        
        embed = discord.Embed(
            title="🔊 Temp Voice Removed",
            description=f"Successfully removed {channel.mention} from dynamic voice generators.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. Join voice generator channel
        if after.channel and after.channel.id in self.bot.temp_generators:
            generator_channel = after.channel
            guild = member.guild
            
            channel_name = f"🔊 {member.display_name}'s Lobby"
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, connect=True, move_members=True)
            }
            
            try:
                new_channel = await guild.create_voice_channel(
                    name=channel_name,
                    category=generator_channel.category,
                    overwrites=overwrites,
                    reason=f"Temporary voice channel for {member}"
                )
                
                await member.move_to(new_channel)
                
                await self.bot.db.async_add_temp_voice(new_channel.id, guild.id, member.id)
                self.active_temp_channels[new_channel.id] = {"guild_id": guild.id, "owner_id": member.id}
                
                await new_channel.send(
                    f"Welcome {member.mention} to your temporary voice channel!\n"
                    "• You have **Manage Channel** and **Move Members** permissions here.\n"
                    "• This channel will be automatically deleted when all members leave."
                )
                
            except discord.HTTPException as e:
                self.logger.error(f"Error creating temp voice channel: {e}")
                
        # 2. Leave voice channel
        if before.channel and before.channel.id in self.active_temp_channels:
            temp_channel = before.channel
            
            if len(temp_channel.members) == 0:
                try:
                    await temp_channel.delete(reason="Temporary voice channel empty.")
                    await self.bot.db.async_delete_temp_voice(temp_channel.id)
                    self.active_temp_channels.pop(temp_channel.id, None)
                except discord.HTTPException as e:
                    self.logger.error(f"Error deleting empty voice channel: {e}")

async def setup(bot):
    await bot.add_cog(TempVoiceCog(bot))
