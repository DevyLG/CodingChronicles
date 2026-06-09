import discord
from discord import app_commands
from discord.ext import commands

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Returns documented command array.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Registered Commands", color=discord.Color.blue())
        embed.add_field(name="👑 Authorization Required", value="`/addadmin`, `/removeadmin`, `/purge`", inline=False)
        embed.add_field(name="🏷️ Data Management", value="`/name change`, `/name toggle`, `/name server`", inline=False)
        embed.add_field(name="⚙️ Environment Hooks", value="`/redditmode`, `/smashorpass`", inline=False)
        embed.add_field(name="👻 Disruption", value="`/move_spam`, `/unmove`, `/voiceban`, `/unvoiceban`, `/mute`, `/unmute`", inline=False)
        embed.add_field(name="🎲 Evaluators", value="`/roll`, `/choose`, `/coin`, `/userinfo`, `/tournament`, `/siegeroulette`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
