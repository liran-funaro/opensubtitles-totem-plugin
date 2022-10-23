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
import locale
import logging

from gi.repository import Gio

from opensubtitles_api.lang import Language, Languages, normalize_language
from plugin_logger import plugin_logger


def local_language():
    try:
        language_code, _ = locale.getlocale()
        return normalize_language(language_code.split('_')[0])
    except (ImportError, IndexError, AttributeError, KeyError) as e:
        plugin_logger.exception(e)
        return 'eng'


class LanguageSetting(object):
    SCHEMA = 'org.gnome.totem.plugins.opensubtitles'

    def __init__(self):
        self.logger = logging.getLogger("opensubtitles-language")
        self.settings = Gio.Settings.new(self.SCHEMA)
        self.__languages = []

        read_languages = self.read_setting()
        if len(read_languages) == 0:
            read_languages.append(local_language())
        self.set_languages(read_languages)

    def set_languages(self, languages):
        self.__languages = [l.strip() for l in languages if l.strip()]
        self.write_settings()

    def __getitem__(self, item):
        return self.__languages[item]

    def language_index(self, language: Language):
        try:
            return self.__languages.index(normalize_language(language))
        except ValueError:
            return None

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
    def list(self) -> Languages:
        return list(self.__languages)

    @property
    def term(self):
        return ",".join(self.__languages)

    def __repr__(self):
        return self.term

    def read_setting(self):
        try:
            language = self.settings.get_string('language')
            return [lang.strip() for lang in language.split(",")]
        except Exception as e:
            self.logger.error("Failed reading language settings: %s", e)
            return []

    def write_settings(self):
        self.settings.set_string('language', self.term)
