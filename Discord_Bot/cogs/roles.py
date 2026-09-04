import discord
from discord import app_commands
from discord.ext import commands
import re
import asyncio
from cogs.utils import check_is_allowed

def parse_hex_color(color_str: str) -> discord.Color:
    """Parses standard hex colors (e.g. #FF5733 or 0xFF5733) or color names into discord.Color."""
    if not color_str:
        return discord.Color.blue()
    
    color_str = color_str.strip().lstrip('#').lower()
    
    color_map = {
        "red": discord.Color.red(),
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "gold": discord.Color.gold(),
        "orange": discord.Color.orange(),
        "purple": discord.Color.purple(),
        "magenta": discord.Color.magenta(),
        "teal": discord.Color.teal()
    }
    
    if color_str in color_map:
        return color_map[color_str]
        
    try:
        val = int(color_str, 16)
        return discord.Color(val)
    except ValueError:
        return discord.Color.blue()

def is_valid_emoji(emoji_str: str) -> bool:
    if not emoji_str:
        return False
    emoji_str = emoji_str.strip()
    
    # Custom emoji check
    custom_emoji_pattern = re.compile(r'^<(a)?:[a-zA-Z0-9_]+:([0-9]+)>$')
    if custom_emoji_pattern.match(emoji_str):
        return True
        
    # Unicode emoji check: must contain at least one non-ASCII character
    # and must not contain any ASCII alphabetic letters
    if any(ord(c) > 127 for c in emoji_str) and not any(c.isalpha() for c in emoji_str):
        return True
        
    return False

class RoleMenuButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji_str: str = None):
        # Resolve emoji if provided and valid
        resolved_emoji = None
        if emoji_str and is_valid_emoji(emoji_str):
            clean_emoji = emoji_str.strip()
            if clean_emoji.startswith("<") and clean_emoji.endswith(">"):
                try:
                    resolved_emoji = discord.PartialEmoji.from_str(clean_emoji)
                except Exception:
                    resolved_emoji = None
            else:
                resolved_emoji = clean_emoji

        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"rolemenu:role:{role_id}",
            emoji=resolved_emoji if resolved_emoji else None
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(self.role_id)
        
        if not role:
            await interaction.followup.send("❌ This role no longer exists in the server.", ephemeral=True)
            return
            
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Self-Assign Role Menu")
                await interaction.followup.send(f"✅ Removed the role **{role.name}**.", ephemeral=True)
            else:
                await member.add_roles(role, reason="Self-Assign Role Menu")
                await interaction.followup.send(f"✅ Added the role **{role.name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ I do not have permission to manage the role **{role.name}**. "
                "Make sure my bot role is higher than this role in the server settings.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)

class RoleMenuView(discord.ui.View):
    def __init__(self, options):
        # options is a list of tuples/lists containing: (role_id, label, emoji)
        super().__init__(timeout=None)
        for role_id, label, emoji in options:
            self.add_item(RoleMenuButton(role_id, label, emoji))

class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolemenu", description="Creates a persistent self-assign role menu with buttons.")
    @app_commands.describe(
        channel="The text channel to send the role menu to",
        embed_title="Title of the role menu embed",
        embed_description="Description of the role menu embed",
        options="Options list. Format: @Role1,emoji1,Label1 | @Role2,emoji2,Label2",
        color="Embed color (Hex code e.g. #FF5733 or name e.g. red)"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @check_is_allowed()
    async def rolemenu(self, interaction: discord.Interaction, channel: discord.TextChannel, embed_title: str, embed_description: str, options: str, color: str = None):
        await interaction.response.defer(ephemeral=True)
        
        # Parse options
        parsed_options = []
        raw_options = []
        
        # Split by pipe, semicolon, or newline
        for line in options.replace('\n', '|').replace(';', '|').split('|'):
            line = line.strip()
            if line:
                raw_options.append(line)

        for raw_opt in raw_options:
            parts = [p.strip() for p in raw_opt.split(',')]
            if len(parts) < 1 or not parts[0]:
                continue
            
            role_part = parts[0]
            emoji_part = None
            label_part = None
            
            if len(parts) == 2:
                second_part = parts[1]
                if is_valid_emoji(second_part):
                    emoji_part = second_part
                else:
                    label_part = second_part
            elif len(parts) >= 3:
                emoji_part = parts[1] if parts[1] else None
                label_part = parts[2]
                
            # Clean up emoji_part if it is invalid
            if emoji_part and not is_valid_emoji(emoji_part):
                emoji_part = None

            # Resolve role ID from mention or raw text digits
            role_id = None
            role_digits = re.findall(r'\d+', role_part)
            if role_digits:
                role_id = int(role_digits[0])
            else:
                # Look up role by name in current guild
                role_obj = discord.utils.get(interaction.guild.roles, name=role_part)
                if role_obj:
                    role_id = role_obj.id
            
            if not role_id:
                await interaction.followup.send(f"❌ Could not resolve role: `{role_part}`", ephemeral=True)
                return
                
            role_obj = interaction.guild.get_role(role_id)
            if not role_obj:
                await interaction.followup.send(f"❌ Role ID `{role_id}` not found in this server.", ephemeral=True)
                return
                
            if not label_part:
                label_part = role_obj.name
                
            parsed_options.append((role_id, label_part, emoji_part))

        if not parsed_options:
            await interaction.followup.send("❌ No valid options were parsed. Please check the format.", ephemeral=True)
            return

        if len(parsed_options) > 25:
            await interaction.followup.send("❌ You cannot have more than 25 roles in a single menu.", ephemeral=True)
            return

        # Parse embed color
        embed_color = parse_hex_color(color)

        # Create the embed
        embed = discord.Embed(
            title=embed_title,
            description=embed_description,
            color=embed_color
        )
        
        try:
            # Create view
            view = RoleMenuView(parsed_options)
            msg = await channel.send(embed=embed, view=view)
            
            # Save role menu to database
            await self.bot.db.async_create_role_menu(msg.id, interaction.guild_id, channel.id, parsed_options)
            
            # Register view dynamically
            self.bot.add_view(view)
            
            await interaction.followup.send(f"✅ Self-Assign Role Menu created in {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create role menu: {e}", ephemeral=True)
            print(f"Error creating role menu: {e}")

async def setup(bot):
    await bot.add_cog(RolesCog(bot))
