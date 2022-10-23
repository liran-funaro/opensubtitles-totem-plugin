import os
import pprint
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

import tabulate

from opensubtitles_api.hash import hash_query
from opensubtitles_api.lang import iter_normalize_languages, Languages, LANGUAGES_3_TO_NATURAL

if TYPE_CHECKING:
    from opensubtitles_api import OpenSubtitlesApi

SUPPORTED_SUBTITLES_EXT = {"asc", "txt", "sub", "srt", "smi", "ssa", "ass"}


class Subtitles:
    DEFAULT_HEADERS = ("id", "language", "file name", "format", "rating", "size")

    def __init__(self, owner: 'OpenSubtitlesApi', query: 'Query', data: Dict[str, str]):
        self.owner = owner
        self.query = query
        self.data = data
        self.helper_data = {
            "id": data['IDSubtitleFile'],
            "language": LANGUAGES_3_TO_NATURAL[data['SubLanguageID']],
            "ext": data['SubFormat'],
            "format": data['SubFormat'],
            "file name": data['SubFileName'],
            "rating": data['SubRating'],
            "size": f"{int(data['SubSize']) / 1024:.2f} KB",
        }

        self._content: Optional[bytes] = None

    def __getitem__(self, item):
        if isinstance(item, (list, tuple)):
            return [self.get(k) for k in item]
        return self.get(item)

    def get(self, item):
        if item in self.helper_data:
            return self.helper_data[item]
        return self.data[item]

    @property
    def id(self):
        return self.helper_data['id']

    @property
    def ext(self):
        return self.helper_data['ext']

    def summary(self, headers=None):
        if headers is None:
            headers = self.DEFAULT_HEADERS
        return self[headers]

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

    def write_next_to_movie(self, movie_file_path: Optional[str] = None):
        if movie_file_path is None:
            movie_file_path = self.query.movie_file_path
        if movie_file_path is None:
            return
        movie_dir = os.path.dirname(movie_file_path)
        movie_file_name = os.path.splitext(os.path.basename(movie_file_path))[0]
        sub_path = os.path.join(movie_dir, f'{movie_file_name}.{self.ext}')
        content = self.content
        with open(sub_path, "wb") as f:
            f.write(content)


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
        return self.results is not None and len(self.results) > 0

    def set_response(self, response):
        if not response:
            return False

        self.response = response
        data = response.get('data', None)
        if not data:
            return False

        lang_order = defaultdict(lambda: float('inf'), **{l: i for i, l in enumerate(self.languages)})

        self.results: List[Subtitles] = sorted(
            (Subtitles(self.owner, self, r) for r in data if r['SubFormat'] in SUPPORTED_SUBTITLES_EXT),
            key=lambda x: (lang_order[x['SubLanguageID']], -float(x['SubRating']))
        )
        return True

    def __getitem__(self, item) -> Optional[Subtitles]:
        if not self.has_results:
            return None
        return self.results[item]

    def __iter__(self) -> Iterable[Subtitles]:
        if self.results is None:
            raise ValueError("No result to iterate.")
        return iter(self.results)

    def __len__(self):
        if self.results is None:
            return 0
        return len(self.results)

    @property
    def names(self):
        return [r['file name'] for r in self]

    def summary(self, headers=None):
        if not self.has_results:
            return None
        return [[i, *r.summary(headers)] for i, r in enumerate(self.results)]

    def as_table(self, headers=None, table_fmt="simple"):
        if not self.has_results:
            return tabulate.tabulate(list(self.query_data.items()), headers=("key", "value"), tablefmt=table_fmt)

        if headers is None:
            headers = Subtitles.DEFAULT_HEADERS
        return tabulate.tabulate(self.summary(headers), headers=headers, tablefmt=table_fmt)

    def __repr__(self):
        if not self.has_results:
            return pprint.pformat(self.query_data)
        return self.as_table()

    def _repr_html_(self):
        return self.as_table(table_fmt="html")
