from discord.ext.commands import CommandError

class UserBlacklisted(CommandError):
    """Jogado quando um usuário está na blacklist."""
    pass

class VideoDurationOutOfBounds(CommandError):
    """Jogado quando um vídeo tem uma duração maior que `Utils.HALF_HOUR_IN_SECS`."""
    pass