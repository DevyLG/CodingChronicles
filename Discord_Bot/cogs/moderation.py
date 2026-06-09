import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from cogs.utils import check_is_allowed

async def move_spam_loop(member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
    """Executes continuous voice channel oscillation for a targeted member."""
    current_channel = channel1 
    while True:
        try:
            # Check if member is still connected to a voice channel
            if not member.voice or not member.voice.channel:
                break
            
            target_channel = channel2 if current_channel.id == channel1.id else channel1
            current_channel = target_channel
            await member.edit(voice_channel=target_channel, reason="Automated move routine.")
            await asyncio.sleep(2) 
        except asyncio.CancelledError:
            raise
        except (discord.NotFound, discord.HTTPException):
            break 
        except Exception as e:
            print(f"Spam Loop Exception: {e}")
            await asyncio.sleep(5)

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mute", description="Enforces global silence (Chat & Voice).")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def mute(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.muted_members.add(member.id)
        await self.bot.save_data()
        if member.voice:
            try: 
                await member.edit(mute=True)
            except discord.Forbidden: 
                pass
        await interaction.response.send_message(f"🤐 Silence protocol active: {member.mention}", ephemeral=True)

    @app_commands.command(name="unmute", description="Revokes global silence restriction.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.muted_members.discard(member.id)
        await self.bot.save_data()
        if member.voice:
            try: 
                await member.edit(mute=False)
            except discord.Forbidden: 
                pass
        await interaction.response.send_message(f"🗣️ Silence protocol terminated: {member.mention}", ephemeral=True)

    @app_commands.command(name="move_spam", description="Initiates voice channel oscillation.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def move_spam(self, interaction: discord.Interaction, member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
        if member.id == interaction.user.id or member.id in self.bot.spam_move_tasks or not (member.voice and member.voice.channel):
            await interaction.response.send_message("Invalid parameters or state.", ephemeral=True)
            return
        self.bot.spam_move_tasks[member.id] = asyncio.create_task(move_spam_loop(member, channel1, channel2))
        await interaction.response.send_message(f"Oscillation routine initiated on {member.name}.", ephemeral=True)

    @app_commands.command(name="unmove", description="Terminates voice channel oscillation.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def unmove(self, interaction: discord.Interaction, member: discord.Member):
        if member.id in self.bot.spam_move_tasks:
            self.bot.spam_move_tasks.pop(member.id).cancel()
            await interaction.response.send_message("Oscillation routine terminated.", ephemeral=True)
        else:
            await interaction.response.send_message("Target is not currently being oscillated.", ephemeral=True)

    @app_commands.command(name="voiceban", description="Revokes voice channel connection privileges.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def voiceban(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.voicebanned_members.add(member.id)
        await self.bot.save_data()
        if member.voice: 
            try:
                await member.edit(voice_channel=None)
            except discord.Forbidden:
                pass
        await interaction.response.send_message(f"Voice privileges revoked for {member.name}.", ephemeral=True)

    @app_commands.command(name="unvoiceban", description="Restores voice channel connection privileges.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def unvoiceban(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.voicebanned_members.discard(member.id)
        await self.bot.save_data()
        await interaction.response.send_message(f"Voice privileges restored for {member.name}.", ephemeral=True)

    @app_commands.command(name="purge", description="Bulk message deletion protocol.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount < 1: 
            await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f'Purged {len(deleted)} messages.', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error purging messages: {e}", ephemeral=True)

    @app_commands.command(name="redditmode", description="Toggles automatic upvote/downvote reactions.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def redditmode(self, interaction: discord.Interaction):
        if interaction.channel.id in self.bot.reddit_mode_channels:
            self.bot.reddit_mode_channels.remove(interaction.channel.id)
            await interaction.response.send_message('Reddit mode: DISABLED.', ephemeral=True)
        else:
            self.bot.reddit_mode_channels.add(interaction.channel.id)
            await interaction.response.send_message('Reddit mode: ENABLED.', ephemeral=True)
        await self.bot.save_data()

    @app_commands.command(name="smashorpass", description="Toggles automatic evaluation reactions.")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def smashorpass(self, interaction: discord.Interaction):
        if interaction.channel.id in self.bot.smash_or_pass_channels:
            self.bot.smash_or_pass_channels.remove(interaction.channel.id)
            await interaction.response.send_message('Evaluation mode: DISABLED.', ephemeral=True)
        else:
            self.bot.smash_or_pass_channels.add(interaction.channel.id)
            await interaction.response.send_message('Evaluation mode: ENABLED.', ephemeral=True)
        await self.bot.save_data()

    # --- Listeners ---

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id in self.bot.voicebanned_members and after.channel is not None:
            try:
                await member.edit(voice_channel=None)
            except discord.Forbidden:
                pass
            
        if member.id in self.bot.muted_members and after.channel is not None:
            if not after.mute:
                try: 
                    await member.edit(mute=True)
                except discord.Forbidden: 
                    pass
                    
        if after.channel is None and member.id in self.bot.spam_move_tasks:
            task = self.bot.spam_move_tasks.pop(member.id)
            task.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: 
            return
            
        if message.author.id in self.bot.muted_members:
            try: 
                await message.delete()
            except discord.Forbidden: 
                pass 
            return

        if message.channel.id in self.bot.reddit_mode_channels:
            try:
                await message.add_reaction('⬆️')
                await message.add_reaction('⬇️')
            except discord.HTTPException:
                pass
            
        if message.channel.id in self.bot.smash_or_pass_channels and message.attachments:
            try:
                await message.add_reaction('\U0001F4A5') 
                await message.add_reaction('\U0001F6AB') 
            except discord.HTTPException: 
                pass

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
