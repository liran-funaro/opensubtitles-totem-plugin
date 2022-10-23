import pprint
from collections import defaultdict
from typing import Dict, List, Optional

import tabulate

from opensubtitles_api.hash import hash_query
from opensubtitles_api.lang import iter_normalize_languages, Languages, LANGUAGES_MAP

try:
    from opensubtitles_api import OpenSubtitlesApi
except ImportError:
    pass

SUBTITLES_EXT = {"asc", "txt", "sub", "srt", "smi", "ssa", "ass"}


class Subtitles:
    def __init__(self, owner: 'OpenSubtitlesApi', query: 'Query', data: Dict[str, str]):
        self.owner = owner
        self.query = query
        self.data = data

        self._content: Optional[bytes] = None

    def __getitem__(self, item):
        return self.data[item]

    @property
    def id(self):
        return self.data['IDSubtitleFile']

    @property
    def language(self):
        return LANGUAGES_MAP[self.data['SubLanguageID']]

    @property
    def summary(self):
        return [
            self.id,
            self.language,
            self.data['SubFileName'],
            self.data['SubFormat'],
            self.data['SubRating'],
            self.data['SubSize'],
        ]

    @property
    def has_content(self):
        return self._content is not None

    @property
    def content(self):
        if not self.has_content:
            self._content = self.owner.download_subtitles(self.id)
        return self._content

    def __repr__(self):
        return repr(self.data)


class Query:
    def __init__(self, owner: 'OpenSubtitlesApi', languages: Languages,
                 movie_file_path: Optional[str] = None, **kwargs):
        self.owner = owner
        self.languages = list(iter_normalize_languages(languages))
        self.movie_file_path = movie_file_path

        self.query_data = {
            'sublanguageid': ",".join(self.languages),
            **kwargs,
        }
        self.query_hash = hash_query(self.query_data)

        self.response: Optional[Dict[str, object]] = None
        self.results: Optional[List[Subtitles]] = None

    @property
    def has_response(self):
        return self.response is not None

    @property
    def has_results(self):
        return self.results is not None

    def set_response(self, response):
        if not response:
            return False

        self.response = response
        data = response.get('data', None)
        if not data:
            return False

        lang_order = defaultdict(lambda: float('inf'), **{l: i for i, l in enumerate(self.languages)})

        self.results: List[Subtitles] = sorted(
            (Subtitles(self.owner, self, r) for r in data if r['SubFormat'] in SUBTITLES_EXT),
            key=lambda x: (lang_order[x['SubLanguageID']], -float(x['SubRating']))
        )
        return True

    def __getitem__(self, item):
        return self.results[item]

    @property
    def names(self):
        return [r['SubFileName'] for r in self.results]

    @property
    def summary(self):
        return [r.summary for r in self.results]

    def __repr__(self):
        if not self.has_results:
            return pprint.pformat(self.query_data)

        return tabulate.tabulate(
            [[i, *s] for i, s in enumerate(self.summary)],
            headers=["id", "language", "file name", "format", "rating", "size"]
        )
