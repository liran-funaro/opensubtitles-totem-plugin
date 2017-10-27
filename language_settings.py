"""
OpenSubtitles Download - Totem Plugin (see README.md)
Language Manager

Created by (unknown)
Extended by Liran Funaro <funaro@cs.technion.ac.il>
"""
from gi.repository import Gio

import gettext

gettext.textdomain("totem")

D_ = gettext.dgettext
_ = gettext.gettext

# Map of the language codes used by opensubtitles.org's API to their
# human-readable name
LANGUAGES_STR_CODE = [(D_('iso_639_3', 'Albanian'), 'sq'),
                      (D_('iso_639_3', 'Arabic'), 'ar'),
                      (D_('iso_639_3', 'Armenian'), 'hy'),
                      (D_('iso_639_3', 'Neo-Aramaic, Assyrian'), 'ay'),
                      (D_('iso_639_3', 'Basque'), 'eu'),
                      (D_('iso_639_3', 'Bosnian'), 'bs'),
                      (_('Brazilian Portuguese'), 'pb'),
                      (D_('iso_639_3', 'Bulgarian'), 'bg'),
                      (D_('iso_639_3', 'Catalan'), 'ca'),
                      (D_('iso_639_3', 'Chinese'), 'zh'),
                      (D_('iso_639_3', 'Croatian'), 'hr'),
                      (D_('iso_639_3', 'Czech'), 'cs'),
                      (D_('iso_639_3', 'Danish'), 'da'),
                      (D_('iso_639_3', 'Dutch'), 'nl'),
                      (D_('iso_639_3', 'English'), 'en'),
                      (D_('iso_639_3', 'Esperanto'), 'eo'),
                      (D_('iso_639_3', 'Estonian'), 'et'),
                      (D_('iso_639_3', 'Finnish'), 'fi'),
                      (D_('iso_639_3', 'French'), 'fr'),
                      (D_('iso_639_3', 'Galician'), 'gl'),
                      (D_('iso_639_3', 'Georgian'), 'ka'),
                      (D_('iso_639_3', 'German'), 'de'),
                      (D_('iso_639_3', 'Greek, Modern (1453-)'), 'el'),
                      (D_('iso_639_3', 'Hebrew'), 'he'),
                      (D_('iso_639_3', 'Hindi'), 'hi'),
                      (D_('iso_639_3', 'Hungarian'), 'hu'),
                      (D_('iso_639_3', 'Icelandic'), 'is'),
                      (D_('iso_639_3', 'Indonesian'), 'id'),
                      (D_('iso_639_3', 'Italian'), 'it'),
                      (D_('iso_639_3', 'Japanese'), 'ja'),
                      (D_('iso_639_3', 'Kazakh'), 'kk'),
                      (D_('iso_639_3', 'Korean'), 'ko'),
                      (D_('iso_639_3', 'Latvian'), 'lv'),
                      (D_('iso_639_3', 'Lithuanian'), 'lt'),
                      (D_('iso_639_3', 'Luxembourgish'), 'lb'),
                      (D_('iso_639_3', 'Macedonian'), 'mk'),
                      (D_('iso_639_3', 'Malay (macrolanguage)'), 'ms'),
                      (D_('iso_639_3', 'Norwegian'), 'no'),
                      (D_('iso_639_3', 'Occitan (post 1500)'), 'oc'),
                      (D_('iso_639_3', 'Persian'), 'fa'),
                      (D_('iso_639_3', 'Polish'), 'pl'),
                      (D_('iso_639_3', 'Portuguese'), 'pt'),
                      (D_('iso_639_3', 'Romanian'), 'ro'),
                      (D_('iso_639_3', 'Russian'), 'ru'),
                      (D_('iso_639_3', 'Serbian'), 'sr'),
                      (D_('iso_639_3', 'Slovak'), 'sk'),
                      (D_('iso_639_3', 'Slovenian'), 'sl'),
                      (D_('iso_639_3', 'Spanish'), 'es'),
                      (D_('iso_639_3', 'Swedish'), 'sv'),
                      (D_('iso_639_3', 'Thai'), 'th'),
                      (D_('iso_639_3', 'Turkish'), 'tr'),
                      (D_('iso_639_3', 'Ukrainian'), 'uk'),
                      (D_('iso_639_3', 'Vietnamese'), 'vi'), ]

# Map of ISO 639-1 language codes to the codes used by opensubtitles.org's API
LANGUAGES_CODE_MAP = {'sq': 'alb',
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
                      'vi': 'vie', }

LANGUAGES_MAP = {LANGUAGES_CODE_MAP[code]: lang for lang, code in LANGUAGES_STR_CODE}


class LanguageSetting(object):
    schema = 'org.gnome.totem.plugins.opensubtitles'

    def __init__(self):
        self.settings = Gio.Settings.new(self.schema)
        read_languages = self.read_setting()
        if len(read_languages) == 0:
            read_languages.append(self.local_language())
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
            return lang.split(",")
        except:
            return []

    def write_settings(self):
        self.settings.set_string('language', self.term)

    def local_language(self):
        try:
            import locale
            language_code, _ = locale.getlocale()
            return LANGUAGES_CODE_MAP[language_code.split('_')[0]]
        except (ImportError, IndexError, AttributeError, KeyError):
            return 'eng'
