import random
import discord
from discord import app_commands
from discord.ext import commands

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
            except Exception:
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

class TournamentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tournament", description="Initializes an interactive bracket manager.")
    @app_commands.describe(players="Comma-separated roster", team_size="Participants per team construct (Integer)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tournament(self, interaction: discord.Interaction, players: str, team_size: int = 1):
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

async def setup(bot):
    await bot.add_cog(TournamentCog(bot))
