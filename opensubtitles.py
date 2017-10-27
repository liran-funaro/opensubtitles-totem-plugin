"""
OpenSubtitles Download - Totem Plugin (see README.md)

Created by (unknown)
Extended by Liran Funaro <funaro@cs.technion.ac.il>
"""
import os
import pprint
import threading
from ast import literal_eval
from collections import defaultdict
import time
import datetime

from gi.repository import GLib, GObject
from gi.repository import Peas, Gtk, Gdk
from gi.repository import Gio, Pango, Totem

from language_settings import LanguageSetting, LANGUAGES_MAP
from opensubtitles_api import OpenSubtitlesApi, SUBTITLES_EXT
from search_dialog import SearchDialog

import gettext
import logging
import logging.handlers

def start_file_logging():
    handler = logging.FileHandler("/tmp/totem.log", 'w+')

    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    logger = logging.getLogger("totem")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = start_file_logging()

gettext.textdomain("totem")
D_ = gettext.dgettext
_ = gettext.gettext


class OpenSubtitles(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'OpenSubtitles'

    object = GObject.Property(type=GObject.Object)
    progress_interval = 350
    cache_lifetime_days = 1
    opensubtitles_user_agent = 'Totem'

    def __init__(self):
        GObject.Object.__init__(self)

        self.totem_plugin = None
        self.language = LanguageSetting()

    #####################################################################
    # totem.Plugin methods
    #####################################################################

    def do_activate(self):
        """
        Called when the plugin is activated.
        Here the sidebar page is initialized (set up the treeview, connect
        the callbacks, ...) and added to totem.
        """
        self.totem_plugin = self.object

        # Obtain the ServerProxy and init the model
        self.api = OpenSubtitlesApi(self.opensubtitles_user_agent)

        # Name of the movie file which the most-recently-downloaded subtitles
        # are related to.
        self.mrl_filename = None

        self.totem_plugin.connect('file-opened', self.__on_totem__file_opened)
        self.totem_plugin.connect('file-closed', self.__on_totem__file_closed)

        self.dialog = SearchDialog.create_fake()
        self.dialog_lock = threading.RLock()

        self.append_menu()

        enable_dialog = self.totem_plugin.is_playing() and self.is_support_subtitles()
        self.dialog_action.set_enabled(enable_dialog)

    def do_deactivate(self):
        self.close_dialog()
        self.delete_menu()

    #####################################################################
    # UI related code
    #####################################################################

    def open_dialog(self, action, params):
        if not self.is_support_subtitles():
            return

        with self.dialog_lock:
            self.close_dialog()
            self.dialog = SearchDialog(self, self.totem_plugin, self.language.list)

        self.dialog.show()
        self.submit_search_request(cached=True, feeling_lucky=False)

    def close_dialog(self):
        with self.dialog_lock:
            self.dialog.close()
            self.dialog = SearchDialog.create_fake()

    def append_menu(self):
        self.dialog_action = Gio.SimpleAction.new("opensubtitles", None)
        self.dialog_action.connect('activate', self.open_dialog)
        self.totem_plugin.add_action(self.dialog_action)
        self.totem_plugin.set_accels_for_action("app.opensubtitles",
                                                ["<Primary><Shift>s"])

        menu = self.totem_plugin.get_menu_section("subtitle-download-placeholder")
        menu.append(_(u'_Search OpenSubtitles...'), "app.opensubtitles")

        self._set_subtitle_action = Gio.SimpleAction.new("set-opensubtitles",
                                                         GLib.VariantType.new("as"))
        self._set_subtitle_action.connect('activate', self.__on_menu_set_subtitle)
        self.totem_plugin.add_action(self._set_subtitle_action)

        self.subs_menu = Gio.Menu()
        menu.append_section(None, self.subs_menu)

    def delete_menu(self):
        self.totem_plugin.empty_menu_section("subtitle-download-placeholder")

    def enable(self):
        self.dialog_action.set_enabled(True)
        self.dialog.clear()
        self.dialog.enable_buttons()

    def disable(self):
        self.dialog_action.set_enabled(False)
        self.mrl_filename = None
        self.dialog.clear()
        self.dialog.disable_buttons()

    #####################################################################
    # Subtitles Support
    #####################################################################

    def is_support_subtitles(self, mrl=None):
        if not mrl:
            mrl = self.totem_plugin.get_current_mrl()
        return self.check_supported_scheme(mrl) and not self.check_is_audio(mrl)

    def check_supported_scheme(self, mrl):
        current_file = Gio.file_new_for_uri(mrl)
        scheme = current_file.get_uri_scheme()

        unsupported_scheme = ['dvd', 'http', 'dvb', 'vcd']
        return scheme not in unsupported_scheme

    def check_is_audio(self, mrl):
        # FIXME need to use something else here
        # I think we must use video widget metadata but I don't found a way
        # to get this info from python
        return Gio.content_type_guess(mrl, '')[0].split('/')[0] == 'audio'

    ##########################################################
    # Callbacks Handlers
    ##########################################################

    def __on_totem__file_opened(self, _, new_mrl):
        if self.mrl_filename == new_mrl:
            # Check we're not re-opening the same file; if we are, don't
            # clear anything. This happens when we re-load the file with a
            # new set of subtitles, for example
            return

        self.mrl_filename = new_mrl
        # Check if allows subtitles
        if self.is_support_subtitles(new_mrl):
            self.enable()
            feeling_lucky = not self.is_subtitle_exists()
            self.submit_search_request(cached=True, feeling_lucky=feeling_lucky)
        else:
            self.disable()

    def __on_totem__file_closed(self, _):
        self.disable()

    def __on_menu_set_subtitle(self, action, params):
        params = {p: params[i] for i, p in enumerate(['name', 'format', 'id'])}
        self.submit_download_request(params)

    #####################################################################
    # Dialog Handlers
    #####################################################################

    def on_close_dialog(self):
        with self.dialog_lock:
            self.dialog = SearchDialog.create_fake()

    def on_language_change(self, index, language):
        logger.info("Write language %s to index %s", language, index)
        self.language.update_language(index, language)

    def on_search_request(self):
        self.submit_search_request(cached=False, feeling_lucky=False)

    def on_download_request(self, selected_dict):
        self.submit_download_request(selected_dict)

    #####################################################################
    # Subtitles lookup and download
    #####################################################################

    def submit_search_request(self, cached=False, feeling_lucky=False):
        self.submit_background_work(u'Searching subtitles…', self.search_subtitles, [cached],
                                    self.handle_search_results, [feeling_lucky])

    def submit_download_request(self, selected_dict):
        self.submit_background_work(u'Downloading subtitles…', self.download_subtitles,
                                    [selected_dict], self.handle_downloaded_subtitle)

    def search_subtitles(self, cached=False):
        self.clear_cache()

        if cached:
            results = self.read_cached_search_results()
            if results:
                return results

        languages = self.language.term
        movie_file_path = self.movie_file().get_path()
        return self.api.search_subtitles(languages, movie_file_path)

    def download_subtitles(self, selected_dict):
        self.clear_cache()

        subtitle_name = selected_dict['name']
        subtitle_format = selected_dict['format']

        # Lookup the subtitle in the cache
        cached_subtitle = self.cache_file(subtitle_name)
        content = self._read_file(cached_subtitle)
        if not content:
            subtitle_id = selected_dict['id']
            content = self.api.download_subtitles(subtitle_id)
        return self.save_subtitles(content, subtitle_name, subtitle_format)

    def handle_search_results(self, results, feeling_lucky=False):
        if not results:
            return

        self.write_cached_search_results(results)

        lang_list = self.language.list
        lang_order = {l: i for i, l in enumerate(lang_list)}
        lang_order = defaultdict(lambda: float('inf'), **lang_order)

        results = list(sorted([r for r in results if r['SubFormat'] in SUBTITLES_EXT],
                              key=lambda x: (lang_order[x['SubLanguageID']], -float(x['SubRating']))))
        self._populate_submenu(results)
        self._populate_treeview(results)

        if feeling_lucky and len(results) > 0:
            r = results[0]
            selected_dict = {'name': r['SubFileName'],
                             'format': r['SubFormat'],
                             'id': r['IDSubtitleFile']}
            self.submit_download_request(selected_dict)

    def _populate_treeview(self, results):
        item_list = []
        for r in results:
            item = [
                LANGUAGES_MAP[r['SubLanguageID']],
                r['SubFileName'],
                r['SubFormat'],
                r['SubRating'],
                r['IDSubtitleFile'],
                r['SubSize'],
            ]
            item_list.append(item)

        self.dialog.populate_treeview(item_list)

    def _populate_submenu(self, results):
        self.subs_menu.remove_all()
        for r in results:
            lang_name = LANGUAGES_MAP[r['SubLanguageID']]
            file_name = r['SubFileName']
            menu_title = u'\t%s: %s' % (lang_name, file_name)
            menu_item = Gio.MenuItem.new(_(menu_title), "app.set-opensubtitles")

            data = GLib.Variant('as', [
                r['SubFileName'],
                r['SubFormat'],
                r['IDSubtitleFile']
            ])
            menu_item.set_action_and_target_value("app.set-opensubtitles", data)
            self.subs_menu.append_item(menu_item)

    def save_subtitles(self, subtitles, name, extension):
        if not subtitles or not name or not extension:
            return

        # Delete all previous cached subtitle for this file
        for ext in SUBTITLES_EXT:
            # In the cache dir and in the movie dir
            try:
                old_subtitle_file = self.subtitle_file(ext, cache=False)
                old_subtitle_file.delete(None)
            except:
                pass

        save_to_files = [
            self.cache_file(name),
            self.subtitle_file(extension, cache=False),
            self.subtitle_file(extension, cache=True)
        ]

        for i, f in enumerate(save_to_files):
            try:
                self._write_file(f, subtitles)
                # Stop if manage to save in the movie folder
                if i > 0:
                    return f.get_uri()
            except Exception as e:
                print(e)
                continue

        raise Exception("Cannot save subtitle")

    def handle_downloaded_subtitle(self, subtitle_uri):
        if not subtitle_uri:
            return

        self.close_dialog()
        self.totem_plugin.set_current_subtitle(subtitle_uri)

    #####################################################################
    # Filesystem helpers
    #####################################################################

    def cached_search_results_file(self):
        return self.cache_file("%s.%s" % (self.movie_name(), "opensubtitles"))

    def read_cached_search_results(self):
        result_cache = self.cached_search_results_file()
        data = self._read_file(result_cache)
        if not data:
            return
        try:
            data = str(data, 'utf-8')
            return literal_eval(data)
        except:
            return

    def write_cached_search_results(self, results):
        result_cache = self.cached_search_results_file()
        file_content = pprint.pformat(results).encode('utf-8')
        self._write_file(result_cache, file_content)

    def _write_file(self, file_obj, content):
        flags = Gio.FileCreateFlags.REPLACE_DESTINATION
        stream = file_obj.replace('', False, flags, None)
        try:
            stream.write(content, None)
        finally:
            stream.close()

    def _read_file(self, file_obj):
        if not file_obj.query_exists():
            return None
        _, content, _ = file_obj.load_contents()
        if not content:
            return None
        return content

    def movie_name(self):
        subtitle_file = Gio.file_new_for_uri(self.mrl_filename)
        return subtitle_file.get_basename().rpartition('.')[0]

    def movie_file(self):
        return Gio.file_new_for_uri(self.mrl_filename)

    def subtitle_path(self, ext, cache=False):
        movie_name = self.movie_name()
        if cache:
            dir_path = self._cache_subtitles_dir()
        else:
            dir_path = self._movie_dir()
        return os.path.join(dir_path, "%s.%s" % (movie_name, ext))

    def subtitle_file(self, ext, cache=False):
        return Gio.file_new_for_path(self.subtitle_path(ext, cache))

    def is_subtitle_exists(self):
        return any(self.subtitle_file(ext, cache=False).query_exists() for ext in SUBTITLES_EXT)

    def cache_file(self, filename):
        dir_path = self._cache_subtitles_dir()
        try:
            directory = Gio.file_new_for_path(dir_path)
            directory.make_directory_with_parents(None)
        except:
            pass
        file_path = os.path.join(dir_path, filename)
        return Gio.file_new_for_path(file_path)

    def _cache_subtitles_dir(self):
        bpath = GLib.get_user_cache_dir()
        ret = os.path.join(bpath, 'totem', 'subtitles')
        GLib.mkdir_with_parents(ret, 0o777)
        return ret

    def _movie_dir(self):
        directory = Gio.file_new_for_uri(self.mrl_filename)
        parent = directory.get_parent()
        return parent.get_path()

    def clear_cache(self):
        dir_path = self._cache_subtitles_dir()
        directory = Gio.file_new_for_path(dir_path)
        children = directory.enumerate_children("time::modified,standard::name",
                                             Gio.FileQueryInfoFlags.NONE, None)

        seconds_per_day = float(60*60*24)
        current_time = datetime.datetime.fromtimestamp(time.time())
        for d in children:
            modified = datetime.datetime.fromtimestamp(
                d.get_attribute_uint64("time::modified")
            )
            days = (current_time - modified).total_seconds() / seconds_per_day
            if days > self.cache_lifetime_days:
                print("Delete", d.get_name())
                path = os.path.join(dir_path, d.get_name())
                Gio.file_new_for_path(path).delete(None)

    ########################################################
    # Background Work
    ########################################################

    def submit_background_work(self, init_message, work_func, work_args,
                               callback_func, callback_args=[]):
        work_tracker = {"status": False,
                        "callback": (callback_func, callback_args)}
        self.init_progress(work_tracker, init_message)
        threading.Thread(target=self.__background_work,
                         args=[work_tracker, work_func, *work_args]).start()

    def __background_work(self, work_tracker, work_func, *args):
        result = None
        message = None

        try:
            result = work_func(*args)
            message = "Success (%s)" % len(result)
        except Exception as e:
            logger.exception("Error: %s", e)
            result = None
            message = str(e)
        finally:
            work_tracker["result"] = result
            work_tracker["message"] = message
            work_tracker["status"] = True

    def init_progress(self, work_tracker, message):
        try:
            self.dialog.set_progress_message(message)
            self.dialog.disable_buttons()
            self.dialog.start_loading_animation()
            self.progress(work_tracker)
            GLib.timeout_add(self.progress_interval, self.progress, work_tracker)
        except Exception as e:
            logger.exception("Error: %s", e)
            self.dialog.set_progress_message(str(e))

    def progress(self, work_tracker):
        self.dialog.progress_pulse()
        if not work_tracker["status"]:
            return True

        callback, args = work_tracker["callback"]
        result = work_tracker["result"]
        message = work_tracker["message"]

        try:
            callback(result, *args)
        except Exception as e:
            logger.exception("Error: %s", e)
            if not message:
                message = str(e)
            else:
                message = "%s, but %s" % (message, str(e))

        self.dialog.enable_buttons()
        self.dialog.stop_loading_animation()
        self.dialog.set_progress_message(message)
        self.dialog.progress_reset()
        return False
