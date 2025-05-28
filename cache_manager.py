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

    def clear(self):
        """Wyczyść cache"""
        self.cache.clear()
        self.access_times.clear()

    def size(self):
        """Zwróć aktualny rozmiar cache"""
        return len(self.cache)


# Globalny cache z mniejszym rozmiarem dla stabilności
file_stats_cache = LRUCache(1000)  # Zmniejszono z 5000 na 1000


@functools.lru_cache(maxsize=500)  # Zmniejszono z 1000 na 500
def get_file_size_readable_cached(size_bytes):
    """Cached version of file size conversion"""
    return get_file_size_readable(size_bytes)


def clear_all_caches():
    """Wyczyść wszystkie cache dla zwolnienia pamięci"""
    file_stats_cache.clear()
    get_file_size_readable_cached.cache_clear()


def get_file_size_readable(size_bytes):
    """Konwertuje rozmiar pliku w bajtach na czytelny format."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"
