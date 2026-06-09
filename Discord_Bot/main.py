import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

# --- Configuration & Environment ---

DATA_FILE = "bot_data.json"
NAMES_FILE = "names.json"
SIEGE_FILE = "siege_data.json"

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

try:
    DEV_ID = int(os.getenv('DEV_ID', 445681610965123082))
except ValueError:
    DEV_ID = 445681610965123082

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- Application State ---
        self.spam_move_tasks = {}
        
        self.voicebanned_members = set()
        self.reddit_mode_channels = set()
        self.smash_or_pass_channels = set()
        self.bot_admins = set()
        self.muted_members = set()
        
        self.disabled_name_enforcements = set() 
        self.enabled_name_enforcements = set()  
        self.enforced_names = {}                
        self.name_enforced_guilds = set()
        self.name_enforcement_on = False        
        
        # Externalized Payload Data (Loaded via JSON)
        self.attack_strats = []
        self.defense_strats = []
        self.general_strats = []
        self.attack_ops = []
        self.defense_ops = []
        
        self.dev_id = DEV_ID

    async def setup_hook(self):
        # Load persistence data
        await self.load_data()
        await self.load_names()
        await self.load_siege_data()
        
        # Load extensions (Cogs)
        if not os.path.exists('./cogs'):
            os.makedirs('./cogs')
            
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != 'utils.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Loaded extension: {filename}")
                except Exception as e:
                    print(f"Failed to load extension {filename}: {e}")

    # --- Data Persistence Handlers (Non-Blocking) ---
    async def load_data(self):
        def _load():
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
        
        data = await asyncio.to_thread(_load)
        self.voicebanned_members = set(data.get("voicebanned_members", []))
        self.reddit_mode_channels = set(data.get("reddit_mode_channels", []))
        self.smash_or_pass_channels = set(data.get("smash_or_pass_channels", []))
        self.bot_admins = set(data.get("admins", []))
        self.muted_members = set(data.get("muted_members", []))
        self.disabled_name_enforcements = set(data.get("disabled_name_enforcements", []))
        self.enabled_name_enforcements = set(data.get("enabled_name_enforcements", []))
        self.name_enforced_guilds = set(data.get("name_enforced_guilds", []))

    async def save_data(self):
        def _save():
            data = {
                "voicebanned_members": list(self.voicebanned_members),
                "reddit_mode_channels": list(self.reddit_mode_channels),
                "smash_or_pass_channels": list(self.smash_or_pass_channels),
                "admins": list(self.bot_admins),
                "muted_members": list(self.muted_members),
                "disabled_name_enforcements": list(self.disabled_name_enforcements),
                "enabled_name_enforcements": list(self.enabled_name_enforcements),
                "name_enforced_guilds": list(self.name_enforced_guilds)
            }
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        
        await asyncio.to_thread(_save)

    async def load_names(self):
        def _load():
            try:
                with open(NAMES_FILE, 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()}
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
        
        self.enforced_names = await asyncio.to_thread(_load)

    async def save_names(self):
        def _save():
            with open(NAMES_FILE, 'w') as f:
                json.dump(self.enforced_names, f, indent=4)
        
        await asyncio.to_thread(_save)

    async def load_siege_data(self):
        def _load():
            try:
                with open(SIEGE_FILE, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"Warning: {SIEGE_FILE} missing or corrupted. Pools initialized empty.")
                return {}
                
        data = await asyncio.to_thread(_load)
        self.attack_strats = data.get("attack_strats", [])
        self.defense_strats = data.get("defense_strats", [])
        self.general_strats = data.get("general_strats", [])
        self.attack_ops = data.get("attack_ops", [])
        self.defense_ops = data.get("defense_ops", [])

    def is_allowed(self, interaction: discord.Interaction) -> bool:
        """Authorization check for restricted administrative commands."""
        if interaction.user.id == self.dev_id: return True
        if interaction.guild and interaction.user.id == interaction.guild.owner_id: return True
        if interaction.user.id in self.bot_admins: return True
        return False

intents = discord.Intents.all()
bot = MyBot(command_prefix="!", intents=intents)

# --- Event Listeners ---

@bot.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=====================================================")
    print(f"Client Authenticated: {bot.user}")
    print(f"Loaded Admins: {len(bot.bot_admins)}")
    print(f"Loaded Enforced Names: {len(bot.enforced_names)}")
    print("=====================================================")
    
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

# --- Text Commands ---

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Owner command to sync slash command tree manually."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} global command(s).")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync command tree: {e}")

@bot.command()
async def dev_sync(ctx):
    """Fallback dev-only sync command (if bot.is_owner() check fails)."""
    if ctx.author.id == bot.dev_id:
        try:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} global command(s).")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync: {e}")

# Run the Bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)