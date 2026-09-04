import sqlite3
import asyncio
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")

class DatabaseManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path

    def initialize_tables(self):
        """Initializes SQLite tables and handles schema migrations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Performance tuning pragmas
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Check if we need to migrate old schema tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reddit_mode_channels'")
        has_old_channels = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enabled_name_enforcements'")
        has_old_names = cursor.fetchone() is not None
        
        # --- Create Core Tables ---
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_admins (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voicebanned_members (
                user_id INTEGER PRIMARY KEY
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS muted_members (
                user_id INTEGER PRIMARY KEY
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_toggles (
                channel_id INTEGER PRIMARY KEY,
                mode TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS name_enforced_guilds (
                guild_id INTEGER PRIMARY KEY
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enforced_names (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                enforcement_state TEXT DEFAULT 'default'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS honeypot_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS honeypot_log_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # --- Create New Expansion Tables ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS joinshield_settings (
                guild_id INTEGER PRIMARY KEY,
                min_days INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_words (
                guild_id INTEGER,
                word TEXT,
                PRIMARY KEY (guild_id, word)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                giveaway_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                prize TEXT,
                winner_count INTEGER,
                end_time INTEGER,
                active INTEGER DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (giveaway_id, user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_menus (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                channel_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_menu_options (
                message_id INTEGER,
                role_id INTEGER,
                label TEXT,
                emoji TEXT,
                PRIMARY KEY (message_id, role_id)
            )
        """)
        
        # --- Polishing Feature Tables ---
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mod_log_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_exempt_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_exempt_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)

        # --- Ticket System Tables ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_staff_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                user_id INTEGER
            )
        """)

        # --- Auto-Roles Tables ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autoroles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)

        # --- Temporary Voice Channels Tables ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_voice_generators (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_voice_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                owner_id INTEGER
            )
        """)

        # --- Reminders Tables ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                channel_id INTEGER,
                message TEXT,
                due_time INTEGER
            )
        """)
        
        # --- Perform Schema Upgrades (Self-Healing) ---
        
        # Add required_role_id to giveaways if not exists
        cursor.execute("PRAGMA table_info(giveaways)")
        columns = [info[1] for info in cursor.fetchall()]
        if "required_role_id" not in columns:
            print("[DB] Migrating giveaways table: adding required_role_id column...")
            cursor.execute("ALTER TABLE giveaways ADD COLUMN required_role_id INTEGER")

        # Migrate ticket_settings to ticket_staff_roles if exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_settings'")
        if cursor.fetchone() is not None:
            print("[DB] Migrating ticket_settings staff roles to new ticket_staff_roles table...")
            try:
                cursor.execute("SELECT guild_id, staff_role_id FROM ticket_settings")
                for g_id, r_id in cursor.fetchall():
                    if r_id:
                        cursor.execute("INSERT OR IGNORE INTO ticket_staff_roles (guild_id, role_id) VALUES (?, ?)", (g_id, r_id))
                cursor.execute("DROP TABLE ticket_settings")
                print("[DB] Ticket settings successfully migrated.")
            except Exception as e:
                print(f"[DB] Error migrating ticket settings: {e}")
        
        if has_old_channels:
            print("[DB] Migrating old channel toggles to consolidated channel_toggles table...")
            try:
                # Copy reddit mode channels
                cursor.execute("SELECT channel_id FROM reddit_mode_channels")
                for (chan_id,) in cursor.fetchall():
                    cursor.execute("INSERT OR IGNORE INTO channel_toggles (channel_id, mode) VALUES (?, 'reddit')", (chan_id,))
                    
                # Copy smash or pass channels
                cursor.execute("SELECT channel_id FROM smash_or_pass_channels")
                for (chan_id,) in cursor.fetchall():
                    cursor.execute("INSERT OR IGNORE INTO channel_toggles (channel_id, mode) VALUES (?, 'smash_or_pass')", (chan_id,))
                    
                # Drop deprecated tables
                cursor.execute("DROP TABLE reddit_mode_channels")
                cursor.execute("DROP TABLE smash_or_pass_channels")
                print("[DB] Channel tables successfully consolidated.")
            except Exception as e:
                print(f"[DB] Error consolidating channel tables: {e}")
                
        if has_old_names:
            print("[DB] Migrating old name enforcement tables to consolidated enforced_names table...")
            try:
                # Read enabled and disabled lists
                cursor.execute("SELECT user_id FROM enabled_name_enforcements")
                enabled_ids = {row[0] for row in cursor.fetchall()}
                
                cursor.execute("SELECT user_id FROM disabled_name_enforcements")
                disabled_ids = {row[0] for row in cursor.fetchall()}
                
                # Fetch existing nickname records
                cursor.execute("SELECT user_id, nickname FROM enforced_names")
                old_names = cursor.fetchall()
                
                # Drop and recreate enforced_names with the new schema
                cursor.execute("DROP TABLE enforced_names")
                cursor.execute("""
                    CREATE TABLE enforced_names (
                        user_id INTEGER PRIMARY KEY,
                        nickname TEXT,
                        enforcement_state TEXT DEFAULT 'default'
                    )
                """)
                
                # Write back records with states
                for user_id, nickname in old_names:
                    state = 'default'
                    if user_id in enabled_ids:
                        state = 'enabled'
                    elif user_id in disabled_ids:
                        state = 'disabled'
                    cursor.execute("INSERT INTO enforced_names (user_id, nickname, enforcement_state) VALUES (?, ?, ?)", (user_id, nickname, state))
                    
                # Drop deprecated tables
                cursor.execute("DROP TABLE enabled_name_enforcements")
                cursor.execute("DROP TABLE disabled_name_enforcements")
                print("[DB] Name enforcement tables successfully consolidated.")
            except Exception as e:
                print(f"[DB] Error consolidating name tables: {e}")
        
        conn.commit()
        conn.close()

    async def init_db(self):
        await asyncio.to_thread(self.initialize_tables)

    def load_all(self):
        """Loads all data from consolidated database tables into memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load admins
        cursor.execute("SELECT guild_id, user_id FROM bot_admins")
        bot_admins = {}
        for g, u in cursor.fetchall():
            if g not in bot_admins:
                bot_admins[g] = set()
            bot_admins[g].add(u)
            
        # Load voicebanned
        cursor.execute("SELECT user_id FROM voicebanned_members")
        voicebanned_members = {row[0] for row in cursor.fetchall()}
        
        # Load muted
        cursor.execute("SELECT user_id FROM muted_members")
        muted_members = {row[0] for row in cursor.fetchall()}
        
        # Load channel toggles (split into reddit/smash sets in memory)
        cursor.execute("SELECT channel_id, mode FROM channel_toggles")
        reddit_mode_channels = set()
        smash_or_pass_channels = set()
        for chan_id, mode in cursor.fetchall():
            if mode == 'reddit':
                reddit_mode_channels.add(chan_id)
            elif mode == 'smash_or_pass':
                smash_or_pass_channels.add(chan_id)
        
        # Load name enforced guilds
        cursor.execute("SELECT guild_id FROM name_enforced_guilds")
        name_enforced_guilds = {row[0] for row in cursor.fetchall()}
        
        # Load name enforcements and states
        cursor.execute("SELECT user_id, nickname, enforcement_state FROM enforced_names")
        enforced_names = {}
        enabled_name_enforcements = set()
        disabled_name_enforcements = set()
        for user_id, nickname, state in cursor.fetchall():
            enforced_names[user_id] = nickname
            if state == 'enabled':
                enabled_name_enforcements.add(user_id)
            elif state == 'disabled':
                disabled_name_enforcements.add(user_id)
        
        # Load honeypot channels
        cursor.execute("SELECT guild_id, channel_id FROM honeypot_channels")
        honeypot_channels = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Load honeypot log channels
        cursor.execute("SELECT guild_id, channel_id FROM honeypot_log_channels")
        honeypot_log_channels = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Load global settings
        cursor.execute("SELECT value FROM global_settings WHERE key = 'name_enforcement_on'")
        row = cursor.fetchone()
        name_enforcement_on = (row[0] == '1') if row else False
        
        # Load joinshield settings
        cursor.execute("SELECT guild_id, min_days FROM joinshield_settings")
        joinshield_settings = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Load blocked words
        cursor.execute("SELECT guild_id, word FROM blocked_words")
        blocked_words = {}
        for g, w in cursor.fetchall():
            if g not in blocked_words:
                blocked_words[g] = set()
            blocked_words[g].add(w)
            
        # Load mod log channels
        cursor.execute("SELECT guild_id, channel_id FROM mod_log_channels")
        mod_log_channels = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Load filter exempt roles
        cursor.execute("SELECT guild_id, role_id FROM filter_exempt_roles")
        filter_exempt_roles = {}
        for g, r in cursor.fetchall():
            if g not in filter_exempt_roles:
                filter_exempt_roles[g] = set()
            filter_exempt_roles[g].add(r)
            
        # Load filter exempt channels
        cursor.execute("SELECT guild_id, channel_id FROM filter_exempt_channels")
        filter_exempt_channels = {}
        for g, c in cursor.fetchall():
            if g not in filter_exempt_channels:
                filter_exempt_channels[g] = set()
            filter_exempt_channels[g].add(c)

        # Load ticket staff roles
        cursor.execute("SELECT guild_id, role_id FROM ticket_staff_roles")
        ticket_staff_roles = {}
        for g, r in cursor.fetchall():
            if g not in ticket_staff_roles:
                ticket_staff_roles[g] = set()
            ticket_staff_roles[g].add(r)

        # Load autoroles
        cursor.execute("SELECT guild_id, role_id FROM autoroles")
        autoroles = {}
        for g, r in cursor.fetchall():
            if g not in autoroles:
                autoroles[g] = set()
            autoroles[g].add(r)

        # Load temp voice generators
        cursor.execute("SELECT channel_id FROM temp_voice_generators")
        temp_generators = {row[0] for row in cursor.fetchall()}
            
        conn.close()
        
        return {
            "bot_admins": bot_admins,
            "voicebanned_members": voicebanned_members,
            "muted_members": muted_members,
            "reddit_mode_channels": reddit_mode_channels,
            "smash_or_pass_channels": smash_or_pass_channels,
            "name_enforced_guilds": name_enforced_guilds,
            "enforced_names": enforced_names,
            "enabled_name_enforcements": enabled_name_enforcements,
            "disabled_name_enforcements": disabled_name_enforcements,
            "honeypot_channels": honeypot_channels,
            "honeypot_log_channels": honeypot_log_channels,
            "name_enforcement_on": name_enforcement_on,
            "joinshield_settings": joinshield_settings,
            "blocked_words": blocked_words,
            "mod_log_channels": mod_log_channels,
            "filter_exempt_roles": filter_exempt_roles,
            "filter_exempt_channels": filter_exempt_channels,
            "ticket_staff_roles": ticket_staff_roles,
            "autoroles": autoroles,
            "temp_generators": temp_generators
        }

    async def get_all_data(self):
        return await asyncio.to_thread(self.load_all)

    # --- SQL Writers & Specific Table Methods (Sync) ---

    def set_joinshield(self, guild_id, min_days):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO joinshield_settings (guild_id, min_days) VALUES (?, ?)", (guild_id, min_days))
        conn.commit()
        conn.close()

    def add_blocked_word(self, guild_id, word):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO blocked_words (guild_id, word) VALUES (?, ?)", (guild_id, word.lower().strip()))
        conn.commit()
        conn.close()

    def remove_blocked_word(self, guild_id, word):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blocked_words WHERE guild_id = ? AND word = ?", (guild_id, word.lower().strip()))
        conn.commit()
        conn.close()

    def add_warning(self, guild_id, user_id, moderator_id, reason):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)", 
                       (guild_id, user_id, moderator_id, reason))
        conn.commit()
        conn.close()

    def get_warnings(self, guild_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT moderator_id, reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC", 
                       (guild_id, user_id))
        res = cursor.fetchall()
        conn.close()
        return res

    def clear_warnings(self, guild_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        conn.commit()
        conn.close()

    def create_giveaway(self, guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id))
        g_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return g_id

    def get_giveaway_requirement(self, giveaway_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT required_role_id FROM giveaways WHERE giveaway_id = ?", (giveaway_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def update_giveaway_message(self, giveaway_id, message_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE giveaways SET message_id = ? WHERE giveaway_id = ?", (message_id, giveaway_id))
        conn.commit()
        conn.close()

    def load_active_giveaways(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT giveaway_id, guild_id, channel_id, message_id, prize, winner_count, end_time, required_role_id FROM giveaways WHERE active = 1")
        res = cursor.fetchall()
        conn.close()
        return res

    def add_giveaway_entry(self, giveaway_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)", (giveaway_id, user_id))
        conn.commit()
        conn.close()

    def remove_giveaway_entry(self, giveaway_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?", (giveaway_id, user_id))
        conn.commit()
        conn.close()

    def get_giveaway_entries(self, giveaway_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
        res = [row[0] for row in cursor.fetchall()]
        conn.close()
        return res

    def end_giveaway(self, giveaway_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE giveaways SET active = 0 WHERE giveaway_id = ?", (giveaway_id,))
        conn.commit()
        conn.close()

    def create_role_menu(self, message_id, guild_id, channel_id, options):
        # options is a list of (role_id, label, emoji)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO role_menus (message_id, guild_id, channel_id) VALUES (?, ?, ?)", 
                       (message_id, guild_id, channel_id))
        cursor.execute("DELETE FROM role_menu_options WHERE message_id = ?", (message_id,))
        for role_id, label, emoji in options:
            cursor.execute("INSERT OR REPLACE INTO role_menu_options (message_id, role_id, label, emoji) VALUES (?, ?, ?, ?)", 
                           (message_id, role_id, label, emoji))
        conn.commit()
        conn.close()

    def load_all_role_menus(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, guild_id, channel_id FROM role_menus")
        menus = cursor.fetchall()
        res = []
        for msg_id, g_id, c_id in menus:
            cursor.execute("SELECT role_id, label, emoji FROM role_menu_options WHERE message_id = ?", (msg_id,))
            options = cursor.fetchall()
            res.append({
                "message_id": msg_id,
                "guild_id": g_id,
                "channel_id": c_id,
                "options": options
            })
        conn.close()
        return res

    def set_mod_log_channel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO mod_log_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
        conn.commit()
        conn.close()

    def add_filter_exempt_role(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO filter_exempt_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        conn.commit()
        conn.close()

    def remove_filter_exempt_role(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM filter_exempt_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        conn.commit()
        conn.close()

    def add_filter_exempt_channel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO filter_exempt_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
        conn.commit()
        conn.close()

    def remove_filter_exempt_channel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM filter_exempt_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
        conn.commit()
        conn.close()

    def add_ticket_staff_role(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO ticket_staff_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        conn.commit()
        conn.close()

    def remove_ticket_staff_role(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ticket_staff_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        conn.commit()
        conn.close()

    def create_ticket(self, channel_id, guild_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO active_tickets (channel_id, guild_id, user_id) VALUES (?, ?, ?)", (channel_id, guild_id, user_id))
        conn.commit()
        conn.close()

    def get_user_ticket(self, guild_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM active_tickets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def is_ticket_channel(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM active_tickets WHERE channel_id = ?", (channel_id,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def delete_ticket(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_tickets WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def add_autorole(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO autoroles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        conn.commit()
        conn.close()

    def remove_autorole(self, guild_id, role_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM autoroles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        conn.commit()
        conn.close()

    def add_temp_generator(self, channel_id, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO temp_voice_generators (channel_id, guild_id) VALUES (?, ?)", (channel_id, guild_id))
        conn.commit()
        conn.close()

    def remove_temp_generator(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM temp_voice_generators WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def add_temp_voice(self, channel_id, guild_id, owner_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO temp_voice_channels (channel_id, guild_id, owner_id) VALUES (?, ?, ?)", (channel_id, guild_id, owner_id))
        conn.commit()
        conn.close()

    def delete_temp_voice(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM temp_voice_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def get_all_temp_voices(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, guild_id, owner_id FROM temp_voice_channels")
        res = cursor.fetchall()
        conn.close()
        return res

    def add_reminder(self, guild_id, user_id, channel_id, message, due_time):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reminders (guild_id, user_id, channel_id, message, due_time) VALUES (?, ?, ?, ?, ?)", 
                       (guild_id, user_id, channel_id, message, due_time))
        conn.commit()
        conn.close()

    def get_due_reminders(self, now):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT reminder_id, guild_id, user_id, channel_id, message FROM reminders WHERE due_time <= ?", (now,))
        res = cursor.fetchall()
        conn.close()
        return res

    def delete_reminder(self, reminder_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE reminder_id = ?", (reminder_id,))
        conn.commit()
        conn.close()

    # --- SQL Writers & Specific Table Methods (Async) ---

    async def async_set_joinshield(self, guild_id, min_days):
        await asyncio.to_thread(self.set_joinshield, guild_id, min_days)

    async def async_add_blocked_word(self, guild_id, word):
        await asyncio.to_thread(self.add_blocked_word, guild_id, word)

    async def async_remove_blocked_word(self, guild_id, word):
        await asyncio.to_thread(self.remove_blocked_word, guild_id, word)

    async def async_add_warning(self, guild_id, user_id, moderator_id, reason):
        await asyncio.to_thread(self.add_warning, guild_id, user_id, moderator_id, reason)

    async def async_get_warnings(self, guild_id, user_id):
        return await asyncio.to_thread(self.get_warnings, guild_id, user_id)

    async def async_clear_warnings(self, guild_id, user_id):
        await asyncio.to_thread(self.clear_warnings, guild_id, user_id)

    async def async_create_giveaway(self, guild_id, channel_id, message_id, prize, winners, end_time, required_role_id=None):
        return await asyncio.to_thread(self.create_giveaway, guild_id, channel_id, message_id, prize, winners, end_time, required_role_id)

    async def async_get_giveaway_requirement(self, giveaway_id):
        return await asyncio.to_thread(self.get_giveaway_requirement, giveaway_id)

    async def async_update_giveaway_message(self, giveaway_id, message_id):
        await asyncio.to_thread(self.update_giveaway_message, giveaway_id, message_id)

    async def async_load_active_giveaways(self):
        return await asyncio.to_thread(self.load_active_giveaways)

    async def async_add_giveaway_entry(self, giveaway_id, user_id):
        await asyncio.to_thread(self.add_giveaway_entry, giveaway_id, user_id)

    async def async_remove_giveaway_entry(self, giveaway_id, user_id):
        await asyncio.to_thread(self.remove_giveaway_entry, giveaway_id, user_id)

    async def async_get_giveaway_entries(self, giveaway_id):
        return await asyncio.to_thread(self.get_giveaway_entries, giveaway_id)

    async def async_end_giveaway(self, giveaway_id):
        await asyncio.to_thread(self.end_giveaway, giveaway_id)

    async def async_create_role_menu(self, message_id, guild_id, channel_id, options):
        await asyncio.to_thread(self.create_role_menu, message_id, guild_id, channel_id, options)

    async def async_load_all_role_menus(self):
        return await asyncio.to_thread(self.load_all_role_menus)

    async def async_set_mod_log_channel(self, guild_id, channel_id):
        await asyncio.to_thread(self.set_mod_log_channel, guild_id, channel_id)

    async def async_add_filter_exempt_role(self, guild_id, role_id):
        await asyncio.to_thread(self.add_filter_exempt_role, guild_id, role_id)

    async def async_remove_filter_exempt_role(self, guild_id, role_id):
        await asyncio.to_thread(self.remove_filter_exempt_role, guild_id, role_id)

    async def async_add_filter_exempt_channel(self, guild_id, channel_id):
        await asyncio.to_thread(self.add_filter_exempt_channel, guild_id, channel_id)

    async def async_remove_filter_exempt_channel(self, guild_id, channel_id):
        await asyncio.to_thread(self.remove_filter_exempt_channel, guild_id, channel_id)

    async def async_add_ticket_staff_role(self, guild_id, role_id):
        await asyncio.to_thread(self.add_ticket_staff_role, guild_id, role_id)

    async def async_remove_ticket_staff_role(self, guild_id, role_id):
        await asyncio.to_thread(self.remove_ticket_staff_role, guild_id, role_id)

    async def async_create_ticket(self, channel_id, guild_id, user_id):
        await asyncio.to_thread(self.create_ticket, channel_id, guild_id, user_id)

    async def async_get_user_ticket(self, guild_id, user_id):
        return await asyncio.to_thread(self.get_user_ticket, guild_id, user_id)

    async def async_is_ticket_channel(self, channel_id):
        return await asyncio.to_thread(self.is_ticket_channel, channel_id)

    async def async_delete_ticket(self, channel_id):
        await asyncio.to_thread(self.delete_ticket, channel_id)

    async def async_add_autorole(self, guild_id, role_id):
        await asyncio.to_thread(self.add_autorole, guild_id, role_id)

    async def async_remove_autorole(self, guild_id, role_id):
        await asyncio.to_thread(self.remove_autorole, guild_id, role_id)

    async def async_add_temp_generator(self, channel_id, guild_id):
        await asyncio.to_thread(self.add_temp_generator, channel_id, guild_id)

    async def async_remove_temp_generator(self, channel_id):
        await asyncio.to_thread(self.remove_temp_generator, channel_id)

    async def async_add_temp_voice(self, channel_id, guild_id, owner_id):
        await asyncio.to_thread(self.add_temp_voice, channel_id, guild_id, owner_id)

    async def async_delete_temp_voice(self, channel_id):
        await asyncio.to_thread(self.delete_temp_voice, channel_id)

    async def async_get_all_temp_voices(self):
        return await asyncio.to_thread(self.get_all_temp_voices)

    async def async_add_reminder(self, guild_id, user_id, channel_id, message, due_time):
        await asyncio.to_thread(self.add_reminder, guild_id, user_id, channel_id, message, due_time)

    async def async_get_due_reminders(self, now):
        return await asyncio.to_thread(self.get_due_reminders, now)

    async def async_delete_reminder(self, reminder_id):
        await asyncio.to_thread(self.delete_reminder, reminder_id)
