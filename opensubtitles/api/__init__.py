"""
OpenSubtitles Download - Totem Plugin (see README.md)
RPC API

Created by (unknown)
Extended by Liran Funaro <fonaro@gmail.com>

Copyright (C) 2006-2018 Liran Funaro

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import logging
import os.path
import threading
import xmlrpc.client
import zlib
from base64 import b64decode
from pathlib import Path
from typing import List, Optional

from opensubtitles.api.cache import QueryCache
from opensubtitles.api.filenameparser import parse_filename
from opensubtitles.api.hash import hash_file
from opensubtitles.api.lang import Languages
from opensubtitles.api.results import Query, SUPPORTED_SUBTITLES_EXT

# See https://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
OPENSUBTITLES_RPC = 'https://api.opensubtitles.org:443/xml-rpc'

OK200 = '200 OK'


class OpenSubtitlesApi:
    """
    OpenSubtitles.org API abstraction
    This contains the logic of the opensubtitles service.
    """

    ERROR_MESSAGE_FMT = u'OpenSubtitles %s: %s'

    def __init__(self, user_agent, username='', password='', cache_dir: Optional[str] = None):
        self.logger = logging.getLogger("opensubtitles-api")
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.DEBUG)
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self._server = xmlrpc.client.Server(OPENSUBTITLES_RPC)
        self._token = None
        self._lock = threading.RLock()

        self._cache = QueryCache(cache_dir)

    ################################################################
    # Login/out
    ################################################################

    def validate_log_in(self):
        with self._lock:
            if not self._token:
                return False

            # We have already logged-in before, check the connection
            try:
                result = self.query(lambda t: self._server.NoOperation(t), login=False)
            except Exception as e:
                self.logger.exception("Failed log-in validation: %s", e)
                result = False

            if not result:
                self.log_off()
            return result

    def log_in(self, validate=False):
        """
        Logs into the opensubtitles web service and gets a valid token for
        the coming communications. If we are already logged it only checks
        the if the token is still valid. It returns a tuple of success boolean
        and error message (if appropriate).

        :return: string (token)
        """
        with self._lock:
            if self._token:
                if not validate:
                    return self._token
                if self.validate_log_in():
                    return self._token

            self.logger.debug("Logging in")
            result = self.query(lambda _: self._server.LogIn(
                self.username, self.password, 'eng', self.user_agent
            ), login=False)

            token = result.get('token', None)
            self.logger.debug(result.get('user'))
            if not token:
                self.log_off()
                raise Exception(self.ERROR_MESSAGE_FMT % ("can't login", token))

            self._token = token
            return token

    def log_off(self):
        with self._lock:
            self._token = None

    ################################################################
    # User queries
    ################################################################

    def search_subtitles_with_title(self, languages: List[str], movie_title: Optional[str] = None,
                                    movie_file_path: Optional[str] = None, refresh_cache=False):
        if movie_file_path is not None:
            movie_properties = parse_filename(movie_file_path)
            self.logger.debug("Movie properties: %s", movie_properties)
        else:
            movie_properties = {}

        if movie_title is None and "search-term" in movie_properties:
            movie_title = movie_properties["search-term"]

        return self._make_query(languages, movie_file_path=movie_file_path, **{
            'query': movie_title
        }, refresh_cache=refresh_cache)

    def search_subtitles_with_file(self, languages: List[str], movie_file_path: str, refresh_cache=False):
        movie_hash, movie_size = hash_file(movie_file_path)
        return self._make_query(languages, movie_file_path=movie_file_path, **{
            'moviehash': movie_hash,
            'moviebytesize': str(movie_size)
        }, refresh_cache=refresh_cache)

    def _make_query(self, languages: List[str], refresh_cache=False, **kwargs) -> Query:
        query = Query(self, languages, **kwargs)
        if not refresh_cache and not query.has_response:
            self._cache.read_cached_query(query)
        if not query.has_response:
            query.set_response(
                self.query(lambda t: self._server.SearchSubtitles(t, [query.query_data]))
            )
            self._cache.write_cached_query(query)
        return query

    def search_subtitles(self, languages: List[str], movie_file_path: Optional[str] = None,
                         movie_title: Optional[str] = None, refresh_cache=False):
        if movie_file_path is not None:
            q = self.search_subtitles_with_file(languages, movie_file_path, refresh_cache=refresh_cache)
            if q.has_results:
                return q
            self.logger.debug("Failed getting subtitles using movie file metadata. Trying with title.")

        return self.search_subtitles_with_title(
            languages, movie_title, movie_file_path=movie_file_path, refresh_cache=refresh_cache
        )

    def download_subtitles(self, subtitle_id, refresh_cache=False) -> bytes:
        if not refresh_cache:
            content = self._cache.read_cached_subtitles(str(subtitle_id))
            if content is not None:
                return content

        result = self.query(lambda t: self._server.DownloadSubtitles(t, [subtitle_id]))

        try:
            subtitle64 = result['data'][0]['data']
            subtitle_zip = b64decode(subtitle64)
            content = zlib.decompress(subtitle_zip, 47)
            self._cache.write_cached_subtitles(str(subtitle_id), content)
            return content
        except Exception as e:
            self.logger.error("Failed parsing subtitles: %s", e)
            raise Exception(u"Parse subtitles error:" % e)

    @staticmethod
    def subtitle_path(movie_path, ext):
        dir_name = os.path.dirname(movie_path)
        file_name, _ = os.path.splitext(os.path.basename(movie_path))
        return os.path.join(dir_name, f"{file_name}.{ext}")

    def subtitle_file(self, movie_path, ext) -> Path:
        return Path(self.subtitle_path(movie_path, ext))

    def get_existing_subtitles_files(self, movie_path):
        for ext in SUPPORTED_SUBTITLES_EXT:
            try:
                subtitle_file = self.subtitle_file(movie_path, ext)
                if subtitle_file.exists():
                    yield subtitle_file
            except Exception as e:
                self.logger.exception(e)

    def remove_subtitles(self, movie_path):
        # Delete all previous subtitle for this file in the movie directory
        for subtitle_file in self.get_existing_subtitles_files(movie_path):
            try:
                subtitle_file.unlink(missing_ok=True)
            except Exception as e:
                self.logger.exception(e)

    def save_subtitles(self, movie_path, subtitles, extension):
        if not subtitles or not extension:
            return

        self.remove_subtitles(movie_path)

        try:
            f = self.subtitle_file(movie_path, extension)
            f.write_bytes(subtitles)
        except Exception as e:
            self.logger.exception("Failed to save subtitles file: %s", e)

    ################################################################
    # Helper query
    ################################################################

    def query(self, expression, login=True, attempts=3):
        self.logger.info("Querying server")
        attempts = max(1, attempts)
        last_attempt = attempts - 1
        for i in range(attempts):
            if not login:
                token = self._token
            else:
                try:
                    token = self.log_in()
                except Exception as e:
                    self.logger.error("Failed login: %s", e)
                    self.log_off()
                    if i == last_attempt:
                        raise Exception("Login error: %s" % e)
                    continue
            try:
                result = expression(token)
                status = result.get('status', None)
                if status != OK200:
                    self.logger.error("Bas response: %s", status)
                    raise Exception(f"invalid results. Status: {status}")
                else:
                    return result
            except Exception as e:
                self.log_off()
                if i == last_attempt:
                    raise Exception(self.ERROR_MESSAGE_FMT % ("Query error", e))

        raise Exception(self.ERROR_MESSAGE_FMT % ("Failed query", "invalid results"))
