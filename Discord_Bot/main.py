import asyncio
import json
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from db_manager import DatabaseManager

# --- Configuration & Environment ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "bot_data.json")
NAMES_FILE = os.path.join(BASE_DIR, "names.json")
SIEGE_FILE = os.path.join(BASE_DIR, "siege_data.json")

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

try:
    DEV_ID = int(os.getenv('DEV_ID', 445681610965123082))
except ValueError:
    DEV_ID = 445681610965123082

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = DatabaseManager()
        
        # --- Application State ---
        self.spam_move_tasks = {}
        
        self.voicebanned_members = set()
        self.reddit_mode_channels = set()
        self.smash_or_pass_channels = set()
        self.bot_admins = {}
        self.muted_members = set()
        
        self.disabled_name_enforcements = set() 
        self.enabled_name_enforcements = set()  
        self.enforced_names = {}                
        self.name_enforced_guilds = set()
        self.name_enforcement_on = False        
        self.honeypot_channels = {}
        self.honeypot_log_channels = {}
        self.joinshield_settings = {}
        self.blocked_words = {}
        self.mod_log_channels = {}
        self.filter_exempt_roles = {}
        self.filter_exempt_channels = {}
        self.ticket_staff_roles = {}
        self.autoroles = {}
        self.temp_generators = set()
        
        # Externalized Payload Data (Loaded via JSON)
        self.attack_strats = []
        self.defense_strats = []
        self.general_strats = []
        self.attack_ops = []
        self.defense_ops = []
        
        self.dev_id = DEV_ID

    async def setup_hook(self):
        # Initialize SQLite tables
        await self.db.init_db()
        
        # Load persistence data
        await self.load_data()
        await self.load_siege_data()
        
        # Load extensions (Cogs)
        cogs_dir = os.path.join(BASE_DIR, "cogs")
        if not os.path.exists(cogs_dir):
            os.makedirs(cogs_dir)
            
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and filename != 'utils.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Loaded extension: {filename}")
                except Exception as e:
                    print(f"Failed to load extension {filename}: {e}")

        # Register persistent views
        try:
            from cogs.giveaways import GiveawayView
            active_giveaways = await self.db.async_load_active_giveaways()
            for giveaway in active_giveaways:
                giveaway_id = giveaway[0]
                self.add_view(GiveawayView(giveaway_id))
                print(f"Registered persistent GiveawayView for giveaway_id: {giveaway_id}")
        except Exception as e:
            print(f"Failed to register persistent GiveawayViews: {e}")
            
        try:
            from cogs.roles import RoleMenuView
            menus = await self.db.async_load_all_role_menus()
            for menu in menus:
                options = menu["options"]
                self.add_view(RoleMenuView(options))
                print(f"Registered persistent RoleMenuView for message_id: {menu['message_id']}")
        except Exception as e:
            print(f"Failed to register persistent RoleMenuViews: {e}")
            
        try:
            from cogs.tickets import TicketWelcomeView
            self.add_view(TicketWelcomeView())
            print("Registered persistent TicketWelcomeView")
        except Exception as e:
            print(f"Failed to register persistent TicketWelcomeView: {e}")

        try:
            from cogs.siegeroulette import SiegeRouletteView
            self.add_view(SiegeRouletteView(self))
            print("Registered persistent SiegeRouletteView")
        except Exception as e:
            print(f"Failed to register persistent SiegeRouletteView: {e}")

    # --- Data Persistence Handlers (SQLite-backed) ---
    async def load_data(self):
        data = await self.db.get_all_data()
        
        self.bot_admins = data["bot_admins"]
        self.voicebanned_members = data["voicebanned_members"]
        self.muted_members = data["muted_members"]
        self.reddit_mode_channels = data["reddit_mode_channels"]
        self.smash_or_pass_channels = data["smash_or_pass_channels"]
        self.name_enforced_guilds = data["name_enforced_guilds"]
        self.enforced_names = data["enforced_names"]
        self.enabled_name_enforcements = data["enabled_name_enforcements"]
        self.disabled_name_enforcements = data["disabled_name_enforcements"]
        self.honeypot_channels = data["honeypot_channels"]
        self.honeypot_log_channels = data["honeypot_log_channels"]
        self.name_enforcement_on = data["name_enforcement_on"]
        self.joinshield_settings = data["joinshield_settings"]
        self.blocked_words = data["blocked_words"]
        self.mod_log_channels = data.get("mod_log_channels", {})
        self.filter_exempt_roles = data.get("filter_exempt_roles", {})
        self.filter_exempt_channels = data.get("filter_exempt_channels", {})
        self.ticket_staff_roles = data.get("ticket_staff_roles", {})
        self.autoroles = data.get("autoroles", {})
        self.temp_generators = data.get("temp_generators", set())

    async def save_data(self):
        import sqlite3
        def _save():
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            try:
                # Save admins
                cursor.execute("DELETE FROM bot_admins")
                for guild_id, user_ids in self.bot_admins.items():
                    for user_id in user_ids:
                        cursor.execute("INSERT INTO bot_admins (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
                        
                # Save voicebanned
                cursor.execute("DELETE FROM voicebanned_members")
                for user_id in self.voicebanned_members:
                    cursor.execute("INSERT INTO voicebanned_members (user_id) VALUES (?)", (user_id,))
                    
                # Save muted
                cursor.execute("DELETE FROM muted_members")
                for user_id in self.muted_members:
                    cursor.execute("INSERT INTO muted_members (user_id) VALUES (?)", (user_id,))
                    
                # Save reddit and smash_or_pass channels
                cursor.execute("DELETE FROM channel_toggles")
                for chan_id in self.reddit_mode_channels:
                    cursor.execute("INSERT OR REPLACE INTO channel_toggles (channel_id, mode) VALUES (?, 'reddit')", (chan_id,))
                for chan_id in self.smash_or_pass_channels:
                    cursor.execute("INSERT OR REPLACE INTO channel_toggles (channel_id, mode) VALUES (?, 'smash_or_pass')", (chan_id,))
                    
                # Save name enforced guilds
                cursor.execute("DELETE FROM name_enforced_guilds")
                for guild_id in self.name_enforced_guilds:
                    cursor.execute("INSERT INTO name_enforced_guilds (guild_id) VALUES (?)", (guild_id,))
                    
                # (Name enforcement states enabled/disabled are consolidated and saved in save_names)
                    
                # Save honeypot channels
                cursor.execute("DELETE FROM honeypot_channels")
                for guild_id, chan_id in self.honeypot_channels.items():
                    cursor.execute("INSERT INTO honeypot_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, chan_id))
                    
                # Save honeypot log channels
                cursor.execute("DELETE FROM honeypot_log_channels")
                for guild_id, chan_id in self.honeypot_log_channels.items():
                    cursor.execute("INSERT INTO honeypot_log_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, chan_id))
                    
                # Save global settings
                cursor.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES ('name_enforcement_on', ?)", ('1' if self.name_enforcement_on else '0',))
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Failed to save state to SQLite: {e}")
            finally:
                conn.close()
                
        await asyncio.to_thread(_save)

    async def save_names(self):
        import sqlite3
        def _save():
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            try:
                cursor.execute("DELETE FROM enforced_names")
                for user_id, nickname in self.enforced_names.items():
                    state = 'default'
                    if user_id in self.enabled_name_enforcements:
                        state = 'enabled'
                    elif user_id in self.disabled_name_enforcements:
                        state = 'disabled'
                    cursor.execute("INSERT INTO enforced_names (user_id, nickname, enforcement_state) VALUES (?, ?, ?)", (user_id, nickname, state))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Failed to save names to SQLite: {e}")
            finally:
                conn.close()
                
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
        if interaction.guild:
            if interaction.user.id == interaction.guild.owner_id: return True
            guild_admins = self.bot_admins.get(interaction.guild.id, set())
            if interaction.user.id in guild_admins: return True
        return False

    def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Returns the configured log channel (custom mod log -> honeypot log -> system channel -> None)."""
        if not guild:
            return None
        # Try custom mod log first
        log_chan_id = self.mod_log_channels.get(guild.id)
        if log_chan_id:
            chan = guild.get_channel(log_chan_id)
            if chan:
                return chan
        # Fallback to honeypot log
        log_chan_id = self.honeypot_log_channels.get(guild.id)
        if log_chan_id:
            chan = guild.get_channel(log_chan_id)
            if chan:
                return chan
        # Fallback to system channel
        return guild.system_channel

intents = discord.Intents.all()
bot = MyBot(command_prefix="!", intents=intents)

# --- Event Listeners ---

@bot.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=====================================================")
    print(f"Client Authenticated: {bot.user}")
    print(f"Loaded Admin Guilds: {len(bot.bot_admins)}")
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

@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Clean up role menus and giveaways from the database when their messages are deleted."""
    import sqlite3
    db_path = bot.db.db_path
    def _cleanup():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM role_menus WHERE message_id = ?", (payload.message_id,))
        cursor.execute("DELETE FROM role_menu_options WHERE message_id = ?", (payload.message_id,))
        cursor.execute("DELETE FROM giveaways WHERE message_id = ?", (payload.message_id,))
        conn.commit()
        conn.close()
    await asyncio.to_thread(_cleanup)

@bot.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    """Clean up role menus and giveaways from the database when messages are bulk deleted."""
    import sqlite3
    db_path = bot.db.db_path
    def _cleanup():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for msg_id in payload.message_ids:
            cursor.execute("DELETE FROM role_menus WHERE message_id = ?", (msg_id,))
            cursor.execute("DELETE FROM role_menu_options WHERE message_id = ?", (msg_id,))
            cursor.execute("DELETE FROM giveaways WHERE message_id = ?", (msg_id,))
        conn.commit()
        conn.close()
    await asyncio.to_thread(_cleanup)

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