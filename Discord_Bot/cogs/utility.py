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
            if num_dice < 1 or die_type < 2:
                await interaction.response.send_message("❌ Invalid dice parameters. Count must be >= 1 and sides must be >= 2.", ephemeral=True)
                return
                
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

    @app_commands.command(name="whois", description="Fetches detailed metadata and warning count for a member.")
    @app_commands.describe(member="The member to fetch info for")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def whois(self, interaction: discord.Interaction, member: discord.User = None):
        target = member or interaction.user
        
        # Resolve to Member if in guild context
        if interaction.guild and not isinstance(target, discord.Member):
            target = interaction.guild.get_member(target.id) or target

        is_member = isinstance(target, discord.Member)
        
        embed = discord.Embed(title=f"👤 User Profile: {target.name}", color=target.color if is_member else discord.Color.blurple())
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="📛 Username", value=f"{target} ({target.mention})", inline=True)
        embed.add_field(name="🆔 User ID", value=target.id, inline=True)
        
        if interaction.guild:
            warnings_list = await self.bot.db.async_get_warnings(interaction.guild.id, target.id)
            warn_count = len(warnings_list) if warnings_list else 0
            embed.add_field(name="⚠️ Infractions", value=f"`{warn_count}` warning(s)", inline=True)
        else:
            embed.add_field(name="⚠️ Infractions", value="N/A (DM Context)", inline=True)
            
        created_ts = int(target.created_at.timestamp())
        embed.add_field(name="📅 Account Created", value=f"<t:{created_ts}:D>\n(<t:{created_ts}:R>)", inline=True)
        
        if is_member and target.joined_at:
            joined_ts = int(target.joined_at.timestamp())
            embed.add_field(name="📥 Joined Server", value=f"<t:{joined_ts}:D>\n(<t:{joined_ts}:R>)", inline=True)
        else:
            embed.add_field(name="📥 Joined Server", value="N/A", inline=True)

        if is_member:
            roles = [role.mention for role in target.roles if role.name != "@everyone"]
            roles_str = " ".join(roles) if roles else "None"
            embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=roles_str, inline=False)
            
            key_perms = []
            perms = target.guild_permissions
            if perms.administrator:
                key_perms.append("Administrator")
            else:
                if perms.manage_guild: key_perms.append("Manage Server")
                if perms.kick_members: key_perms.append("Kick Members")
                if perms.ban_members: key_perms.append("Ban Members")
                if perms.manage_channels: key_perms.append("Manage Channels")
                if perms.manage_messages: key_perms.append("Manage Messages")
                if perms.mention_everyone: key_perms.append("Mention Everyone")
                if perms.mute_members: key_perms.append("Mute Members")
                if perms.deafen_members: key_perms.append("Deafen Members")
                if perms.move_members: key_perms.append("Move Members")
            
            key_perms_str = ", ".join(key_perms) if key_perms else "None"
            embed.add_field(name="🔑 Key Permissions", value=key_perms_str, inline=False)
        else:
            embed.add_field(name="🎭 Roles", value="N/A (Not in server)", inline=False)
            
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Fetches detailed server statistics and metadata.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ This command can only be used inside a server.", ephemeral=True)
            return

        total_members = guild.member_count
        humans = sum(1 for m in guild.members if not m.bot)
        bots = total_members - humans
        
        online = sum(1 for m in guild.members if m.status == discord.Status.online)
        idle = sum(1 for m in guild.members if m.status == discord.Status.idle)
        dnd = sum(1 for m in guild.members if m.status == discord.Status.do_not_disturb)
        offline = total_members - (online + idle + dnd)
        
        categories = len(guild.categories)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        stage_channels = len(guild.stage_channels)
        
        created_ts = int(guild.created_at.timestamp())
        
        embed = discord.Embed(title=f"🏰 Server Information: {guild.name}", color=discord.Color.gold())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="👑 Owner", value=f"{guild.owner.mention} (`{guild.owner.id}`)" if guild.owner else f"`{guild.owner_id}`", inline=True)
        embed.add_field(name="🆔 Guild ID", value=guild.id, inline=True)
        embed.add_field(name="📅 Created On", value=f"<t:{created_ts}:D> (<t:{created_ts}:R>)", inline=False)
        
        member_desc = (
            f"👥 **Total**: {total_members}\n"
            f"👤 **Humans**: {humans}\n"
            f"🤖 **Bots**: {bots}\n"
            f"🟢 **Online**: {online} | 🌙 **Idle**: {idle} | 🔴 **DND**: {dnd} | ⚫ **Offline**: {offline}"
        )
        embed.add_field(name="👥 Members", value=member_desc, inline=False)
        
        channel_desc = (
            f"📁 **Categories**: {categories}\n"
            f"💬 **Text**: {text_channels}\n"
            f"🔊 **Voice**: {voice_channels}\n"
            f"🎙️ **Stage**: {stage_channels}"
        )
        embed.add_field(name="📺 Channels", value=channel_desc, inline=True)
        
        other_desc = (
            f"💎 **Tier**: {guild.premium_tier}\n"
            f"🚀 **Boosts**: {guild.premium_subscription_count}\n"
            f"🎭 **Roles**: {len(guild.roles)}\n"
            f"🛡️ **Verification**: {guild.verification_level.name.title()}"
        )
        embed.add_field(name="⚙️ Details", value=other_desc, inline=True)
        
        if guild.banner:
            embed.set_image(url=guild.banner.url)
            
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
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

    @app_commands.command(name="teams", description="Splits a roster of players into balanced teams.")
    @app_commands.describe(
        players="Comma-separated roster of player names (Optional if use_voice is True)",
        team_count="Number of teams to create (e.g. 2)",
        team_size="Number of players per team (Overrides team_count if specified)",
        use_voice="Automatically pull player names from your current voice channel"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def teams(self, interaction: discord.Interaction, players: str = None, team_count: int = None, team_size: int = None, use_voice: bool = False):
        player_list = []
        
        # 1. Handle Voice Channel Import
        member = None
        if use_voice:
            if not interaction.guild:
                await interaction.response.send_message("❌ Voice import can only be used inside a server channel.", ephemeral=True)
                return
                
            member = interaction.guild.get_member(interaction.user.id)
            if not member or not member.voice or not member.voice.channel:
                await interaction.response.send_message("❌ You must be connected to a voice channel to import player names.", ephemeral=True)
                return
                
            player_list = [m.display_name for m in member.voice.channel.members if not m.bot]
            
        # 2. Handle Manual Input
        if players:
            manual_list = [p.strip() for p in players.replace(';', ',').replace('\n', ',').split(',') if p.strip()]
            player_list.extend(manual_list)
            
        # Remove duplicates while preserving order
        seen = set()
        player_list = [x for x in player_list if not (x in seen or seen.add(x))]
        
        if len(player_list) < 2:
            await interaction.response.send_message("❌ Insufficient player names. Please enter at least 2 players or import from voice.", ephemeral=True)
            return

        random.shuffle(player_list)
        
        # 3. Calculate team count
        total_players = len(player_list)
        if team_size and team_size > 0:
            team_count = max(1, total_players // team_size)
            
        if not team_count or team_count < 2:
            team_count = 2
            
        if team_count > total_players:
            team_count = total_players

        if team_count > 25:
            await interaction.response.send_message("❌ Maximum team count is 25 due to Discord embed display limits.", ephemeral=True)
            return

        teams = [[] for _ in range(team_count)]
        for i, player in enumerate(player_list):
            teams[i % team_count].append(player)
            
        embed = discord.Embed(
            title="⚔️ Team Splitter",
            description=f"Successfully split **{total_players}** players into **{team_count}** teams.",
            color=discord.Color.gold()
        )
        if use_voice and member and member.voice and member.voice.channel:
            embed.set_footer(text=f"Imported from voice channel: {member.voice.channel.name}")
        
        for i in range(team_count):
            players_str = "\n".join(f"• {p}" for p in teams[i])
            embed.add_field(name=f"🛡️ Team {i+1} ({len(teams[i])})", value=players_str, inline=True)
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
