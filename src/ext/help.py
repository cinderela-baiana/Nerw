from discord.ext import commands, menus
from typing import Dict, Optional, Iterable
from copy import deepcopy
import discord
import yaml
import string

with open("config/credentials.yaml") as fp:
    cred = yaml.safe_load(fp)

def is_canary():
    return cred.get("ENVIROMENT", "CANARY") == "CANARY"

class HelpMenu(menus.Menu):
    def __init__(self, ctx):
        super().__init__()
        self.page = 0
        self.ctx = ctx
    
    def get_commands(self) -> discord.Embed:
        dic = self.ctx.bot.get_cog("Ajuda")._filter_by_letter(self.ctx.bot.commands)
        char = list(dic.keys())[self.page]
        com = dic[char]

        embed = discord.Embed(title=f"Comandos começando com {char.upper()}", color=discord.Color.blue())
        embed.description = desc = " | ".join(map(lambda cmd : cmd.name, com)) or "Não há"
        return embed

    @menus.button("◀️")
    async def left_button(self, payload):
        if self.page > 0:
            self.page -= 1
            await self.message.edit(embed=self.get_commands())

    @menus.button("▶️")
    async def right_button(self, payload):
        if self.page < 25:
            self.page += 1
            await self.message.edit(embed=self.get_commands())
    

    async def send_initial_message(self, ctx, channel):
        return await ctx.reply(embed=self.get_commands())
    

class Help(commands.Cog, name="Ajuda"):
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
        embed = discord.Embed(title=command.qualified_name,
                              description=command.usage,
                              color=color)

        alal = "|".join(aliases_copy)

        embed.add_field(name="Descrição", value=command.help if command.help is not None else "Nenhuma ajuda disponível")
        embed.add_field(name="Apelidos", value=alal if alal != "" else "Nenhum", inline=False)
        embed.add_field(name="Argumentação", value=f"`{command.qualified_name} {command.signature}`", inline=True)
        return embed

    def get_subcommand_help(self, ctx, command: commands.Group):
        embed = self.get_command_help(ctx, command)
        cmds = command.commands
        scheme = []

        for cmd in cmds:
            scheme.append(f"`,{command.qualified_name} {cmd.name}`")
        embed.add_field(name="Subcomandos", value="\n".join(scheme))

        return embed

    def get_hidden_commands(self):
        return list(filter(lambda command : command.enabled, self.client.commands))

    @commands.command(name="helpall")
    async def _help(self, ctx, *, cmd: Optional[str]):
        if isinstance(ctx.me, discord.ClientUser):
            color = discord.Color.from_rgb(230, 0, 0)
        else:
            color = ctx.me.color
        permissions = discord.Permissions(administrator=True)
        url = discord.utils.oauth_url(self.client.user.id, permissions)
        eb = discord.Embed(color=color)
        eb.set_author(name="Me convide para o seu servidor!", url=url)

        filt = filter(lambda command: not command.hidden, self.client.commands)
        eb.description = " | ".join(map(lambda command: f"`{command.name}`", filt))

    @commands.command(name="help")
    async def _help(self, ctx, *, cmd: Optional[str]):
        """Mostra essa mensagem."""

        if cmd is None:
            men = HelpMenu(ctx)
            await men.start(ctx)
        else:
            try:
                command = self.client.get_command(cmd)
                if isinstance(command, commands.Group):
                    hlp = self.get_subcommand_help(ctx, command)
                elif isinstance(command, commands.Command):
                    hlp = self.get_command_help(ctx, command)
            except ValueError:
                await ctx.reply(f"Não existe nenhum comando com o nome **{cmd}**.")
                return
            else:
                try:
                    await ctx.reply(embed=hlp)
                except UnboundLocalError:
                    return await ctx.reply(f"Não existe nenhum comando com o nome **{cmd}**.")

    def _filter_by_letter(self, commands: Iterable[commands.Command]) -> Dict[str, Iterable[commands.Command]]:
        let = {letter: [] for letter in string.ascii_lowercase}
        for command in commands:
            name = command.name[0]
            let[name].append(command)
        
        return let

def setup(client):
    client.add_cog(Help(client))