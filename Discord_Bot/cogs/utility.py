import random
import discord
from discord import app_commands
from discord.ext import commands

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Standard dice execution (e.g. 1d20+5).")
    @app_commands.choices(rule=[
        app_commands.Choice(name="Normal", value="normal"), 
        app_commands.Choice(name="Advantage", value="adv"), 
        app_commands.Choice(name="Disadvantage", value="dis")
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def roll(self, interaction: discord.Interaction, expression: str, rule: app_commands.Choice[str] = None):
        # Administrative Output Injection (Cheat Code)
        clean_expr = expression.replace("+", "").replace("-", "")
        
        if clean_expr.isdigit() and interaction.client.is_allowed(interaction):
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

    @app_commands.command(name="userinfo", description="Fetches metadata for targeted object.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
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

    @app_commands.command(name="choose", description="Executes random selection from array.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def choose(self, interaction: discord.Interaction, choices: str):
        options = [x.strip() for x in choices.split(',')]
        if len(options) < 2: 
            await interaction.response.send_message("Insufficient options. Minimum 2 required.", ephemeral=True)
            return
        await interaction.response.send_message(embed=discord.Embed(title="Evaluation Output:", description=f"**{random.choice(options)}**", color=discord.Color.blurple()))

    @app_commands.command(name="coin", description="Executes binary evaluation (Heads/Tails).")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def coin(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="🪙 Binary Evaluation", description=f"Result: **{random.choice(['Heads', 'Tails'])}**", color=discord.Color.gold()))

    @app_commands.command(name="teams", description="Splits a roster into a specific number of teams.")
    @app_commands.describe(players="Comma-separated roster", team_count="Number of teams to create (Defaults to 2)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def teams(self, interaction: discord.Interaction, players: str, team_count: int = 2):
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

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
