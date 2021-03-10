from discord.ext import commands
from Utils import Field, create_async_database
from dataclass import write_blacklist, write_reaction_messages_to_file
from typing import Union, Optional

import discord
import psutil


class Moderation(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def blacklist(self, ctx, user: Union[discord.Member, discord.User], *, reason: str = None):
        """Deixa uma pessoa na lista negra.

        A lista negra é uma lista de usuários que impede
        elas de usarem os comandos do bot.

        **Veja também**: Comando `whitelist`."""
        appinfo = await self.client.application_info()
        if user in appinfo.team.members:
            await ctx.reply("Você não pode dar blacklist em membros do time!")
            return
        fields = (
            Field(name="user_id", type="TEXT NOT NULL"),
            Field(name="reason", type="TEXT")
        )
        async with create_async_database("main.db") as wrap:
            await wrap.create_table_if_absent("blacklisteds", fields)

        write_blacklist(user, reason)
        await ctx.reply(f"O usuário {user} foi banido de usar o bot.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def whitelist(self, ctx, user: Union[discord.Member, discord.User]):
        """
        Tira um usuário da lista negra.

        **Veja também**: Comando `blacklist`.
        """
        async with create_async_database("main.db") as wrap:
            item = await wrap.get_item("blacklisteds", f"user_id = {user.id}", "user_id")

            if item is None:
                return await ctx.reply(f"O usuário {user} não está banido.")

            await wrap.remove_item("blacklisteds", f"user_id = {user.id}")
        await ctx.reply(f"O usuário {user} foi desbanido.")

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def nick(self, ctx, user: discord.Member, *, new_nick: str):
        """Altera o apelido de um usuário."""

        await user.edit(nick=new_nick)
        await ctx.reply(f"Alterado nick de {user} para {new_nick}!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(1, 10, commands.BucketType.member)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """
        Expulsa um usuário.

        Você e o bot precisam da permissão `Expulsar membros`.
        """
        if member == ctx.message.author:
            await ctx.channel.send("Você não pode se expulsar!")
            return

        emoji = self.client.get_emoji(793335773892968502)
        if emoji is None:
            emoji = "🔨"
        embed = discord.Embed(title=f"{emoji} {member} foi expulso!",


                                      description=f"**Motivo:** *{reason}*",
                                      color=0x00ff9d)
        embed.set_footer(text="Não façam como ele crianças, respeitem as regras.")
        await member.kick(reason=f"{reason}; Ação efetuada por {ctx.author}")
        await ctx.channel.send(embed=embed)
        await ctx.message.delete()

    @commands.command(aliases=["mov"])
    @commands.has_permissions(manage_messages=True)
    async def mover_mensagem(self, ctx, message: discord.Message, canal: discord.TextChannel, *, motivo=None):
        if motivo is None:
            motivo = 'Não especificado'

        hook = await canal.create_webhook(name="Gamera Bot")
        files = None
        if message.attachments:
            files = [await att.to_file() for att in message.attachments]
        await canal.send(content=f'{message.author.mention}', embed=discord.Embed(title=f'Mensagem movida!',
                                                    description=f'Sua mensagem foi movida para cá.\n'
                                                    f'Motivo: {motivo}'),
                                                    delete_after=20)
        content = message.content
        if message.reference is not None and \
                not isinstance(message.reference, discord.DeletedReferencedMessage):
            # respondeu a alguém usando o novo sistema e
            # a mensagem referenciada não foi apagada

            rmessage = await ctx.channel.fetch_message(message.reference.message_id)

            files = []
            for attch in message.attachments:
                files.append(await attch.to_file())

            wmessage = await hook.send(username=rmessage.author.display_name,
                            avatar_url=rmessage.author.avatar_url,
                            content=rmessage.content,
                            files=files,
                            wait=True)

            content = f"> {wmessage.content}\n{rmessage.author.mention} {message.content}"

        await hook.send(content=content, files=files, username=message.author.name,
                        avatar_url=message.author.avatar_url)

        await message.delete()
        await ctx.message.delete()
        await hook.delete()

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def reaction_activate(self, ctx, channel: Optional[discord.TextChannel],
                                msg: str,
                                emoji: discord.Emoji,
                                role: discord.Role):
        """Sisteminha básico de reaction roles, atualmente suporta apenas 1 reação por mensagem."""
        message = await channel.send(msg)
        try:
            await message.add_reaction(emoji)
        except discord.InvalidArgument:
            await channel.send("Me desculpe, aparentemente há algo de errado com o seu emoji :sad:")
        except discord.NotFound:
            await channel.send("Emoji não encontrado")
        except discord.HTTPException:
            await channel.send("Algo deu errado:(")
        else:
            write_reaction_messages_to_file(channel.id, message.id, emoji.id, role.id)
            await channel.send("Mensagem reagida com sucesso!")

def setup(client):
    client.add_cog(Moderation(client))