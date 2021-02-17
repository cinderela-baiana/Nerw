from discord.ext import commands
from Utils import DatabaseWrap, Field
from dataclass import write_blacklist
from typing import Union

import discord

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 10, commands.BucketType.member)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """
        Bane um usuário.

        Você e o bot precisam da permissão `Banir membros`.
        """
        if member == ctx.message.author:
            await ctx.channel.send("Você não pode se banir!")
            return

        emoji = self.client.get_emoji(793335773892968502)
        if emoji is None:
            emoji = "🔨"
        embed = discord.Embed(title=f"{emoji} {member} foi banido!",
                                      description=f"**Motivo:** *{reason}*",
                                      color=0x00ff9d)
        embed.set_footer(text="Não façam como ele crianças, respeitem as regras.")
        await member.ban(reason=f"{reason}; Ação efetuada por {ctx.author}")
        await ctx.channel.send(embed=embed)
        await ctx.message.delete()

    @commands.command()
    @commands.is_owner()
    async def blacklist(self, ctx, user: Union[discord.Member, discord.User], *, reason: str = None):
        """Deixa uma pessoa na lista negra.

        A lista negra é uma lista de usuários que impede
        eles de usarem os comandos do bot.

        **Veja também**: Comando `whitelist`."""
        fields = (
            Field(name="user_id", type="TEXT NOT NULL"),
            Field(name="reason", type="TEXT")
        )
        wrap = DatabaseWrap.from_filepath("main.db")
        wrap.create_table_if_absent("blacklisteds", fields)

        write_blacklist(user, reason)
        await ctx.reply(f"O usuário {user} foi banido de usar o bot.")

    @commands.command()
    @commands.is_owner()
    async def whitelist(self, ctx, user: Union[discord.Member, discord.User]):
        """
        Tira um usuário da lista negra.

        **Veja também**: Comando `blacklist`.
        """
        wrap = DatabaseWrap.from_filepath("main.db")
        item = wrap.get_item("blacklisteds", f"user_id = {user.id}", "user_id")

        if item is None:
            return await ctx.reply(f"O usuário {user} não está banido.")

        wrap.remove_item("blacklisteds", f"user_id = {user.id}")
        await ctx.reply(f"O usuário {user} foi desbanido.")

def setup(client):
    client.add_cog(Moderation(client))