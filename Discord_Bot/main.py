import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import random

# --- Configuration & Environment ---

DATA_FILE = "bot_data.json"
NAMES_FILE = "names.json"
SIEGE_FILE = "siege_data.json"

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TEST_GUILD_ID = None

# --- Application State ---

spam_move_tasks = {}

voicebanned_members = set()
reddit_mode_channels = set()
smash_or_pass_channels = set()
bot_admins = set()
muted_members = set()

disabled_name_enforcements = set() 
enabled_name_enforcements = set()  
enforced_names = {}                
name_enforced_guilds = set()
name_enforcement_on = False        

# Externalized Payload Data (Loaded via JSON)
attack_strats = []
defense_strats = []
general_strats = []
attack_ops = []
defense_ops = []

# --- Data Persistence Handlers ---

def load_data():
    """Initializes sets from persistent bot state file."""
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
                set(data.get("name_enforced_guilds", [])) 
            )
    except (FileNotFoundError, json.JSONDecodeError):
        return set(), set(), set(), set(), set(), set(), set(), set()

def save_data():
    """Serializes active sets to bot state file."""
    with open(DATA_FILE, 'w') as f:
        data = {
            "voicebanned_members": list(voicebanned_members),
            "reddit_mode_channels": list(reddit_mode_channels),
            "smash_or_pass_channels": list(smash_or_pass_channels),
            "admins": list(bot_admins),
            "muted_members": list(muted_members),
            "disabled_name_enforcements": list(disabled_name_enforcements),
            "enabled_name_enforcements": list(enabled_name_enforcements),
            "name_enforced_guilds": list(name_enforced_guilds) 
        }
        json.dump(data, f, indent=4)

def load_names():
    """Initializes enforced nickname registry."""
    try:
        with open(NAMES_FILE, 'r') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_names():
    """Serializes enforced nickname registry."""
    with open(NAMES_FILE, 'w') as f:
        json.dump(enforced_names, f, indent=4)

def load_siege_data():
    """Populates roulette pools from external configuration."""
    global attack_strats, defense_strats, general_strats, attack_ops, defense_ops
    try:
        with open(SIEGE_FILE, 'r') as f:
            data = json.load(f)
            attack_strats = data.get("attack_strats", [])
            defense_strats = data.get("defense_strats", [])
            general_strats = data.get("general_strats", [])
            attack_ops = data.get("attack_ops", [])
            defense_ops = data.get("defense_ops", [])
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: {SIEGE_FILE} missing or corrupted. Pools initialized empty.")
        attack_strats, defense_strats, general_strats = [], [], []
        attack_ops, defense_ops = [], []

def is_allowed(interaction: discord.Interaction) -> bool:
    """Authorization check for restricted administrative commands."""
    dev_id = 445681610965123082 
    if interaction.user.id == dev_id: return True
    if interaction.guild and interaction.user.id == interaction.guild.owner_id: return True
    if interaction.user.id in bot_admins: return True
    return False

# --- Asynchronous Tasks ---

async def move_spam_loop(member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
    """Executes continuous voice channel oscillation for a targeted member."""
    current_channel = channel1 
    while True:
        try:
            target_channel = channel2 if current_channel.id == channel1.id else channel1
            current_channel = target_channel
            await member.edit(voice_channel=target_channel, reason="Automated move routine.")
            await asyncio.sleep(2) 
        except asyncio.CancelledError:
            raise
        except discord.NotFound:
            break 
        except Exception as e:
            print(f"Spam Loop Exception: {e}")
            await asyncio.sleep(5)

@tasks.loop(seconds=10)
async def enforce_nicknames_loop():
    """Polls target guilds to ensure enforced nicknames remain consistent."""
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

# --- Event Listeners ---

@bot.event
async def on_ready():
    global voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins, muted_members, enforced_names, disabled_name_enforcements, enabled_name_enforcements, name_enforced_guilds
    
    voicebanned_members, reddit_mode_channels, smash_or_pass_channels, bot_admins, muted_members, disabled_name_enforcements, enabled_name_enforcements, name_enforced_guilds = load_data()
    enforced_names = load_names()
    load_siege_data()
    
    if not enforce_nicknames_loop.is_running():
        enforce_nicknames_loop.start()

    os.system('cls' if os.name == 'nt' else 'clear')
    print("=====================================================")
    print(f"Client Authenticated: {bot.user}")
    print(f"Loaded Admins: {len(bot_admins)}")
    print(f"Loaded Enforced Names: {len(enforced_names)}")
    print("=====================================================")
    
    try:
        if TEST_GUILD_ID:
            guild_obj = discord.Object(id=TEST_GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            await bot.tree.sync(guild=guild_obj)
        else:
            await bot.tree.sync()
    except Exception as e:
        print(f"Command Tree Sync Exception: {e}")
        
    await bot.change_presence(activity=discord.Game(name="/help"))

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message('Authorization failed.', ephemeral=True)
    elif isinstance(error, app_commands.TransformerError):
         await interaction.response.send_message('Invalid parameter type.', ephemeral=True)
    else:
        await interaction.response.send_message('An unhandled exception occurred.', ephemeral=True)
        print(f"Unhandled app command error: {error}")

@bot.event
async def on_member_update(before, after):
    """Triggers immediate reversion if a user manually circumvents name enforcement."""
    if after.guild.id not in name_enforced_guilds: return
    if after.id in disabled_name_enforcements: return
    
    should_enforce = name_enforcement_on or (after.id in enabled_name_enforcements)
    if not should_enforce: return
    
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
                await member.edit(mute=True)
            except discord.Forbidden: 
                pass
                
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
                await message.add_reaction('\U0001F4A5') 
                await message.add_reaction('\U0001F6AB') 
            except discord.HTTPException: 
                pass
                
    await bot.process_commands(message) 

# --- Name Enforcement Controllers ---

name_group = app_commands.Group(name="name", description="Manage profile enforcement policies.")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@name_group.command(name="change", description="Registers a persistent nickname payload.")
@app_commands.check(is_allowed)
async def name_change(interaction: discord.Interaction, member: discord.Member, name: str):
    enforced_names[member.id] = name
    save_names() 
    
    if member.id in disabled_name_enforcements:
        disabled_name_enforcements.remove(member.id)
        save_data()

    try:
        await member.edit(nick=name)
        await interaction.response.send_message(f"✅ Executed: Payload **{name}** assigned to {member.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Saved to registry, but inadequate permissions to push update.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@name_group.command(name="toggle", description="Modifies enforcement state flags.")
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
            await interaction.response.send_message("Target not found in registry.", ephemeral=True)
            return

        if state == "reset":
            enabled_name_enforcements.discard(member.id)
            disabled_name_enforcements.discard(member.id)
            save_data()
            await interaction.response.send_message(f"♻️ Reverted state flags for {member.mention}.", ephemeral=True)

        elif state == "on":
            enabled_name_enforcements.add(member.id)
            disabled_name_enforcements.discard(member.id)
            save_data()
            await interaction.response.send_message(f"🟢 State [Enabled] forced for {member.mention}.", ephemeral=True)
        
        elif state == "off":
            disabled_name_enforcements.add(member.id)
            enabled_name_enforcements.discard(member.id)
            save_data()
            await interaction.response.send_message(f"🔴 State [Disabled] forced for {member.mention}.", ephemeral=True)
            
    else:
        if state == "reset":
             await interaction.response.send_message("Invalid operation. Global flag cannot be reset.", ephemeral=True)
        elif state == "on":
            name_enforcement_on = True
            await interaction.response.send_message("🟢 Global enforcement flag: TRUE.", ephemeral=True)
        elif state == "off":
            name_enforcement_on = False
            await interaction.response.send_message("🔴 Global enforcement flag: FALSE.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@name_group.command(name="server", description="Modifies server-level enforcement permissions.")
@app_commands.choices(state=[
    app_commands.Choice(name="On (Allow)", value="on"),
    app_commands.Choice(name="Off (Block)", value="off")
])
@app_commands.check(is_allowed)
async def name_server(interaction: discord.Interaction, state: str):
    if state == "on":
        name_enforced_guilds.add(interaction.guild_id)
        save_data()
        await interaction.response.send_message("🟢 Guild added to enforcement pool.", ephemeral=True)
    else:
        name_enforced_guilds.discard(interaction.guild_id)
        save_data()
        await interaction.response.send_message("🔴 Guild removed from enforcement pool.", ephemeral=True)

bot.tree.add_command(name_group)

# --- Administrative Endpoints ---

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="addadmin", description="Grants administrative clearance to a user ID.")
@app_commands.check(is_allowed)
async def addadmin(interaction: discord.Interaction, user: discord.User):
    bot_admins.add(user.id)
    save_data()
    await interaction.response.send_message(f"✅ Authorization granted: {user.name}", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="removeadmin", description="Revokes administrative clearance from a user ID.")
@app_commands.check(is_allowed)
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    bot_admins.discard(user.id)
    save_data()
    await interaction.response.send_message(f"🗑️ Authorization revoked: {user.name}", ephemeral=True)

# --- Moderation Toolkit ---

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="mute", description="Enforces global silence (Chat & Voice).")
@app_commands.check(is_allowed)
async def mute(interaction: discord.Interaction, member: discord.Member):
    muted_members.add(member.id)
    save_data()
    if member.voice:
        try: await member.edit(mute=True)
        except discord.Forbidden: pass
    await interaction.response.send_message(f"🤐 Silence protocol active: {member.mention}", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="unmute", description="Revokes global silence restriction.")
@app_commands.check(is_allowed)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    muted_members.discard(member.id)
    save_data()
    if member.voice:
        try: await member.edit(mute=False)
        except discord.Forbidden: pass
    await interaction.response.send_message(f"🗣️ Silence protocol terminated: {member.mention}", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="move_spam", description="Initiates voice channel oscillation.")
@app_commands.check(is_allowed)
async def move_spam(interaction: discord.Interaction, member: discord.Member, channel1: discord.VoiceChannel, channel2: discord.VoiceChannel):
    if member.id == interaction.user.id or member.id in spam_move_tasks or not (member.voice and member.voice.channel):
        await interaction.response.send_message("Invalid parameters or state.", ephemeral=True)
        return
    spam_move_tasks[member.id] = asyncio.create_task(move_spam_loop(member, channel1, channel2))
    await interaction.response.send_message(f"Oscillation routine initiated on {member.name}.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="unmove", description="Terminates voice channel oscillation.")
@app_commands.check(is_allowed)
async def unmove(interaction: discord.Interaction, member: discord.Member):
    if member.id in spam_move_tasks:
        spam_move_tasks.pop(member.id).cancel()
        await interaction.response.send_message("Oscillation routine terminated.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="voiceban", description="Revokes voice channel connection privileges.")
@app_commands.check(is_allowed)
async def voiceban(interaction: discord.Interaction, member: discord.Member):
    voicebanned_members.add(member.id)
    save_data()
    if member.voice: await member.edit(voice_channel=None)
    await interaction.response.send_message(f"Voice privileges revoked for {member.name}.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="unvoiceban", description="Restores voice channel connection privileges.")
@app_commands.check(is_allowed)
async def unvoiceban(interaction: discord.Interaction, member: discord.Member):
    voicebanned_members.discard(member.id)
    save_data()
    await interaction.response.send_message(f"Voice privileges restored for {member.name}.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="purge", description="Bulk message deletion protocol.")
@app_commands.check(is_allowed)
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1: return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f'Purged {len(deleted)} messages.', ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="redditmode", description="Toggles automatic upvote/downvote reactions.")
@app_commands.check(is_allowed)
async def redditmode(interaction: discord.Interaction):
    if interaction.channel.id in reddit_mode_channels:
        reddit_mode_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Reddit mode: DISABLED.', ephemeral=True)
    else:
        reddit_mode_channels.add(interaction.channel.id)
        await interaction.response.send_message('Reddit mode: ENABLED.', ephemeral=True)
    save_data()

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@bot.tree.command(name="smashorpass", description="Toggles automatic evaluation reactions.")
@app_commands.check(is_allowed)
async def smashorpass(interaction: discord.Interaction):
    if interaction.channel.id in smash_or_pass_channels:
        smash_or_pass_channels.remove(interaction.channel.id)
        await interaction.response.send_message('Evaluation mode: DISABLED.', ephemeral=True)
    else:
        smash_or_pass_channels.add(interaction.channel.id)
        await interaction.response.send_message('Evaluation mode: ENABLED.', ephemeral=True)
    save_data()

# ==========================================
# --- TOURNAMENT MANAGER CONTROLLERS ---
# ==========================================

class TournamentCleanupView(discord.ui.View):
    """Handles archival operations upon bracket conclusion."""
    def __init__(self, msg_history, host_id):
        super().__init__(timeout=None)
        self.msg_history = msg_history
        self.host_id = host_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Authorization denied: Host privileges required.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🗄️ Keep History", style=discord.ButtonStyle.secondary)
    async def btn_keep(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=None)

    @discord.ui.button(label="🧹 Clear All History", style=discord.ButtonStyle.danger)
    async def btn_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for msg in self.msg_history:
            try:
                await msg.delete()
            except:
                pass
        self.msg_history.clear()

class TournamentView(discord.ui.View):
    """Maintains bracket state and manages progression logic."""
    def __init__(self, teams_list, host_id, round_num=1, msg_history=None):
        super().__init__(timeout=None)
        self.teams = teams_list
        self.host_id = host_id
        self.round_num = round_num
        self.msg_history = msg_history if msg_history is not None else []
        self.winners = []
        self.matches = []
        
        # Segment players based on specified team constraints
        for i in range(0, len(self.teams), 2):
            if i + 1 < len(self.teams):
                self.matches.append([self.teams[i], self.teams[i+1], None])
            else:
                self.winners.append(self.teams[i])

        self.create_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Authorization denied: Host privileges required.", ephemeral=True)
            return False
        return True

    def create_buttons(self):
        """Dynamically reconstructs view components based on current match states."""
        self.clear_items()
        
        for i, match in enumerate(self.matches):
            label = f"Match {i+1}: {match[0]} vs {match[1]}"
            if match[2] is not None:
                label = f"✅ Winner: {match[match[2]]}"
            
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, row=i // 2)
            btn.callback = self.make_callback(i)
            self.add_item(btn)

        if all(m[2] is not None for m in self.matches):
            next_btn = discord.ui.Button(label="🚀 Start Next Round", style=discord.ButtonStyle.success, row=4)
            next_btn.callback = self.next_round_callback
            self.add_item(next_btn)

    def make_callback(self, match_idx):
        """Generates contextual callback functions for dynamically rendered buttons."""
        async def callback(interaction: discord.Interaction):
            match = self.matches[match_idx]
            if match[2] is None: match[2] = 0
            elif match[2] == 0: match[2] = 1
            else: match[2] = 0
            
            self.create_buttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        return callback

    async def next_round_callback(self, interaction: discord.Interaction):
        """Processes bracket advancement and initializes subsequent rounds."""
        current_winners = [m[m[2]] for m in self.matches]
        all_advancing = current_winners + self.winners
        
        if len(all_advancing) < 2:
            final_embed = discord.Embed(
                title="🏆 Tournament Complete!",
                description=f"The grand champion is: **{all_advancing[0]}**\n\nChoose an option below regarding the match history.",
                color=0x00FF00
            )
            final_view = TournamentCleanupView(self.msg_history, self.host_id)
            await interaction.response.send_message(embed=final_embed, view=final_view)
            
            final_msg = await interaction.original_response()
            self.msg_history.append(final_msg)
            return

        next_view = TournamentView(all_advancing, self.host_id, self.round_num + 1, self.msg_history)
        await interaction.response.send_message(embed=next_view.make_embed(), view=next_view)
        
        new_msg = await interaction.original_response()
        self.msg_history.append(new_msg)

    def make_embed(self):
        desc = f"**Current Teams:** {len(self.teams)}\n\n"
        for i, m in enumerate(self.matches):
            winner_text = f" -> 🏆 **{m[m[2]]}**" if m[2] is not None else ""
            desc += f"**Match {i+1}:** {m[0]} vs {m[1]}{winner_text}\n"
        
        byes = [t for t in self.teams if t not in [m[0] for m in self.matches] and t not in [m[1] for m in self.matches]]
        if byes:
            desc += f"\n🛡️ **Byes (Advance Automatically):** {', '.join(byes)}"

        embed = discord.Embed(title=f"🏆 Tournament: Round {self.round_num}", description=desc, color=0xFFD700)
        return embed

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="tournament", description="Initializes an interactive bracket manager.")
@app_commands.describe(players="Comma-separated roster", team_size="Participants per team construct (Integer)")
async def tournament(interaction: discord.Interaction, players: str, team_size: int = 1):
    player_list = [p.strip() for p in players.split(',') if p.strip()]
    if len(player_list) < 2:
        await interaction.response.send_message("Insufficient roster parameters.", ephemeral=True)
        return
        
    random.shuffle(player_list)
    
    teams = []
    for i in range(0, len(player_list), team_size):
        chunk = player_list[i:i + team_size]
        teams.append(" & ".join(chunk))

    history = []
    view = TournamentView(teams, host_id=interaction.user.id, msg_history=history)
    await interaction.response.send_message(embed=view.make_embed(), view=view)
    
    first_msg = await interaction.original_response()
    history.append(first_msg)

# --- Standard Utilities ---

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="roll", description="Standard dice execution (e.g. 1d20+5).")
@app_commands.choices(rule=[
    app_commands.Choice(name="Normal", value="normal"), 
    app_commands.Choice(name="Advantage", value="adv"), 
    app_commands.Choice(name="Disadvantage", value="dis")
])
async def roll(interaction: discord.Interaction, expression: str, rule: app_commands.Choice[str] = None):
    # Administrative Output Injection
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

    # Standard Expression Parsing
    try:
        roll_type = rule.value if rule else "normal"
        expression = expression.lower().strip()
        modifier = 0
        
        if '+' in expression: 
            parts = expression.split('+')
            expression = parts[0]
            modifier = int(parts[1])
        elif '-' in expression: 
            parts = expression.split('-')
            expression = parts[0]
            modifier = -int(parts[1])

        if 'd' not in expression: 
            await interaction.response.send_message("Syntax error. Expected format: XdY", ephemeral=True)
            return
            
        num_dice, die_type = map(int, expression.split('d'))
        
        # Enforce constraints to prevent performance degradation
        if num_dice > 100 or die_type > 1000: 
            await interaction.response.send_message("Threshold exceeded. Reduce dice count.", ephemeral=True)
            return

        def roll_dice(): 
            return [random.randint(1, die_type) for _ in range(num_dice)]

        rolls1 = roll_dice()
        total1 = sum(rolls1) + modifier
        
        embed = discord.Embed(color=discord.Color.green())
        
        if roll_type == "normal":
            embed.title = "🎲 Dice Roll"
            embed.add_field(name="Result", value=f"**{total1}**")
            embed.set_footer(text=f"Rolls: {rolls1}")
        else:
            rolls2 = roll_dice()
            total2 = sum(rolls2) + modifier
            final = max(total1, total2) if roll_type == "adv" else min(total1, total2)
            
            embed.title = f"🎲 Roll ({'Advantage' if roll_type=='adv' else 'Disadvantage'})"
            embed.add_field(name="Final", value=f"**{final}**")
            embed.add_field(name="Roll 1", value=f"{total1} {rolls1}", inline=True)
            embed.add_field(name="Roll 2", value=f"{total2} {rolls2}", inline=True)
            
        await interaction.response.send_message(embed=embed)
        
    except ValueError: 
        await interaction.response.send_message("Syntax error during evaluation.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="userinfo", description="Fetches metadata for targeted object.")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    
    if isinstance(target, discord.Member):
        roles = [role.mention for role in target.roles if role.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "None"
    else:
        roles_str = "N/A - Out of Guild Context"
        
    embed = discord.Embed(title=f"Metadata: {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🆔 Object ID", value=target.id, inline=False)
    
    created_ts = int(target.created_at.timestamp())
    embed.add_field(name="📅 Creation Log", value=f"<t:{created_ts}:D> (<t:{created_ts}:R>)", inline=True)
    
    if hasattr(target, "joined_at") and target.joined_at:
        joined_ts = int(target.joined_at.timestamp())
        embed.add_field(name="📥 Guild Entry", value=f"<t:{joined_ts}:D> (<t:{joined_ts}:R>)", inline=True)
    else:
        embed.add_field(name="📥 Guild Entry", value="Unknown", inline=True)

    embed.add_field(name="🎭 Role Array", value=roles_str, inline=False)
    embed.set_image(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="choose", description="Executes random selection from array.")
async def choose(interaction: discord.Interaction, choices: str):
    options = [x.strip() for x in choices.split(',')]
    if len(options) < 2: 
        await interaction.response.send_message("Insufficient options. Minimum 2 required.", ephemeral=True)
        return
    await interaction.response.send_message(embed=discord.Embed(title="Evaluation Output:", description=f"**{random.choice(options)}**", color=discord.Color.blurple()))

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="coin", description="Executes binary evaluation (Heads/Tails).")
async def coin(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="🪙 Binary Evaluation", description=f"Result: **{random.choice(['Heads', 'Tails'])}**", color=discord.Color.gold()))

# ==========================================
# --- TACTICAL ROULETTE DASHBOARD ---
# ==========================================

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="teams", description="Splits a roster into a specific number of teams.")
@app_commands.describe(players="Comma-separated roster", team_count="Number of teams to create (Defaults to 2)")
async def teams(interaction: discord.Interaction, players: str, team_count: int = 2):
    player_list = [p.strip() for p in players.split(',') if p.strip()]
    if len(player_list) < 2:
        await interaction.response.send_message("Insufficient roster parameters.", ephemeral=True)
        return
        
    random.shuffle(player_list)
    
    # Failsafes for invalid numbers
    if team_count < 2: team_count = 2
    if team_count > len(player_list): team_count = len(player_list)
        
    teams = [[] for _ in range(team_count)]
    
    # Round-robin distribution
    for i, player in enumerate(player_list):
        teams[i % team_count].append(player)
        
    embed = discord.Embed(title="⚔️ Team Splitter", color=discord.Color.blurple())
    
    for i in range(team_count):
        players_str = "\n".join(f"• {p}" for p in teams[i])
        embed.add_field(name=f"Team {i+1}", value=players_str, inline=True)
        
    await interaction.response.send_message(embed=embed)


class OpCountModal(discord.ui.Modal):
    """Modal interface for dynamic operator generation."""
    def __init__(self, side: str, dashboard_view: discord.ui.View):
        super().__init__(title=f"{side.capitalize()} Request")
        self.side = side
        self.dashboard_view = dashboard_view 
        
        self.count_input = discord.ui.TextInput(
            label="Integer limit (1-5)",
            style=discord.TextStyle.short,
            placeholder="3",
            required=True,
            min_length=1,
            max_length=1
        )
        self.add_item(self.count_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.count_input.value)
            if count < 1: count = 1
            if count > 5: count = 5
        except ValueError:
            await interaction.response.send_message("Validation Error: Expected Integer.", ephemeral=True)
            return

        if self.side == "attack":
            pool = attack_ops
            color = 0x1A5276
            title = f"⚔️ Operators Generated ({count})"
        else:
            pool = defense_ops
            color = 0xE67E22
            title = f"🛡️ Operators Generated ({count})"

        if not pool:
            await interaction.response.send_message("Data Error: Relevant arrays not populated. Check config.", ephemeral=True)
            return

        chosen_ops = random.sample(pool, count)
        ops_text = "\n".join([f"**{i+1}.** {op}" for i, op in enumerate(chosen_ops)])
        
        embed = discord.Embed(title=title, description=ops_text, color=color)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.dashboard_view.spawned_messages.append(msg)

class SiegeRouletteView(discord.ui.View):
    """Persistent interface for tactical evaluation and generation."""
    def __init__(self):
        super().__init__(timeout=None)
        self.last_attack_strat = None
        self.last_defense_strat = None
        self.last_chaotic_strat = None
        self.spawned_messages = [] 

    # --- ROW 0: STRATEGY GENERATION ---

    @discord.ui.button(label="Attack Strat", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def btn_attack_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not attack_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in attack_strats if s != self.last_attack_strat]
        if not pool: pool = attack_strats
            
        strat = random.choice(pool)
        self.last_attack_strat = strat
        
        embed = discord.Embed(title="⚔️ Attack Strat", description=strat, color=0x1A5276)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.spawned_messages.append(msg)

    @discord.ui.button(label="Defense Strat", style=discord.ButtonStyle.danger, emoji="🛡️", row=0)
    async def btn_defense_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not defense_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in defense_strats if s != self.last_defense_strat]
        if not pool: pool = defense_strats
            
        strat = random.choice(pool)
        self.last_defense_strat = strat
        
        embed = discord.Embed(title="🛡️ Defense Strat", description=strat, color=0xE67E22)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.spawned_messages.append(msg)

    @discord.ui.button(label="Chaotic Strat", style=discord.ButtonStyle.secondary, emoji="🎲", row=0)
    async def btn_chaotic_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        full_pool = attack_strats + defense_strats + general_strats
        if not full_pool:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in full_pool if s != self.last_chaotic_strat]
        if not pool: pool = full_pool
            
        strat = random.choice(pool)
        self.last_chaotic_strat = strat
        
        embed = discord.Embed(title="🎲 Chaotic Strat", description=strat, color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.spawned_messages.append(msg)

    # --- ROW 1: OPERATOR GENERATION ---

    @discord.ui.button(label="Random Attack Ops", style=discord.ButtonStyle.primary, emoji="👥", row=1)
    async def btn_attack_ops(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OpCountModal(side="attack", dashboard_view=self))

    @discord.ui.button(label="Random Defense Ops", style=discord.ButtonStyle.danger, emoji="👥", row=1)
    async def btn_defense_ops(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OpCountModal(side="defense", dashboard_view=self))

    # --- ROW 2: MAINTENANCE ---
    
    @discord.ui.button(label="Clear Spam", style=discord.ButtonStyle.secondary, emoji="🧹", row=2)
    async def btn_clear_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        for msg in self.spawned_messages:
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
                
        self.spawned_messages.clear()

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="siegeroulette", description="Initializes tactical dashboard interface.")
async def siegeroulette(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎯 Tactical Generation Interface",
        description=(
            "**Dashboard Initialized.**\n"
            "Select parameters below to execute generation routines.\n\n"
            "This interface remains persistent for rapid execution."
        ),
        color=0x202225
    )
    await interaction.response.send_message(embed=embed, view=SiegeRouletteView())

# --- Help Endpoints ---

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="help", description="Returns documented command array.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Registered Commands", color=discord.Color.blue())
    embed.add_field(name="👑 Authorization Required", value="`/addadmin`, `/removeadmin` `/purge`", inline=False)
    embed.add_field(name="🏷️ Data Management", value="`/name change`, `/name toggle`, `/name server`", inline=False)
    embed.add_field(name="⚙️ Environment Hooks", value="`/redditmode`, `/smashorpass`", inline=False)
    embed.add_field(name="👻 Disruption", value="`/move_spam`, `/unmove`, `/voiceban`, `/unvoiceban`, `/mute`, `/unmute`", inline=False)
    embed.add_field(name="🎲 Evaluators", value="`/roll`, `/choose`, `/coin`, `/userinfo`, `/tournament`, `/siegeroulette`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(DISCORD_TOKEN)