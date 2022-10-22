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
import argparse
import logging
import os
import struct
import threading
import xmlrpc.client
import zlib
from base64 import b64decode
from pprint import pprint
from typing import List

# See https://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
OPENSUBTITLES_RPC = 'https://api.opensubtitles.org:443/xml-rpc'

OK200 = '200 OK'
SUBTITLES_EXT = {"asc", "txt", "sub", "srt", "smi", "ssa", "ass"}

block_size = 2 ** 16
min_file_size = block_size * 2
longlong_format = 'q'  # long long
longlong_size = struct.calcsize(longlong_format)
longlong_per_block = int(block_size / longlong_size)
block_mask = 0xFFFFFFFFFFFFFFFF0

# Map of ISO 639-1 language codes to the codes used by opensubtitles.org API
LANGUAGES_CODE_MAP = {
    'sq': 'alb',
    'ar': 'ara',
    'hy': 'arm',
    'ay': 'ass',
    'bs': 'bos',
    'pb': 'pob',
    'bg': 'bul',
    'ca': 'cat',
    'zh': 'chi',
    'hr': 'hrv',
    'cs': 'cze',
    'da': 'dan',
    'nl': 'dut',
    'en': 'eng',
    'eo': 'epo',
    'eu': 'eus',
    'et': 'est',
    'fi': 'fin',
    'fr': 'fre',
    'gl': 'glg',
    'ka': 'geo',
    'de': 'ger',
    'el': 'ell',
    'he': 'heb',
    'hi': 'hin',
    'hu': 'hun',
    'is': 'ice',
    'id': 'ind',
    'it': 'ita',
    'ja': 'jpn',
    'kk': 'kaz',
    'ko': 'kor',
    'lv': 'lav',
    'lt': 'lit',
    'lb': 'ltz',
    'mk': 'mac',
    'ms': 'may',
    'no': 'nor',
    'oc': 'oci',
    'fa': 'per',
    'pl': 'pol',
    'pt': 'por',
    'ro': 'rum',
    'ru': 'rus',
    'sr': 'scc',
    'sk': 'slo',
    'sl': 'slv',
    'es': 'spa',
    'sv': 'swe',
    'th': 'tha',
    'tr': 'tur',
    'uk': 'ukr',
    'vi': 'vie',
}


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


def get_language_term(languages: List[str]):
    return ",".join(map(LANGUAGES_CODE_MAP.get, languages))


class OpenSubtitlesApi:
    """
    OpenSubtitles.org API abstraction
    This contains the logic of the opensubtitles service.
    """

    ERROR_MESSAGE_FMT = u'OpenSubtitles %s: %s'

    def __init__(self, user_agent, username='', password=''):
        self.logger = logging.getLogger("OpenSubtitlesApi")
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self._server = xmlrpc.client.Server(OPENSUBTITLES_RPC)
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

            result = self.query(lambda t: self._server.LogIn(
                self.username, self.password, 'eng', self.user_agent
            ), login=False)

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

    def search_subtitles_with_title(self, languages_term, movie_title):
        query_search_data = {
            'sublanguageid': languages_term,
            'query': movie_title
        }

        result = self.query(lambda t: self._server.SearchSubtitles(t, [query_search_data]))
        data = result.get('data', None)
        if not data:
            raise Exception(u'No results found')
        return data

    def search_subtitles_with_file(self, languages_term, movie_file_path):
        movie_hash, movie_size = hash_file(movie_file_path)

        hash_search_data = {
            'sublanguageid': languages_term,
            'moviehash': movie_hash,
            'moviebytesize': str(movie_size)
        }

        result = self.query(lambda token: self._server.SearchSubtitles(token, [hash_search_data]))
        data = result.get('data', None)
        if not data:
            raise Exception(u'No results found')
        return data

    def search_subtitles(self, languages_term, movie_file_path):
        logging.log(logging.DEBUG, "languages_term: %s", languages_term)
        try:
            return self.search_subtitles_with_file(languages_term, movie_file_path)
        except Exception as e:
            self.logger.error("Failed getting file's subtitles: %s", e)

        file_name = os.path.splitext(os.path.basename(movie_file_path))[0]
        movie_title = file_name.replace(".", " ")
        movie_title = movie_title.replace("DDP5", "")
        movie_title = movie_title.replace("Atmos", "")
        movie_title = movie_title.replace("265-EVO", "")
        movie_title = movie_title.strip()
        logging.log(logging.DEBUG, "Movie title: %s", movie_title)
        return self.search_subtitles_with_title(languages_term, movie_title)

    def download_subtitles(self, subtitle_id):
        result = self.query(lambda t: self._server.DownloadSubtitles(t, [subtitle_id]))

        try:
            subtitle64 = result['data'][0]['data']
            subtitle_zip = b64decode(subtitle64)
            return zlib.decompress(subtitle_zip, 47)
        except Exception as e:
            self.logger.error("Failed parsing subtitles: %s", e)
            raise Exception(u"Parse subtitles error:" % e)

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


def extant_file_exist(input_path: str) -> str:
    path = os.path.expanduser(input_path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("path does not exist")
    return path


def main():
    p = argparse.ArgumentParser(description="Opensubtitles.org Downloader")
    p.add_argument("-f", "--file-path", type=extant_file_exist)
    p.add_argument("-t", "--title", type=str)
    p.add_argument("-o", "--op", action="append", default=["query"], choices=["query", "download"])
    p.add_argument("-i", "--index", type=int)
    p.add_argument("-l", "--language", nargs="*", default=["he", "en"], choices=LANGUAGES_CODE_MAP.keys())
    args = p.parse_args()

    if args.file_path is None and args.title is None:
        raise Exception("Must supply either file-path or title")
    if args.file_path is not None and args.title is not None:
        raise Exception("Must supply either file-path or title")

    languages = get_language_term(args.language)

    open_sub = OpenSubtitlesApi('Totem')
    for op in args.op:
        if op == "query":
            if args.file_path is not None:
                ret = open_sub.search_subtitles(languages, args.file_path)
            else:
                ret = open_sub.search_subtitles_with_title(languages, args.title)

            for r in ret:
                pprint(r)
        elif op == "download":
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
