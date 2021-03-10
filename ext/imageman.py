from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw
from typing import Optional
import io
import discord
import aiohttp
import time

MEMEMAN_IMG = "https://i.ibb.co/4YmHZCm/cumm.png"
FONT_LIMIT = 31 # depende muito da fonte e do tamanho usado.

def splitlen(string, per):
    return [string[i : i + per] for i in range(0, len(string), per)]

class ImageCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._mememan_bytes = None

    async def fetch_mememan(self):
        if self._mememan_bytes is not None:
            return self._mememan_bytes

        async with aiohttp.ClientSession() as session:
            async with session.get(MEMEMAN_IMG) as request:
               return await request.read()

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def mememan(self, ctx, *, text: str):
        async with ctx.typing():
            image: Image.Image = Image.open(io.BytesIO(await self.fetch_mememan()))

            if len(text) > FONT_LIMIT:
                text = "\n".join(splitlen(text, FONT_LIMIT))

            # a gente vai soltar um JPG, e JPGs não suportam alpha.
            image = image.convert("RGB")
            image_draw = ImageDraw.Draw(image)

            font = ImageFont.truetype("assets/coolvetica.ttf", 45)

            image_draw.text((10,0), text, (10,10,10), font=font)
            image.save("mememan.jpg")

        with open("mememan.jpg", "rb") as file:
            timm = str(round(time.time()))
            await ctx.reply(file=discord.File(file, filename=timm + ".jpg"))

    def get_colors(self, image, colors=10, resize=150):
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        image = Image.open(image)

        image = image.copy()
        image.thumbnail((resize, resize))

        palt = image.convert("P", palette=Image.ADAPTIVE, colors=colors)
        palette = palt.getpalette()
        color_counts = sorted(palt.getcolors(), reverse=True)
        colors = []

        for c in range(len(colors) + 1):
            palette_index = color_counts[c][1]
            dominant_color = palette[palette_index*3:palette_index*3+3]

            colors.append(tuple(dominant_color))

        return colors

    def save_palette(self, colors, swatchsize=20, outfile="palette.png"):
        num_colors = len(colors)
        palette = Image.new('RGB', (swatchsize*num_colors, swatchsize))
        draw = ImageDraw.Draw(palette)

        posx = 0
        for color in colors:
            draw.rectangle([posx, 0, posx+swatchsize, swatchsize], fill=color)
            posx = posx + swatchsize

        del draw
        palette.save(outfile, "PNG")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def domin(self, ctx, member: Optional[discord.Member]):
        """
        Pega a cor dominante do seu avatar ou do membro *member*.

        As vezes a cor retornada, pode parecer não ser precisa, mas é basicamente
        a cor com a maior quantidade de pixels coloridos com aquela cor, então
        pode variar com o tamanho da imagem.
        """
        avatar = (member or ctx.author).avatar_url

        colors = self.get_colors(await avatar.read())
        self.save_palette(colors)

        with open("palette.png", "rb") as fp:
            file = discord.File(fp, "palette.png")

        await ctx.reply(file=file)

def setup(client):
    client.add_cog(ImageCog(client))
