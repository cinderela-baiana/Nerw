from discord.ext.commands import CommandError

class UserBlacklisted(CommandError):
    """Jogado quando um usuário está na blacklist."""
    pass
