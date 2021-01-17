from discord.ext import commands
from typing import Optional
from copy import deepcopy

import discord

class Help(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    def get_command_help(self, ctx, command):
        if command is None:
            raise ValueError

        if isinstance(ctx.me, discord.ClientUser):
            color = discord.Color.from_rgb(230, 0, 0)
        else:
            color = ctx.me.color

        aliases_copy = deepcopy(command.aliases)
        embed = discord.Embed(title=command.name,
                description=command.usage,
                color=color)
        try:
            aliases_copy.remove(ctx.invoked_with)
        except ValueError:
            # não tem problema se o apelido não estiver presente
            pass

        alal = "|".join(aliases_copy)

        embed.add_field(name="Descrição", value=command.help if command.help is not None else "Nenhuma ajuda disponível")
        embed.add_field(name="Apelidos", value=alal if alal is not "" else "Nenhum", inline=False)
        embed.add_field(name="Argumentação", value=f"`{command.name} {command.signature}`", inline=True)
        return embed

    @commands.command(name="help")
    async def _help(self, ctx, cmd: Optional[str]):
        """Mostra essa mensagem."""

        if cmd is None:
            all_commands = " | ".join([command.name for command in self.client.commands])
            eb = discord.Embed(title="Ajuda!", description=all_commands, color=discord.Color.magenta())
            await ctx.send(embed=eb)
        else:
            hlp = self.get_command_help(ctx, self.client.get_command(cmd))
            await ctx.send(embed=hlp)


def setup(client):
    client.add_cog(Help(client))