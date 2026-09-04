import random
import os
import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
from cogs.utils import check_is_allowed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIEGE_FILE = os.path.join(BASE_DIR, "siege_data.json")

def save_siege_file(bot):
    """Helper to save the current operator and strategy pools back to JSON."""
    data = {
        "attack_strats": bot.attack_strats,
        "defense_strats": bot.defense_strats,
        "general_strats": bot.general_strats,
        "attack_ops": bot.attack_ops,
        "defense_ops": bot.defense_ops
    }
    with open(SIEGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_loadout(op_name: str, side: str) -> str:
    """Generates a randomized primary, secondary, gadget, and challenge modifier for an operator."""
    primaries = ["Assault Rifle", "Shotgun", "LMG", "Marksman Rifle", "SMG"]
    secondaries = ["Handgun", "Machine Pistol", "Revolver", "Super Shorty Shotgun"]
    
    attacker_gadgets = ["Frag Grenade", "Stun Grenade", "Smoke Grenade", "Claymore", "Hard Breach Charge", "Impact EMP"]
    defender_gadgets = ["Barbed Wire", "Deployable Shield", "Nitro Cell", "Bulletproof Camera", "Proximity Alarm", "Impact Grenade"]
    
    modifiers = [
        "Suppressor Only (Silent Assassin)",
        "Iron Sights Only (Old School)",
        "Angled Grip & Laser (Run 'n Gun)",
        "Hipfire Only (No Scope)",
        "Pistol Only (Secondary Challenge)",
        "No Attachments (Recruit Mode)",
        "Canted Sights/1.5x Only",
        "Full Auto Spray (No burst firing)"
    ]
    
    primary = random.choice(primaries)
    secondary = random.choice(secondaries)
    gadget = random.choice(attacker_gadgets if side == "attack" else defender_gadgets)
    modifier = random.choice(modifiers)
    
    loadout_text = (
        f"👤 **Operator**: **{op_name}**\n"
        f"🔫 **Primary Weapon**: {primary}\n"
        f"🔫 **Secondary Weapon**: {secondary}\n"
        f"🎒 **Gadget**: {gadget}\n"
        f"⚠️ **Challenge**: {modifier}"
    )
    return loadout_text

class SiegeRouletteView(discord.ui.View):
    """Persistent interface for tactical evaluation and generation."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.last_attack_strat = None
        self.last_defense_strat = None
        self.last_chaotic_strat = None
        
        self.last_title = None
        self.last_result = None
        self.last_color = 0x202225
        self.spawned_messages = [] 

    def update_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎯 Tactical Generation Dashboard",
            description=(
                "Select parameters below to execute generation routines.\n"
                "Updates occur in-place on this dashboard. Use **Post to Squad** to share."
            ),
            color=self.last_color
        )
        if self.last_title and self.last_result:
            embed.add_field(name=f"Result: {self.last_title}", value=self.last_result, inline=False)
        else:
            embed.add_field(name="Last Action", value="None", inline=False)
        return embed

    # --- ROW 0: STRATEGY GENERATION ---

    @discord.ui.button(label="Attack Strat", style=discord.ButtonStyle.primary, emoji="⚔️", row=0, custom_id="siege_btn_attack_strat")
    async def btn_attack_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.attack_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in self.bot.attack_strats if s != self.last_attack_strat]
        if not pool: pool = self.bot.attack_strats
            
        strat = random.choice(pool)
        self.last_attack_strat = strat
        
        self.last_title = "Attacker Strategy"
        self.last_result = f"💡 **Strategy**: {strat}"
        self.last_color = 0x1A5276
        
        # Enable post button
        self.btn_post_squad.disabled = False
        
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="Defense Strat", style=discord.ButtonStyle.danger, emoji="🛡️", row=0, custom_id="siege_btn_defense_strat")
    async def btn_defense_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.defense_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in self.bot.defense_strats if s != self.last_defense_strat]
        if not pool: pool = self.bot.defense_strats
            
        strat = random.choice(pool)
        self.last_defense_strat = strat
        
        self.last_title = "Defender Strategy"
        self.last_result = f"💡 **Strategy**: {strat}"
        self.last_color = 0xE67E22
        
        # Enable post button
        self.btn_post_squad.disabled = False
        
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="Chaotic Strat", style=discord.ButtonStyle.secondary, emoji="🎲", row=0, custom_id="siege_btn_chaotic_strat")
    async def btn_chaotic_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        full_pool = self.bot.attack_strats + self.bot.defense_strats + self.bot.general_strats
        if not full_pool:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in full_pool if s != self.last_chaotic_strat]
        if not pool: pool = full_pool
            
        strat = random.choice(pool)
        self.last_chaotic_strat = strat
        
        self.last_title = "Chaotic Strategy"
        self.last_result = f"🎲 **Strategy**: {strat}"
        self.last_color = discord.Color.dark_grey().value
        
        # Enable post button
        self.btn_post_squad.disabled = False
        
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    # --- ROW 1: OPERATOR GENERATION ---

    @discord.ui.button(label="Roll Attack Op", style=discord.ButtonStyle.primary, emoji="👥", row=1, custom_id="siege_btn_attack_ops")
    async def btn_attack_ops(self, interaction: discord.Interaction, button: discord.ui.Button):
        pool = self.bot.attack_ops
        if not pool:
            await interaction.response.send_message("Data Error: Attacker operators pool is empty.", ephemeral=True)
            return
            
        op = random.choice(pool)
        self.last_title = "Attacker Operator Roll"
        self.last_result = f"👤 **Operator**: **{op}**"
        self.last_color = 0x1A5276
        
        # Enable post button
        self.btn_post_squad.disabled = False
        
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="Roll Defense Op", style=discord.ButtonStyle.danger, emoji="👥", row=1, custom_id="siege_btn_defense_ops")
    async def btn_defense_ops(self, interaction: discord.Interaction, button: discord.ui.Button):
        pool = self.bot.defense_ops
        if not pool:
            await interaction.response.send_message("Data Error: Defender operators pool is empty.", ephemeral=True)
            return
            
        op = random.choice(pool)
        self.last_title = "Defender Operator Roll"
        self.last_result = f"👤 **Operator**: **{op}**"
        self.last_color = 0xE67E22
        
        # Enable post button
        self.btn_post_squad.disabled = False
        
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    # --- ROW 2: ACTIONS ---
    
    @discord.ui.button(label="Post to Squad", style=discord.ButtonStyle.success, emoji="📢", row=2, disabled=True, custom_id="siege_btn_post_squad")
    async def btn_post_squad(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.last_title or not self.last_result:
            await interaction.response.send_message("❌ Nothing to post yet. Roll something first!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=f"📢 {self.last_title}",
            description=self.last_result,
            color=self.last_color
        )
        embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
        
        msg = await interaction.channel.send(embed=embed)
        self.spawned_messages.append(msg)
        
        await interaction.response.send_message("📢 Results posted to the squad!", ephemeral=True)

    @discord.ui.button(label="Clear Spam", style=discord.ButtonStyle.secondary, emoji="🧹", row=2, custom_id="siege_btn_clear_spam")
    async def btn_clear_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        for msg in self.spawned_messages:
            try:
                await msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            except Exception:
                pass
                
        self.spawned_messages.clear()
        await interaction.followup.send("🧹 Cleared all roulette messages from chat.", ephemeral=True)

class SiegeRouletteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    siegeroulette_group = app_commands.Group(
        name="siegeroulette",
        description="Siege Roulette commands."
    )

    @siegeroulette_group.command(name="dashboard", description="Initializes the tactical generation dashboard interface.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dashboard(self, interaction: discord.Interaction):
        view = SiegeRouletteView(bot=self.bot)
        await interaction.response.send_message(embed=view.update_embed(), view=view)

    @siegeroulette_group.command(name="add_op", description="Adds a new operator to the roulette pools.")
    @app_commands.describe(
        side="Whether this operator is for Attack or Defense",
        name="The name of the operator"
    )
    @app_commands.choices(side=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Defense", value="defense")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def add_op(self, interaction: discord.Interaction, side: str, name: str):
        op_name = name.strip()
        if not op_name:
            await interaction.response.send_message("❌ Invalid name.", ephemeral=True)
            return

        if side == "attack":
            if op_name in self.bot.attack_ops:
                await interaction.response.send_message(f"❌ **{op_name}** is already in the Attacker pool.", ephemeral=True)
                return
            self.bot.attack_ops.append(op_name)
            self.bot.attack_ops.sort()
        else:
            if op_name in self.bot.defense_ops:
                await interaction.response.send_message(f"❌ **{op_name}** is already in the Defender pool.", ephemeral=True)
                return
            self.bot.defense_ops.append(op_name)
            self.bot.defense_ops.sort()

        # Save to file
        await asyncio.to_thread(save_siege_file, self.bot)
        await interaction.response.send_message(f"✅ Added **{op_name}** to the **{side.capitalize()}** operator pool.", ephemeral=True)

    @siegeroulette_group.command(name="remove_op", description="Removes an operator from the roulette pools.")
    @app_commands.describe(
        side="Whether the operator is in Attack or Defense",
        name="The name of the operator to remove"
    )
    @app_commands.choices(side=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Defense", value="defense")
    ])
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def remove_op(self, interaction: discord.Interaction, side: str, name: str):
        op_name = name.strip()
        
        if side == "attack":
            matches = [op for op in self.bot.attack_ops if op.lower() == op_name.lower()]
            if not matches:
                await interaction.response.send_message(f"❌ **{op_name}** is not in the Attacker pool.", ephemeral=True)
                return
            for m in matches:
                self.bot.attack_ops.remove(m)
        else:
            matches = [op for op in self.bot.defense_ops if op.lower() == op_name.lower()]
            if not matches:
                await interaction.response.send_message(f"❌ **{op_name}** is not in the Defender pool.", ephemeral=True)
                return
            for m in matches:
                self.bot.defense_ops.remove(m)

        # Save to file
        await asyncio.to_thread(save_siege_file, self.bot)
        await interaction.response.send_message(f"✅ Removed **{op_name}** from the **{side.capitalize()}** operator pool.", ephemeral=True)

    @siegeroulette_group.command(name="ops_list", description="Lists all operators currently in the roulette pools.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ops_list(self, interaction: discord.Interaction):
        att_ops = sorted(self.bot.attack_ops)
        def_ops = sorted(self.bot.defense_ops)
        
        att_str = ", ".join(att_ops) if att_ops else "None"
        def_str = ", ".join(def_ops) if def_ops else "None"
        
        if len(att_str) > 1024: att_str = att_str[:1020] + "..."
        if len(def_str) > 1024: def_str = def_str[:1020] + "..."
        
        embed = discord.Embed(
            title="🎯 Siege Roulette Operator Pools",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"⚔️ Attackers ({len(att_ops)})", value=att_str, inline=False)
        embed.add_field(name=f"🛡️ Defenders ({len(def_ops)})", value=def_str, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SiegeRouletteCog(bot))
