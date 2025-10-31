import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands
import os


DATA_FILE = "bot_data.json"

with open("token.token", 'r') as f:
    DevyBot = f.read()

intents = discord.Intents.all()


bot = commands.Bot(command_prefix="!", intents=intents)

# --- IMPORTANT: For testing, add your server's ID here ---
# This makes commands update instantly in your server.
# For global commands, remove the guild=... part from the sync call below.
TEST_GUILD_ID = None # e.g., 123456789012345678


def is_allowed(interaction: discord.Interaction) -> bool:
    """Checks if the user is one of the allowed bot operators."""
    allowed_ids = [
        0 # Replace with your Discord user ID
    ]
    return interaction.user.id in allowed_ids

def load_data():
    """Loads data from the JSON file."""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return (
                set(data.get("voicebanned_members", [])),
                set(data.get("reddit_mode_channels", [])),
                set(data.get("smash_or_pass_channels", []))
            )
    except (FileNotFoundError, json.JSONDecodeError):
        return set(), set(), set()

def save_data(voicebanned, reddit_mode, smash_pass):
    """Saves data to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        data = {
            "voicebanned_members": list(voicebanned),
            "reddit_mode_channels": list(reddit_mode),
            "smash_or_pass_channels": list(smash_pass)
        }
        json.dump(data, f, indent=4)

voicebanned_members, reddit_mode_channels, smash_or_pass_channels = load_data()

@bot.event
async def on_ready():
    global voicebanned_members, reddit_mode_channels, smash_or_pass_channels
    voicebanned_members, reddit_mode_channels, smash_or_pass_channels = load_data()
    
    os.system('cls' if os.name == 'nt' else 'clear')
    print("")
    print(f"Logged in as: {bot.user}")
    print("=====================================================")
    

    try:
        if TEST_GUILD_ID:
            guild_obj = discord.Object(id=TEST_GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            await bot.tree.sync(guild=guild_obj)
            print(f"Synced commands to guild: {TEST_GUILD_ID}")
        else:
            await bot.tree.sync()
            print("Synced commands globally.")
            
    except Exception as e:
        print(f"Error syncing commands: {e}")
        
    print("=====================================================")
    status = "Listening for /commands"
    await bot.change_presence(activity=discord.Game(name=status))

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            'You do not have permission to use this command.', 
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            'An unexpected error occurred.', 
            ephemeral=True
        )
        print(f"Unhandled error in command '{interaction.command.name}': {error}")




@bot.tree.command(name="voiceban", description="Voiceban a member, preventing them from joining VCs.")
@app_commands.check(is_allowed)
async def voiceban(interaction: discord.Interaction, member: discord.Member):
    voicebanned_members.add(member.id)
    save_data(voicebanned_members, reddit_mode_channels, smash_or_pass_channels)
    
    if member.voice and member.voice.channel:
        await member.edit(voice_channel=None)
        
    await interaction.response.send_message(f"{member.mention} has been voicebanned.", ephemeral=True)

@bot.tree.command(name="unvoiceban", description="Removes a member from the voiceban list.")
@app_commands.check(is_allowed)
async def unvoiceban(interaction: discord.Interaction, member: discord.Member):
    if member.id in voicebanned_members:
        voicebanned_members.remove(member.id)
        save_data(voicebanned_members, reddit_mode_channels, smash_or_pass_channels)
        await interaction.response.send_message(f"{member.mention} has been un-voicebanned.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{member.mention} is not currently voicebanned.", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    """Kicks a voicebanned member if they join a voice channel."""
    if member.id in voicebanned_members and after.channel is not None:
        await member.edit(voice_channel=None)



@bot.tree.command(name="purge", description="Deletes a specified number of messages from the channel.")
@app_commands.describe(amount="The number of messages to delete.")
@app_commands.check(is_allowed)
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1:
        await interaction.response.send_message('Please enter a number greater than 0.', ephemeral=True)
        return
        

    await interaction.response.defer(ephemeral=True)
    
    deleted = await interaction.channel.purge(limit=amount)
    
    await interaction.followup.send(f'Deleted {len(deleted)} messages.')

@bot.tree.command(name="redditmode", description="Toggles Reddit-style upvote/downvote reactions on messages.")
@app_commands.check(is_allowed)
async def redditmode(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id in reddit_mode_channels:
        reddit_mode_channels.remove(channel_id)
        await interaction.response.send_message('Reddit mode is now **off** for this channel.')
    else:
        reddit_mode_channels.add(channel_id)
        await interaction.response.send_message('Reddit mode is now **on** for this channel.')
    save_data(voicebanned_members, reddit_mode_channels, smash_or_pass_channels)

@bot.tree.command(name="smashorpass", description="Toggles Smash or Pass reactions on images.")
@app_commands.check(is_allowed)
async def smashorpass(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id in smash_or_pass_channels:
        smash_or_pass_channels.remove(channel_id)
        await interaction.response.send_message('Smash or Pass mode is now **off** for this channel.')
    else:
        smash_or_pass_channels.add(channel_id)
        await interaction.response.send_message('Smash or Pass mode is now **on** for this channel.')
    save_data(voicebanned_members, reddit_mode_channels, smash_or_pass_channels)



@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id in reddit_mode_channels:
        await message.add_reaction('⬆️')
        await message.add_reaction('⬇️')

    if message.channel.id in smash_or_pass_channels and message.attachments:
        await message.add_reaction('💥')
        await message.add_reaction('🚫')



@bot.tree.command(name="help", description="Shows the list of available commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Help", description="List of available slash commands:", color=discord.Color.blue())
    embed.add_field(name="/voiceban <member>", value="Voiceban a member.", inline=False)
    embed.add_field(name="/unvoiceban <member>", value="Unvoiceban a member.", inline=False)
    embed.add_field(name="/redditmode", value="Toggle Reddit mode on or off for the current channel.", inline=False)
    embed.add_field(name="/smashorpass", value="Toggle Smash or Pass mode on or off for the current channel.", inline=False)
    embed.add_field(name="/purge <amount>", value="Purge a certain number of messages from the channel.", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(DevyBot)