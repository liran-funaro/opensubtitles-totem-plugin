import json
import logging
import os
from datetime import datetime
from typing import Optional

from opensubtitles_api.results import Query

SECONDS_PER_DAY = float(60 * 60 * 24)
CACHE_LIFETIME_DAYS = 1

try:
    from appdirs import user_cache_dir
except ImportError:
    import tempfile


    def user_cache_dir():
        return tempfile.mkdtemp()


class QueryCache:
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = logging.getLogger("opensubtitles-cache")
        if cache_dir is None:
            cache_dir = user_cache_dir()
        self._cache_dir = os.path.join(cache_dir, 'totem', 'opensubtitles')
        self.logger.info("Cache dir: %s", self._cache_dir)

    def _write_json_file(self, file_path, content: dict):
        self.clear_cache()
        with open(file_path, 'w') as f:
            json.dump(content, f)

    def _read_json_file(self, file_path: str) -> Optional[dict]:
        self.clear_cache()
        if not os.path.isfile(file_path):
            return None
        with open(file_path, 'r') as f:
            return json.load(f)

    def _write_binary_file(self, file_path, content: bytes):
        self.clear_cache()
        with open(file_path, 'wb') as f:
            f.write(content)

    def _read_binary_file(self, file_path: str) -> Optional[bytes]:
        self.clear_cache()
        if not os.path.isfile(file_path):
            return None
        with open(file_path, 'rb') as f:
            return f.read()

    @property
    def cache_path(self):
        os.makedirs(self._cache_dir, exist_ok=True)
        return self._cache_dir

    @property
    def query_cache_path(self):
        path = os.path.join(self._cache_dir, "queries")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def subtitles_cache_path(self):
        path = os.path.join(self._cache_dir, "subtitles")
        os.makedirs(path, exist_ok=True)
        return path

    def query_cache_file(self, filename):
        return os.path.join(self.query_cache_path, filename)

    def subtitles_cache_file(self, sub_id):
        return os.path.join(self.subtitles_cache_path, str(sub_id))

    def read_cached_query(self, query: Query):
        query.set_response(self._read_json_file(self.query_cache_file(query.query_hash)))
        return query

    def write_cached_query(self, query: Query):
        if query.has_response:
            self._write_json_file(self.query_cache_file(query.query_hash), query.response)

    def read_cached_subtitles(self, sub_id):
        return self._read_binary_file(self.subtitles_cache_file(sub_id))

    def write_cached_subtitles(self, sub_id, content: bytes):
        self._write_binary_file(self.subtitles_cache_file(sub_id), content)

    def clear_cache(self):
        current_time = datetime.now()

        for root, _, files in os.walk(self.cache_path):
            for f in files:
                path = os.path.join(root, f)
                modified = datetime.fromtimestamp(os.path.getmtime(path))
                days = (current_time - modified).total_seconds() / SECONDS_PER_DAY
                if days > CACHE_LIFETIME_DAYS:
                    self.logger.info("Delete: %s", f)
                    os.unlink(path)
