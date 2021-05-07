from discord.ext import tasks
from dataclass import SingleGuildData


class Tasks:
    def __init__(self, client):
        self.client = client

    @tasks.loop(hours=24)
    async def oleo(self):
        instance = SingleGuildData.get_instance()
        for channel in instance.walk_channels(self.client):
            link = "https://cdn.discordapp.com/attachments/595487735620304898/788239202881241108/oleo_de_macaco-1.mp4"
            await channel.send(link)

    def start_tasks(self):
        self.oleo.start()

    def stop_tasks(self):
        self.oleo.cancel()