import functools
import time
from pathlib import Path


class LRUCache:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}

    def get(self, key):
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            # Usuń najstarszy element
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()


# Globalny cache
file_stats_cache = LRUCache(5000)


@functools.lru_cache(maxsize=1000)
def get_file_size_readable_cached(size_bytes):
    """Cached version of file size conversion"""
    return get_file_size_readable(size_bytes)
