import discord
from discord import app_commands

def check_is_allowed():
    """Decorator that checks if a user is authorized (dev, guild owner, or bot admin)."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.client.is_allowed(interaction):
            return True
        raise app_commands.CheckFailure("Authorization failed.")
    return app_commands.check(predicate)
