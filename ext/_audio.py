import collections
import asyncio
import logging

logger = logging.getLogger(__name__)

class _FakePlayer:
    def ended(self, ctx):
        return True

    def __repr__(self):
        return f"FakePlayer at 0x{id(self)}"

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

    def __repr__(self):
        return f"Playlist(items={self._deque})"

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
            return None

        item = self._deque.popleft()
        return item

    def clear(self):
        self._deque.clear()

    @property
    def currently_playing(self):
        try:
            return self._deque[0]
        except IndexError:
            return _FakePlayer()

    def empty(self):
        return len(self) == 0

    def upcoming(self):
        return self._deque[1:]

    def __next__(self):
        res = self.get_next_video()
        if res is None:
            raise StopIteration
        return res
