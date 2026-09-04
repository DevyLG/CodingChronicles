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
            if match[2] is not None:
                label = f"✅ Winner: {match[match[2]]}"
                style = discord.ButtonStyle.success
            else:
                label = f"Match {i+1}: {match[0]} vs {match[1]}"
                style = discord.ButtonStyle.secondary
            
            btn = discord.ui.Button(label=label, style=style, row=i // 2)
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
        embed = discord.Embed(title=f"🏆 Tournament: Round {self.round_num}", color=discord.Color.gold())
        embed.description = f"**Total Teams**: {len(self.teams)}"
        
        matches_text = ""
        for i, m in enumerate(self.matches):
            if m[2] is not None:
                matches_text += f"⭐ **Match {i+1}**: {m[0]} vs {m[1]} ➔ 🏆 **{m[m[2]]}**\n"
            else:
                matches_text += f"⚔️ **Match {i+1}**: {m[0]} vs {m[1]}\n"
                
        if not matches_text:
            matches_text = "No matches this round."
            
        embed.add_field(name="⚔️ Matchups", value=matches_text, inline=False)
        
        byes = [t for t in self.teams if t not in [m[0] for m in self.matches] and t not in [m[1] for m in self.matches]]
        if byes:
            embed.add_field(name="🛡️ Byes (Auto-Advance)", value="\n".join(f"• {b}" for b in byes), inline=False)
            
        return embed

class TournamentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tournament", description="Initializes an interactive bracket manager.")
    @app_commands.describe(
        players="Comma-separated roster of player names (Optional if use_voice is True)",
        team_size="Participants per team construct (Integer, Defaults to 1)",
        use_voice="Automatically pull player names from your current voice channel"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tournament(self, interaction: discord.Interaction, players: str = None, team_size: int = 1, use_voice: bool = False):
        player_list = []
        
        # 1. Handle Voice Channel Import
        member = None
        if use_voice:
            if not interaction.guild:
                await interaction.response.send_message("❌ Voice import can only be used inside a server channel.", ephemeral=True)
                return
                
            member = interaction.guild.get_member(interaction.user.id)
            if not member or not member.voice or not member.voice.channel:
                await interaction.response.send_message("❌ You must be connected to a voice channel to import players.", ephemeral=True)
                return
                
            player_list = [m.display_name for m in member.voice.channel.members if not m.bot]
            
        # 2. Handle Manual Input
        if players:
            manual_list = [p.strip() for p in players.replace(';', ',').replace('\n', ',').split(',') if p.strip()]
            player_list.extend(manual_list)
            
        # Remove duplicates
        seen = set()
        player_list = [x for x in player_list if not (x in seen or seen.add(x))]
        
        if len(player_list) < 2:
            await interaction.response.send_message("❌ Insufficient player names. Please enter at least 2 players or import from voice.", ephemeral=True)
            return
 
        if team_size < 1:
            await interaction.response.send_message("❌ Team size must be at least 1.", ephemeral=True)
            return
 
        random.shuffle(player_list)
        
        teams = []
        for i in range(0, len(player_list), team_size):
            chunk = player_list[i:i + team_size]
            teams.append(" & ".join(chunk))

        if len(teams) < 2:
            await interaction.response.send_message("❌ You need at least 2 teams to start a tournament. Decrease the team size or add more players.", ephemeral=True)
            return

        if len(teams) > 32:
            await interaction.response.send_message("❌ Maximum number of teams supported is 32 to prevent Discord formatting limits.", ephemeral=True)
            return

        history = []
        view = TournamentView(teams, host_id=interaction.user.id, msg_history=history)
        embed = view.make_embed()
        
        if use_voice and member and member.voice and member.voice.channel:
            embed.set_footer(text=f"Imported from voice channel: {member.voice.channel.name}")
            
        await interaction.response.send_message(embed=embed, view=view)
        
        first_msg = await interaction.original_response()
        history.append(first_msg)

async def setup(bot):
    await bot.add_cog(TournamentCog(bot))
