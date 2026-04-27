import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import random
from datetime import datetime

# --- Constants and Setup ---

DATA_FILE = "bot_data.json"
NAMES_FILE = "names.json"

# Load Token
load_dotenv()
DevyBot = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TEST_GUILD_ID = None

spam_move_tasks = {}

# --- Global Data Variables ---
voicebanned_members = set()
reddit_mode_channels = set()
smash_or_pass_channels = set()
bot_admins = set()
muted_members = set()

# Name Enforcement Variables
disabled_name_enforcements = set() 
enabled_name_enforcements = set()  
enforced_names = {}                
name_enforced_guilds = set()
name_enforcement_on = False        

# --- Utility Functions ---

def load_data():
    """Loads bot_data.json"""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return (
                set(data.get("voicebanned_members", [])),
                set(data.get("reddit_mode_channels", [])),
                set(data.get("smash_or_pass_channels", [])),
                set(data.get("admins", [])),
                set(data.get("muted_members", [])),
                set(data.get("disabled_name_enforcements", [])),
                set(data.get("enabled_name_enforcements", [])),
                set(data.get("name_enforced_guilds", [])) # <--- NEW
            )
    except (FileNotFoundError, json.JSONDecodeError):
        print("Data file not found or corrupted. Creating new data sets.")
        return set(), set(), set(), set(), set(), set(), set(), set()

def save_data():
    """Saves bot_data.json"""
    with open(DATA_FILE, 'w') as f:
        data = {
            "voicebanned_members": list(voicebanned_members),
            "reddit_mode_channels": list(reddit_mode_channels),
            "smash_or_pass_channels": list(smash_or_pass_channels),
            "admins": list(bot_admins),
            "muted_members": list(muted_members),
            "disabled_name_enforcements": list(disabled_name_enforcements),
            "enabled_name_enforcements": list(enabled_name_enforcements),
            "name_enforced_guilds": list(name_enforced_guilds) # <--- NEW
        }
        json.dump(data, f, indent=4)

def load_names():
    """Loads names.json"""
    try:
        with open(NAMES_FILE, 'r') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        print("Names file not found. Starting empty.")
        return {}

def save_names():
    """Saves names.json"""
    with open(NAMES_FILE, 'w') as f:
        json.dump(enforced_names, f, indent=4)

def is_allowed(interaction: discord.Interaction) -> bool:
    dev_id = 445681610965123082 
    if interaction.user.id == dev_id: return True
    if interaction.guild and interaction.user.id == interaction.guild.owner_id: return True
    if interaction.user.id in bot_admins: return True
    return False

# --- ASYNC LOOPS ---

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

@tasks.loop(seconds=10)
async def enforce_nicknames_loop():
    for guild in bot.guilds:
        if guild.id not in name_enforced_guilds:
            continue

        for user_id, forced_nick in enforced_names.items():
            
            if user_id in disabled_name_enforcements:
                continue

            should_enforce = name_enforcement_on or (user_id in enabled_name_enforcements)

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
                except Exception as e:
                    print(f"Error changing nickname in loop: {e}")

# --- Events ---

@bot.event
async def on_ready():
    global voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins, muted_members, enforced_names, disabled_name_enforcements, enabled_name_enforcements, name_enforced_guilds
    
    # 1. Load basic data
    voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins, muted_members, disabled_name_enforcements, enabled_name_enforcements, name_enforced_guilds = load_data()
    
    # 2. Load names directly from the JSON file
    enforced_names = load_names()
    
    # Start the loop
    if not enforce_nicknames_loop.is_running():
        enforce_nicknames_loop.start()

    os.system('cls' if os.name == 'nt' else 'clear')
    print("=====================================================")
    print(f"Logged in as: {bot.user}")
    print(f"Loaded {len(bot_admins)} admins.")
    print(f"Loaded {len(enforced_names)} enforced names.")
    print(f"Active in {len(name_enforced_guilds)} servers.")
    print(f"Global Name Mode: {name_enforcement_on}")
    print("=====================================================")
    
    try:
        if TEST_GUILD_ID:
            guild_obj = discord.Object(id=TEST_GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            await bot.tree.sync(guild=guild_obj)
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
async def on_member_update(before, after):
    """Instant detection when someone changes their profile."""
    
    if after.guild.id not in name_enforced_guilds:
        return

    if after.id in disabled_name_enforcements:
        return

    should_enforce = name_enforcement_on or (after.id in enabled_name_enforcements)

    if not should_enforce:
        return

    if after.id in enforced_names:
        forced_name = enforced_names[after.id]
        
        if after.display_name != forced_name:
            if after.id == after.guild.owner_id: return
            if after.top_role >= after.guild.me.top_role: return

            try:
                await after.edit(nick=forced_name)
            except discord.Forbidden:
                pass

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in voicebanned_members and after.channel is not None:
        await member.edit(voice_channel=None)
        
    if member.id in muted_members and after.channel is not None:
        if not after.mute:
            try:
                await member.edit(mute=True, reason="User is hard-muted.")
            except discord.Forbidden:
                print(f"Failed to server mute {member.name} (Missing Permissions).")

    if after.channel is None and member.id in spam_move_tasks:
        task = spam_move_tasks.pop(member.id)
        task.cancel()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
        
    if message.author.id in muted_members:
        try:
            await message.delete()
        except discord.Forbidden:
            pass 
        return

    if message.channel.id in reddit_mode_channels:
        await message.add_reaction('⬆️')
        await message.add_reaction('⬇️')
        
    if message.channel.id in smash_or_pass_channels and message.attachments:
            try:
                # Use Unicode ID for 💥 (Collision/Smash)
                await message.add_reaction('\U0001F4A5') 
                # Use Unicode ID for 🚫 (No Entry/Pass)
                await message.add_reaction('\U0001F6AB') 
            except discord.HTTPException:
                pass # Ignores errors if the message was deleted instantly
    
    await bot.process_commands(message) 


name_group = app_commands.Group(name="name", description="Manage enforced nicknames.")

@name_group.command(name="change", description="Sets a permanent nickname for a user.")
@app_commands.describe(member="The member to target", name="The nickname to enforce")
@app_commands.check(is_allowed)
async def name_change(interaction: discord.Interaction, member: discord.Member, name: str):
    enforced_names[member.id] = name
    save_names() 
    
    if member.id in disabled_name_enforcements:
        disabled_name_enforcements.remove(member.id)
        save_data()

    try:
        await member.edit(nick=name)
        await interaction.response.send_message(f"✅ Set {member.mention}'s enforced name to **{name}**.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Saved to list, but I don't have permission to change {member.mention}'s name right now.", ephemeral=True)


@name_group.command(name="toggle", description="Turn sticky nicknames on or off (Globally or for one person).")
@app_commands.describe(state="On, Off, or Reset", member="Optional: Specific member to toggle.")
@app_commands.choices(state=[
    app_commands.Choice(name="On (Force Enable)", value="on"),
    app_commands.Choice(name="Off (Force Disable)", value="off"),
    app_commands.Choice(name="Reset (Default)", value="reset")
])
@app_commands.check(is_allowed)
async def name_toggle(interaction: discord.Interaction, state: str, member: discord.Member = None):
    global name_enforcement_on
    
    if member:
        if member.id not in enforced_names:
            await interaction.response.send_message(f"⚠️ {member.mention} is not in the name list. Use `/name change` first.", ephemeral=True)
            return

        if state == "reset":
            if member.id in enabled_name_enforcements: enabled_name_enforcements.remove(member.id)
            if member.id in disabled_name_enforcements: disabled_name_enforcements.remove(member.id)
            save_data()
            await interaction.response.send_message(f"♻️ **Reset** {member.mention}. They will now follow the Global setting.", ephemeral=True)

        elif state == "on":
            enabled_name_enforcements.add(member.id)
            if member.id in disabled_name_enforcements: disabled_name_enforcements.remove(member.id)
            save_data()
            await interaction.response.send_message(f"🟢 **Force Enabled** name enforcement for {member.mention} (Overrides Global setting).", ephemeral=True)
        
        elif state == "off":
            disabled_name_enforcements.add(member.id)
            if member.id in enabled_name_enforcements: enabled_name_enforcements.remove(member.id)
            save_data()
            await interaction.response.send_message(f"🔴 **Force Disabled** name enforcement for {member.mention} (Overrides Global setting).", ephemeral=True)
            
    else:
        if state == "reset":
             await interaction.response.send_message("⚠️ You cannot 'Reset' the global switch. Please use On or Off.", ephemeral=True)
        elif state == "on":
            name_enforcement_on = True
            await interaction.response.send_message("🟢 **GLOBAL Name Enforcement Enabled.**", ephemeral=True)
        elif state == "off":
            name_enforcement_on = False
            await interaction.response.send_message("🔴 **GLOBAL Name Enforcement Disabled.** (Individual enabled members will still be checked).", ephemeral=True)

@name_group.command(name="server", description="Enable/Disable name enforcement for this specific server.")
@app_commands.describe(state="On to enable in this server, Off to disable.")
@app_commands.choices(state=[
    app_commands.Choice(name="On (Allow)", value="on"),
    app_commands.Choice(name="Off (Block)", value="off")
])
@app_commands.check(is_allowed)
async def name_server(interaction: discord.Interaction, state: str):
    guild_id = interaction.guild_id
    
    if state == "on":
        name_enforced_guilds.add(guild_id)
        save_data()
        await interaction.response.send_message(f"🟢 **Server Enabled.** Sticky nicknames will now work in **{interaction.guild.name}**.", ephemeral=True)
    else:
        if guild_id in name_enforced_guilds:
            name_enforced_guilds.remove(guild_id)
            save_data()
        await interaction.response.send_message(f"🔴 **Server Disabled.** Sticky nicknames are now OFF for **{interaction.guild.name}**.", ephemeral=True)

bot.tree.add_command(name_group)

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
    await interaction.response.send_message(f"✅ {user.mention} has been added to the bot admins list.", ephemeral=True)

@bot.tree.command(name="removeadmin", description="Removes a user from bot admins.")
@app_commands.describe(user="The user to demote.")
@app_commands.check(is_allowed)
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    if user.id not in bot_admins:
        await interaction.response.send_message(f"{user.mention} is not a bot admin.", ephemeral=True)
        return
        
    bot_admins.remove(user.id)
    save_data()
    await interaction.response.send_message(f"🗑️ {user.mention} has been removed from the bot admins list.", ephemeral=True)

# --- Restricted Commands ---

@bot.tree.command(name="mute", description="Completely silences a user (Chat + Voice).")
@app_commands.describe(member="The user to silence.")
@app_commands.check(is_allowed)
async def mute(interaction: discord.Interaction, member: discord.Member):
    if member.id in muted_members:
        await interaction.response.send_message(f"{member.mention} is already muted.", ephemeral=True)
        return

    muted_members.add(member.id)
    save_data()
    
    if member.voice:
        try:
            await member.edit(mute=True, reason="Mute command")
        except discord.Forbidden:
            pass

    await interaction.response.send_message(f"🤐 **{member.mention}** has been silenced (Chat deleted + Voice Muted).", ephemeral=True)

@bot.tree.command(name="unmute", description="Unsilences a user.")
@app_commands.describe(member="The user to release.")
@app_commands.check(is_allowed)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if member.id not in muted_members:
        await interaction.response.send_message(f"{member.mention} is not muted.", ephemeral=True)
        return

    muted_members.remove(member.id)
    save_data()

    if member.voice:
        try:
            await member.edit(mute=False, reason="Unmute command")
        except discord.Forbidden:
            pass
    
    await interaction.response.send_message(f"🗣️ **{member.mention}** has been unmuted.", ephemeral=True)

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
    await interaction.response.send_message(f"**Started move spam** on {member.mention}.", ephemeral=True)

@bot.tree.command(name="unmove", description="Stops the voice channel spamming.")
@app_commands.check(is_allowed)
async def unmove(interaction: discord.Interaction, member: discord.Member):
    if member.id not in spam_move_tasks:
        await interaction.response.send_message(f"{member.mention} is not being spammed.", ephemeral=True)
        return
    task = spam_move_tasks.pop(member.id)
    task.cancel()
    await interaction.response.send_message(f"**Stopped move spam** on {member.mention}.", ephemeral=True)

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
    await interaction.followup.send(f'Deleted {len(deleted)} messages.', ephemeral=True)

@bot.tree.command(name="redditmode", description="Toggles Reddit upvote/downvote.")
@app_commands.check(is_allowed)
async def redditmode(interaction: discord.Interaction):
    if interaction.channel.id in reddit_mode_channels:
        reddit_mode_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Reddit mode **OFF**.', ephemeral=True)
    else:
        reddit_mode_channels.add(interaction.channel.id)
        await interaction.response.send_message('Reddit mode **ON**.', ephemeral=True)
    save_data()

@bot.tree.command(name="smashorpass", description="Toggles Smash or Pass reactions.")
@app_commands.check(is_allowed)
async def smashorpass(interaction: discord.Interaction):
    if interaction.channel.id in smash_or_pass_channels:
        smash_or_pass_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Smash or Pass **OFF**.', ephemeral=True)
    else:
        smash_or_pass_channels.add(interaction.channel.id)
        await interaction.response.send_message('Smash or Pass **ON**.', ephemeral=True)
    save_data()

# --- Fun/Social Commands (These remain public) ---

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="roll", description="Rolls dice (e.g. 1d20+5).")
@app_commands.choices(rule=[app_commands.Choice(name="Normal", value="normal"), app_commands.Choice(name="Advantage", value="adv"), app_commands.Choice(name="Disadvantage", value="dis")])
async def roll(interaction: discord.Interaction, expression: str, rule: app_commands.Choice[str] = None):
    # --- HIDDEN ADMIN OVERRIDE ---
    clean_expr = expression.replace("+", "").replace("-", "")
    
    if clean_expr.isdigit() and is_allowed(interaction):
        try:
            modifier = 0
            if '+' in expression:
                parts = expression.split('+')
                base = int(parts[0])
                modifier = int(parts[1])
                result = base + modifier
            elif '-' in expression:
                parts = expression.split('-')
                base = int(parts[0])
                modifier = -int(parts[1])
                result = base + modifier
            else:
                result = int(expression)

            embed = discord.Embed(title="🎲 Dice Roll", color=discord.Color.green())
            embed.add_field(name="Result", value=f"**{result}**", inline=False)
            embed.set_footer(text=f"Rolls: [{result}]")
            await interaction.response.send_message(embed=embed)
            return
        except ValueError:
            pass 

    # --- STANDARD LOGIC ---
    try:
        roll_type = rule.value if rule else "normal"
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

# --- UPGRADED USERINFO COMMAND ---
@bot.tree.command(name="userinfo", description="Get stats, dates, and avatar for a user.")
@app_commands.describe(member="The user to view (defaults to you).")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    roles = [role.mention for role in target.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "None"
        
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

# --- HIDDEN PREFIX COMMANDS ---
@bot.command(name="roll")
async def fake_roll(ctx, result: int = 20):
    """Hidden roll command. Usage: !roll 20"""
    is_authorized = False
    if ctx.author.id == 445681610965123082: is_authorized = True
    elif ctx.guild and ctx.author.id == ctx.guild.owner_id: is_authorized = True
    elif ctx.author.id in bot_admins: is_authorized = True

    if not is_authorized: return
    try: await ctx.message.delete()
    except discord.Forbidden: pass

    embed = discord.Embed(title="🎲 Dice Roll", color=discord.Color.green())
    embed.add_field(name="Result", value=f"**{result}**", inline=False)
    embed.set_footer(text=f"Rolls: [{result}]")
    await ctx.send(embed=embed)


@bot.command()
async def cleardups(ctx):
    """Run this command once to delete the duplicate commands."""
    # Security check: Only you can run this
    if ctx.author.id != 445681610965123082: 
        return

    msg = await ctx.send("🧹 Clearing old guild-specific commands...")
    
    # This wipes the commands strictly for this specific server
    bot.tree.clear_commands(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    
    await msg.edit(content="✅ **Duplicates Cleared!**\nIf you still see them, fully restart your Discord app (Ctrl+R).")


@bot.tree.command(name="help", description="Shows commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="DevyBot Commands", color=discord.Color.blue())
    embed.add_field(name="👑 Admin", value="`/addadmin`, `/removeadmin` `/purge`", inline=False)
    embed.add_field(name="🏷️ Names", value="`/name change`, `/name toggle`, `/name server`", inline=False)
    embed.add_field(name="⚙️ Channel", value="`/redditmode`, `/smashorpass`", inline=False)
    embed.add_field(name="👻 Chaos", value="`/move_spam`, `/unmove`, `/voiceban`, `/unvoiceban`, `/mute`, `/unmute`", inline=False)
    embed.add_field(name="🎲 Fun", value="`/roll`, `/choose`, `/coin`, `/userinfo`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(DevyBot)