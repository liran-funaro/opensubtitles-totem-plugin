"""
OpenSubtitles Download - Totem Plugin (see README.md)
Language Manager

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
import locale

from gi.repository import Gio

from opensubtitles_api import LANGUAGES_CODE_MAP
from plugin_logger import plugin_logger

gettext.textdomain("totem")
DGT = gettext.dgettext
GT = gettext.gettext

# Map of the language codes used by opensubtitles.org API to their human-readable name
LANGUAGES_STR_CODE = [
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
LANGUAGES_MAP = {LANGUAGES_CODE_MAP[code]: lang for lang, code in LANGUAGES_STR_CODE}


def local_language():
    try:
        language_code, _ = locale.getlocale()
        return LANGUAGES_CODE_MAP[language_code.split('_')[0]]
    except (ImportError, IndexError, AttributeError, KeyError) as e:
        plugin_logger.exception(e)
        return 'eng'


class LanguageSetting(object):
    SCHEMA = 'org.gnome.totem.plugins.opensubtitles'

    def __init__(self):
        self.settings = Gio.Settings.new(self.SCHEMA)
        read_languages = self.read_setting()
        if len(read_languages) == 0:
            read_languages.append(local_language())
        self.__languages = []
        self.set_languages(read_languages)

    def set_languages(self, languages):
        self.__languages = [l.strip() for l in languages if l.strip()]
        self.write_settings()

    def update_language(self, index, language):
        language = language.strip()
        if not language:
            return

        if index < len(self.__languages):
            self.__languages[index] = language
        else:
            self.__languages.append(language)

        self.write_settings()

    @property
    def list(self):
        return list(self.__languages)

    @property
    def term(self):
        return ",".join(self.__languages)

    def __repr__(self):
        return self.term

    def read_setting(self):
        try:
            lang = self.settings.get_string('language')
            return [l.strip() for l in lang.split(",")]
        except:
            return []

    def write_settings(self):
        self.settings.set_string('language', self.term)
