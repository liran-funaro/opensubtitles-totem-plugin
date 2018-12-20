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
from base64 import b64decode

import os
import zlib
import struct
import threading
import xmlrpc.client

OK200 = '200 OK'
SUBTITLES_EXT = {"asc", "txt", "sub", "srt", "smi", "ssa", "ass", }

block_size = 2 ** 16
min_file_size = block_size * 2
longlong_format = 'q'  # long long
longlong_size = struct.calcsize(longlong_format)
longlong_per_block = int(block_size / longlong_size)
block_mask = 0xFFFFFFFFFFFFFFFF0


def read_longlong(file_handle):
    buf = file_handle.read(longlong_size)
    (l_value,) = struct.unpack(longlong_format, buf)
    return l_value


def hash_block(file_handle, current_hash):
    for _ in range(longlong_per_block):
        current_hash += read_longlong(file_handle)
        current_hash &= block_mask
    return current_hash


def hash_file(file_path):
    """
    Create a hash of movie title (file name)
    :param file_path: The URI of the movie file
    :return: tuple (hash, size)
    """
    file_size = os.path.getsize(file_path)

    if file_size < min_file_size:
        raise Exception("Hash: file must be larger than two blocks (%s)" % min_file_size)

    file_hash = file_size
    last_block = max(0, file_size - block_size)

    with open(file_path, "rb") as file_handle:
        for hash_place in [0, last_block]:
            file_handle.seek(hash_place, os.SEEK_SET)
            if file_handle.tell() != hash_place:
                raise Exception("Hash: Failed to seek to %s" % hash_place)
            file_hash = hash_block(file_handle, file_hash)

    returned_hash = "%016x" % file_hash
    return returned_hash, file_size


class OpenSubtitlesApi(object):
    """
    OpenSubtitles.org API abstraction
    This contains the logic of the opensubtitles service.
    """

    ERROR_MESSAGE_FMT = 'OpenSubtitles %s: %s'

    def __init__(self, user_agent, username='', password=''):
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self._server = xmlrpc.client.Server('http://api.opensubtitles.org/xml-rpc')
        self._token = None
        self._lock = threading.RLock()

    ################################################################
    # Login/out
    ################################################################

    def validate_log_in(self):
        with self._lock:
            if not self._token:
                return False

            # We have already logged-in before, check the connection
            try:
                result = self.query(lambda token: self._server.NoOperation(token), login=False)
            except:
                result = False

            if not result:
                self.log_off()
            return result

    def log_in(self, validate=False):
        """
        Logs into the opensubtitles web service and gets a valid token for
        the coming comunications. If we are already logged it only checks
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

            result = self.query(lambda token: self._server.LogIn(self.username, self.password,
                                                                 'eng', self.user_agent),
                                login=False)

            token = result.get('token', None)
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

    def search_subtitles(self, languages_term, movie_file_path):
        movie_hash, movie_size = hash_file(movie_file_path)

        hash_search_data = {
            'sublanguageid': languages_term,
            'moviehash': movie_hash,
            'moviebytesize': str(movie_size)
        }

        query_search_data = {
            'sublanguageid': languages_term,
            'query': os.path.basename(movie_file_path)
        }

        result = self.query(lambda token: self._server.SearchSubtitles(token, [hash_search_data]))

        data = result.get('data', None)
        if not data:
            result = self.query(lambda token: self._server.SearchSubtitles(token, [query_search_data]))

        data = result.get('data', None)
        if not data:
            raise Exception(u'No results found')

        return data

    def download_subtitles(self, subtitle_id):
        result = self.query(lambda token: self._server.DownloadSubtitles(token, [subtitle_id]))

        try:
            subtitle64 = result['data'][0]['data']
            subtitle_zip = b64decode(subtitle64)
            return zlib.decompress(subtitle_zip, 47)
        except Exception as e:
            raise Exception("Parse subtitles error:" % e)

    ################################################################
    # Helper query
    ################################################################

    def query(self, expression, login=True):
        for is_last in [False, False, True]:
            if not login:
                token = self._token
            else:
                try:
                    token = self.log_in()
                except Exception as e:
                    self.log_off()
                    if is_last:
                        raise Exception("Login error: %s" % e)
                    continue
            try:   
                result = expression(token)
                status = result.get('status', None)
                if status == OK200:
                    return result
                else:
                    raise Exception("invalid results. Status: %s" % status)
            except Exception as e:
                self.log_off()
                if is_last:
                    raise Exception(self.ERROR_MESSAGE_FMT % ("Query error", e))

        raise Exception(self.ERROR_MESSAGE_FMT % ("Failed query", "invalid results"))
