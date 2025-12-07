import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from datetime import datetime

# --- Constants and Setup ---

DATA_FILE = "bot_data.json"

# Load Token
with open("token.token", 'r') as f:
    DevyBot = f.read().strip()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- IMPORTANT: For testing, add your server's ID here ---
# This makes commands update instantly in your server.
# For global commands, remove the guild=... part from the sync call below.

TEST_GUILD_ID = None

spam_move_tasks = {}

# --- Global Data Variables ---
voicebanned_members = set()
reddit_mode_channels = set()
smash_or_pass_channels = set()
bot_admins = set()

# --- Utility Functions ---

def load_data():
    """Loads data from the JSON file."""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return (
                set(data.get("voicebanned_members", [])),
                set(data.get("reddit_mode_channels", [])),
                set(data.get("smash_or_pass_channels", [])),
                set(data.get("admins", [])) 
            )
    except (FileNotFoundError, json.JSONDecodeError):
        print("Data file not found or corrupted. Creating new data sets.")
        return set(), set(), set(), set()

def save_data():
    """Saves global data variables to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        data = {
            "voicebanned_members": list(voicebanned_members),
            "reddit_mode_channels": list(reddit_mode_channels),
            "smash_or_pass_channels": list(smash_or_pass_channels),
            "admins": list(bot_admins)
        }
        json.dump(data, f, indent=4)

def is_allowed(interaction: discord.Interaction) -> bool:
    """Checks if the user is allowed (Owner, Hardcoded Dev, or in Admin List)."""
    dev_id = 445681610965123082 
    if interaction.user.id == dev_id:
        return True

    if interaction.guild and interaction.user.id == interaction.guild.owner_id:
        return True
        
    if interaction.user.id in bot_admins:
        return True
        
    return False

# --- Admin Management Commands ---

@bot.tree.command(name="addadmin", description="Allows a user to use restricted bot commands.")
@app_commands.describe(user="The user to promote to bot admin.")
@app_commands.check(is_allowed)
async def addadmin(interaction: discord.Interaction, user: discord.User):
    if user.id in bot_admins:
        await interaction.response.send_message(f"{user.mention} is already a bot admin.", ephemeral=True)
        return
    
    bot_admins.add(user.id)
    save_data()
    await interaction.response.send_message(f"✅ {user.mention} has been added to the bot admins list.")

@bot.tree.command(name="removeadmin", description="Removes a user from bot admins.")
@app_commands.describe(user="The user to demote.")
@app_commands.check(is_allowed)
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    if user.id not in bot_admins:
        await interaction.response.send_message(f"{user.mention} is not a bot admin.", ephemeral=True)
        return
        
    bot_admins.remove(user.id)
    save_data()
    await interaction.response.send_message(f"🗑️ {user.mention} has been removed from the bot admins list.")

# --- Async Loop for Move Spam ---

async def move_spam_loop(member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
    current_channel = channel1 
    while True:
        try:
            target_channel = channel2 if current_channel.id == channel1.id else channel1
            current_channel = target_channel
            
            await member.edit(voice_channel=target_channel, reason="Voice channel spam requested by admin.")
            await asyncio.sleep(2) 
            
        except asyncio.CancelledError:
            raise
        except discord.NotFound:
            break 
        except Exception as e:
            print(f"Error during move_spam_loop: {e}")
            await asyncio.sleep(5)

# --- Events ---

@bot.event
async def on_ready():
    global voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins
    
    voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins = load_data()
    
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=====================================================")
    print(f"Logged in as: {bot.user}")
    print(f"Loaded {len(bot_admins)} admins from file.")
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
        
    await bot.change_presence(activity=discord.Game(name="Listening for /commands"))

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message('You do not have permission to use this command.', ephemeral=True)
    elif isinstance(error, app_commands.TransformerError):
         await interaction.response.send_message('Invalid input provided.', ephemeral=True)
    else:
        await interaction.response.send_message('An unexpected error occurred.', ephemeral=True)
        print(f"Unhandled error: {error}")

@bot.event
async def on_voice_state_update(member, before, after):
    
    if member.id in voicebanned_members and after.channel is not None:
        await member.edit(voice_channel=None)
        
    if after.channel is None and member.id in spam_move_tasks:
        task = spam_move_tasks.pop(member.id)
        task.cancel()

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
    
    await bot.process_commands(message) 

# --- Restricted Commands ---

@bot.tree.command(name="move_spam", description="Spam moves a user between two voice channels.")
@app_commands.check(is_allowed)
async def move_spam(interaction: discord.Interaction, member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
    if member.id == interaction.user.id:
        await interaction.response.send_message("You can't move-spam yourself!", ephemeral=True)
        return
    if member.id in spam_move_tasks:
        await interaction.response.send_message(f"{member.mention} is already being spammed.", ephemeral=True)
        return
    if channel1.id == channel2.id:
        await interaction.response.send_message("Channels must be different.", ephemeral=True)
        return

    if not (member.voice and member.voice.channel):
         await interaction.response.send_message(f"{member.mention} is not in a voice channel.", ephemeral=True)
         return

    loop_task = asyncio.create_task(move_spam_loop(member, channel1, channel2))
    spam_move_tasks[member.id] = loop_task
    await interaction.response.send_message(f"**Started move spam** on {member.mention}.", ephemeral=False)

@bot.tree.command(name="unmove", description="Stops the voice channel spamming.")
@app_commands.check(is_allowed)
async def unmove(interaction: discord.Interaction, member: discord.Member):
    if member.id not in spam_move_tasks:
        await interaction.response.send_message(f"{member.mention} is not being spammed.", ephemeral=True)
        return
    task = spam_move_tasks.pop(member.id)
    task.cancel()
    await interaction.response.send_message(f"**Stopped move spam** on {member.mention}.", ephemeral=False)

@bot.tree.command(name="voiceban", description="Voiceban a member.")
@app_commands.check(is_allowed)
async def voiceban(interaction: discord.Interaction, member: discord.Member):
    voicebanned_members.add(member.id)
    save_data()
    if member.voice: await member.edit(voice_channel=None)
    await interaction.response.send_message(f"{member.mention} has been voicebanned.", ephemeral=True)

@bot.tree.command(name="unvoiceban", description="Un-voiceban a member.")
@app_commands.check(is_allowed)
async def unvoiceban(interaction: discord.Interaction, member: discord.Member):
    if member.id in voicebanned_members:
        voicebanned_members.remove(member.id)
        save_data()
        await interaction.response.send_message(f"{member.mention} has been un-voicebanned.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{member.mention} is not voicebanned.", ephemeral=True)

@bot.tree.command(name="purge", description="Deletes messages.")
@app_commands.check(is_allowed)
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1: return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f'Deleted {len(deleted)} messages.')

@bot.tree.command(name="redditmode", description="Toggles Reddit upvote/downvote.")
@app_commands.check(is_allowed)
async def redditmode(interaction: discord.Interaction):
    if interaction.channel.id in reddit_mode_channels:
        reddit_mode_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Reddit mode **OFF**.')
    else:
        reddit_mode_channels.add(interaction.channel.id)
        await interaction.response.send_message('Reddit mode **ON**.')
    save_data()

@bot.tree.command(name="smashorpass", description="Toggles Smash or Pass reactions.")
@app_commands.check(is_allowed)
async def smashorpass(interaction: discord.Interaction):
    if interaction.channel.id in smash_or_pass_channels:
        smash_or_pass_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Smash or Pass **OFF**.')
    else:
        smash_or_pass_channels.add(interaction.channel.id)
        await interaction.response.send_message('Smash or Pass **ON**.')
    save_data()

# --- Fun/Social Commands ---

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="roll", description="Rolls dice (e.g. 1d20+5).")
@app_commands.choices(rule=[app_commands.Choice(name="Normal", value="normal"), app_commands.Choice(name="Advantage", value="adv"), app_commands.Choice(name="Disadvantage", value="dis")])
async def roll(interaction: discord.Interaction, expression: str, rule: app_commands.Choice[str] = None):
    # ... (Keep the rest of your roll logic exactly the same) ...
    try:
        roll_type = rule.value if rule else "normal"
        # ... existing logic ...
        # (I am hiding the logic here to save space, but keep your existing code inside)
        expression = expression.lower().strip()
        modifier = 0
        
        if '+' in expression: parts = expression.split('+'); expression = parts[0]; modifier = int(parts[1])
        elif '-' in expression: parts = expression.split('-'); expression = parts[0]; modifier = -int(parts[1])

        if 'd' not in expression: await interaction.response.send_message("Use format XdY (e.g. 1d20).", ephemeral=True); return
        num_dice, die_type = map(int, expression.split('d'))
        
        if num_dice > 100 or die_type > 1000: await interaction.response.send_message("Too many dice.", ephemeral=True); return

        def roll_dice(): return [random.randint(1, die_type) for _ in range(num_dice)]
        rolls1 = roll_dice(); total1 = sum(rolls1) + modifier
        
        embed = discord.Embed(color=discord.Color.green())
        if roll_type == "normal":
            embed.title = "🎲 Dice Roll"; embed.add_field(name="Result", value=f"**{total1}**")
            embed.set_footer(text=f"Rolls: {rolls1}")
        else:
            rolls2 = roll_dice(); total2 = sum(rolls2) + modifier
            final = max(total1, total2) if roll_type == "adv" else min(total1, total2)
            embed.title = f"🎲 Roll ({'Advantage' if roll_type=='adv' else 'Disadvantage'})"
            embed.add_field(name="Final", value=f"**{final}**")
            embed.add_field(name="Roll 1", value=f"{total1} {rolls1}", inline=True)
            embed.add_field(name="Roll 2", value=f"{total2} {rolls2}", inline=True)
            
        await interaction.response.send_message(embed=embed)
    except ValueError: await interaction.response.send_message("Invalid format.", ephemeral=True)




@bot.tree.command(name="userinfo", description="Get stats, dates, and avatar for a user.")
@app_commands.describe(member="The user to view (defaults to you).")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    

    roles = [role.mention for role in target.roles if role.name != "@everyone"]
    if not roles:
        roles_str = "None"
    else:
        roles_str = ", ".join(roles)
        
    embed = discord.Embed(title=f"User Info: {target.display_name}", color=target.color)

    embed.set_thumbnail(url=target.display_avatar.url)
    

    embed.add_field(name="🆔 User ID", value=target.id, inline=False)
    
    created_ts = int(target.created_at.timestamp())
    embed.add_field(name="📅 Created Account", value=f"<t:{created_ts}:D> (<t:{created_ts}:R>)", inline=True)
    
    if target.joined_at:
        joined_ts = int(target.joined_at.timestamp())
        embed.add_field(name="📥 Joined Server", value=f"<t:{joined_ts}:D> (<t:{joined_ts}:R>)", inline=True)
    else:
        embed.add_field(name="📥 Joined Server", value="Unknown", inline=True)

    embed.add_field(name=f"🎭 Roles ({len(roles)})", value=roles_str, inline=False)
    
    embed.set_image(url=target.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="choose", description="Picks a random item.")
async def choose(interaction: discord.Interaction, choices: str):
    options = [x.strip() for x in choices.split(',')]
    if len(options) < 2: await interaction.response.send_message("Need at least 2 choices.", ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title="Decided:", description=f"**{random.choice(options)}**", color=discord.Color.blurple()))

@bot.tree.command(name="coin", description="Flips a coin.")
async def coin(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="🪙 Coin Flip", description=f"Result: **{random.choice(['Heads', 'Tails'])}**", color=discord.Color.gold()))





@bot.tree.command(name="help", description="Shows commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="DevyBot Commands", color=discord.Color.blue())
    embed.add_field(name="👑 Admin", value="`/addadmin`, `/removeadmin` `/purge`", inline=False)
    embed.add_field(name="⚙️ Channel", value="`/redditmode`, `/smashorpass`, ", inline=False)
    embed.add_field(name="👻 Chaos", value="`/move_spam`, `/unmove`, `/voiceban`, `/unvoiceban`", inline=False)
    embed.add_field(name="🎲 Fun", value="`/roll`, `/choose`, `/coin`, `/userinfo`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(DevyBot)