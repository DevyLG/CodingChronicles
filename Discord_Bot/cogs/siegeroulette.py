import random
import discord
from discord import app_commands
from discord.ext import commands

class OpCountModal(discord.ui.Modal):
    """Modal interface for dynamic operator generation."""
    def __init__(self, side: str, dashboard_view: discord.ui.View):
        super().__init__(title=f"{side.capitalize()} Request")
        self.side = side
        self.dashboard_view = dashboard_view 
        self.bot = dashboard_view.bot
        
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
            pool = self.bot.attack_ops
            color = 0x1A5276
            title = f"⚔️ Operators Generated ({count})"
        else:
            pool = self.bot.defense_ops
            color = 0xE67E22
            title = f"🛡️ Operators Generated ({count})"

        if not pool:
            await interaction.response.send_message("Data Error: Relevant arrays not populated. Check config.", ephemeral=True)
            return

        chosen_ops = random.sample(pool, min(count, len(pool)))
        ops_text = "\n".join([f"**{i+1}.** {op}" for i, op in enumerate(chosen_ops)])
        
        embed = discord.Embed(title=title, description=ops_text, color=color)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.dashboard_view.spawned_messages.append(msg)

class SiegeRouletteView(discord.ui.View):
    """Persistent interface for tactical evaluation and generation."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.last_attack_strat = None
        self.last_defense_strat = None
        self.last_chaotic_strat = None
        self.spawned_messages = [] 

    # --- ROW 0: STRATEGY GENERATION ---

    @discord.ui.button(label="Attack Strat", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def btn_attack_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.attack_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in self.bot.attack_strats if s != self.last_attack_strat]
        if not pool: pool = self.bot.attack_strats
            
        strat = random.choice(pool)
        self.last_attack_strat = strat
        
        embed = discord.Embed(title="⚔️ Attack Strat", description=strat, color=0x1A5276)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.spawned_messages.append(msg)

    @discord.ui.button(label="Defense Strat", style=discord.ButtonStyle.danger, emoji="🛡️", row=0)
    async def btn_defense_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.defense_strats:
            await interaction.response.send_message("Data Error: Strat arrays empty.", ephemeral=True)
            return
            
        pool = [s for s in self.bot.defense_strats if s != self.last_defense_strat]
        if not pool: pool = self.bot.defense_strats
            
        strat = random.choice(pool)
        self.last_defense_strat = strat
        
        embed = discord.Embed(title="🛡️ Defense Strat", description=strat, color=0xE67E22)
        await interaction.response.send_message(embed=embed)
        
        msg = await interaction.original_response()
        self.spawned_messages.append(msg)

    @discord.ui.button(label="Chaotic Strat", style=discord.ButtonStyle.secondary, emoji="🎲", row=0)
    async def btn_chaotic_strat(self, interaction: discord.Interaction, button: discord.ui.Button):
        full_pool = self.bot.attack_strats + self.bot.defense_strats + self.bot.general_strats
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
            except (discord.NotFound, discord.Forbidden):
                pass
            except Exception:
                pass
                
        self.spawned_messages.clear()

class SiegeRouletteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="siegeroulette", description="Initializes tactical dashboard interface.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def siegeroulette(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎯 Tactical Generation Interface",
            description=(
                "**Dashboard Initialized.**\n"
                "Select parameters below to execute generation routines.\n\n"
                "This interface remains persistent for rapid execution."
            ),
            color=0x202225
        )
        await interaction.response.send_message(embed=embed, view=SiegeRouletteView(bot=self.bot))

async def setup(bot):
    await bot.add_cog(SiegeRouletteCog(bot))
