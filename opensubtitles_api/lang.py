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
import gettext
from typing import List

gettext.textdomain("totem")
DGT = gettext.dgettext
GT = gettext.gettext

Language = str
Languages = List[Language]

# Map of ISO 639-1 language codes to the codes used by opensubtitles.org API
LANGUAGES_2_TO_3 = {
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

# Map of the language codes used by opensubtitles.org API to their human-readable name
LANGUAGES_NATURAL_TO_2 = [
    (DGT('iso_639_3', 'Albanian'), 'sq'),
    (DGT('iso_639_3', 'Arabic'), 'ar'),
    (DGT('iso_639_3', 'Armenian'), 'hy'),
    (DGT('iso_639_3', 'Neo-Aramaic, Assyrian'), 'ay'),
    (DGT('iso_639_3', 'Basque'), 'eu'),
    (DGT('iso_639_3', 'Bosnian'), 'bs'),
    (GT('Brazilian Portuguese'), 'pb'),
    (DGT('iso_639_3', 'Bulgarian'), 'bg'),
    (DGT('iso_639_3', 'Catalan'), 'ca'),
    (DGT('iso_639_3', 'Chinese'), 'zh'),
    (DGT('iso_639_3', 'Croatian'), 'hr'),
    (DGT('iso_639_3', 'Czech'), 'cs'),
    (DGT('iso_639_3', 'Danish'), 'da'),
    (DGT('iso_639_3', 'Dutch'), 'nl'),
    (DGT('iso_639_3', 'English'), 'en'),
    (DGT('iso_639_3', 'Esperanto'), 'eo'),
    (DGT('iso_639_3', 'Estonian'), 'et'),
    (DGT('iso_639_3', 'Finnish'), 'fi'),
    (DGT('iso_639_3', 'French'), 'fr'),
    (DGT('iso_639_3', 'Galician'), 'gl'),
    (DGT('iso_639_3', 'Georgian'), 'ka'),
    (DGT('iso_639_3', 'German'), 'de'),
    (DGT('iso_639_3', 'Greek, Modern (1453-)'), 'el'),
    (DGT('iso_639_3', 'Hebrew'), 'he'),
    (DGT('iso_639_3', 'Hindi'), 'hi'),
    (DGT('iso_639_3', 'Hungarian'), 'hu'),
    (DGT('iso_639_3', 'Icelandic'), 'is'),
    (DGT('iso_639_3', 'Indonesian'), 'id'),
    (DGT('iso_639_3', 'Italian'), 'it'),
    (DGT('iso_639_3', 'Japanese'), 'ja'),
    (DGT('iso_639_3', 'Kazakh'), 'kk'),
    (DGT('iso_639_3', 'Korean'), 'ko'),
    (DGT('iso_639_3', 'Latvian'), 'lv'),
    (DGT('iso_639_3', 'Lithuanian'), 'lt'),
    (DGT('iso_639_3', 'Luxembourgish'), 'lb'),
    (DGT('iso_639_3', 'Macedonian'), 'mk'),
    (DGT('iso_639_3', 'Malay (macrolanguage)'), 'ms'),
    (DGT('iso_639_3', 'Norwegian'), 'no'),
    (DGT('iso_639_3', 'Occitan (post 1500)'), 'oc'),
    (DGT('iso_639_3', 'Persian'), 'fa'),
    (DGT('iso_639_3', 'Polish'), 'pl'),
    (DGT('iso_639_3', 'Portuguese'), 'pt'),
    (DGT('iso_639_3', 'Romanian'), 'ro'),
    (DGT('iso_639_3', 'Russian'), 'ru'),
    (DGT('iso_639_3', 'Serbian'), 'sr'),
    (DGT('iso_639_3', 'Slovak'), 'sk'),
    (DGT('iso_639_3', 'Slovenian'), 'sl'),
    (DGT('iso_639_3', 'Spanish'), 'es'),
    (DGT('iso_639_3', 'Swedish'), 'sv'),
    (DGT('iso_639_3', 'Thai'), 'th'),
    (DGT('iso_639_3', 'Turkish'), 'tr'),
    (DGT('iso_639_3', 'Ukrainian'), 'uk'),
    (DGT('iso_639_3', 'Vietnamese'), 'vi'),
]

LANGUAGES_3_TO_NATURAL = {LANGUAGES_2_TO_3[code]: lang for lang, code in LANGUAGES_NATURAL_TO_2}

LANGUAGES_ALL_TO_3 = {
    **LANGUAGES_2_TO_3,
    **{k: k for k in LANGUAGES_2_TO_3.values()},
    **{lang.lower(): LANGUAGES_2_TO_3[code] for lang, code in LANGUAGES_NATURAL_TO_2}
}


def normalize_language(language: Language):
    return LANGUAGES_ALL_TO_3.get(language.lower())


def iter_normalize_languages(languages: Languages):
    return map(normalize_language, languages)
