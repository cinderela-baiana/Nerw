import collections
import asyncio

class Playlist:
    def __init__(self):
        self._deque = collections.deque()

    def __len__(self):
        return len(self._deque)

    def __iter__(self):
        return iter(self._deque)

    def __contains__(self, item):
        return item in self._deque

    def __bool__(self):
        return len(self) != 0

    def estimated_time(self):
        est = sum(map(lambda e: e.duration, self._deque))
        return est

    def add_video(self, source):
        self._deque.append(source)
        return source

    async def download_all_videos(self):
        done, pending = await asyncio.wait({
            video.download() for video in self
        })
        return done, pending

    def get_next_video(self):
        if len(self) == 0:
            return None, None # ajuda a evitar TypeErrors.

        item = self._deque.popleft()
        return item

    @property
    def currently_playing(self):
        return self._deque[0]
