"""
OpenSubtitles Download - Totem Plugin (see README.md)

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
import os
import threading
from typing import Dict, Optional

from gi.repository import Gio, GLib, GObject, Peas

from opensubtitles.api import OpenSubtitlesApi
from opensubtitles.api.results import SUPPORTED_SUBTITLES_EXT
from opensubtitles.language_settings import LanguageSetting
from opensubtitles.plugin_logger import plugin_logger
from opensubtitles.search_dialog import SearchDialog


def totem_cache_path():
    cache_path = GLib.get_user_cache_dir()
    ret = os.path.join(cache_path, 'totem')
    GLib.mkdir_with_parents(ret, 0o777)
    return ret


class OpenSubtitles(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'OpenSubtitles'

    object: GObject.Object = GObject.Property(type=GObject.Object)
    PROGRESS_INTERVAL = 350
    USER_AGENT = 'Totem'

    def __init__(self):
        GObject.Object.__init__(self)

        self.language = LanguageSetting()
        self.dialog_lock = threading.RLock()

        # Future members
        self.totem: Optional[GObject.Object] = None
        self.api: Optional[OpenSubtitlesApi] = None
        self.dialog: Optional[SearchDialog] = None
        self.dialog_action = None
        self.subs_menu = None
        self._set_subtitle_action = None

        # Name of the movie file which the most-recently-downloaded subtitles
        # are related to.
        self.mrl_filename = None

    #####################################################################
    # totem.Plugin methods
    #####################################################################

    def do_activate(self):
        """
        Called when the plugin is activated.
        Here the sidebar page is initialized (set up the treeview, connect
        the callbacks, ...) and added to totem.
        """
        self.totem: GObject.Object = self.object
        self.api: OpenSubtitlesApi = OpenSubtitlesApi(self.USER_AGENT, cache_dir=totem_cache_path())

        self.totem.connect('file-opened', self.__on_totem__file_opened)
        self.totem.connect('file-closed', self.__on_totem__file_closed)

        self.dialog = SearchDialog(self)

        self.dialog_action = Gio.SimpleAction.new("opensubtitles", None)
        self.dialog_action.connect('activate', self.open_dialog)
        self.totem.add_action(self.dialog_action)
        self.totem.set_accels_for_action("app.opensubtitles",
                                         ["<Primary><Shift>s"])

        # Append menu item
        menu = self.totem.get_menu_section("subtitle-download-placeholder")
        menu.append(gettext.gettext(u'_Search OpenSubtitles...'), "app.opensubtitles")

        self._set_subtitle_action = Gio.SimpleAction.new("set-opensubtitles",
                                                         GLib.VariantType.new("as"))
        self._set_subtitle_action.connect('activate', self.__on_menu_set_subtitle)
        self.totem.add_action(self._set_subtitle_action)

        self.subs_menu = Gio.Menu()
        menu.append_section(None, self.subs_menu)

        # Enable dialog
        enable_dialog = self.totem.is_playing() and self.is_support_subtitles()
        self.dialog_action.set_enabled(enable_dialog)

    def do_deactivate(self):
        self.close_dialog()

        # Cleanup menu
        self.totem.empty_menu_section("subtitle-download-placeholder")

    #####################################################################
    # UI related code
    #####################################################################

    def open_dialog(self, _action, _params):
        if not self.is_support_subtitles():
            return

        with self.dialog_lock:
            self.close_dialog()
            self.dialog = SearchDialog(self)

        self.dialog.show()
        self.submit_search_request()

    def close_dialog(self):
        with self.dialog_lock:
            self.dialog.close()
            self.dialog = SearchDialog(self)

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
            mrl = self.totem.get_current_mrl()
        return self.check_supported_scheme(mrl) and not self.check_is_audio(mrl)

    @staticmethod
    def check_supported_scheme(mrl):
        current_file = Gio.file_new_for_uri(mrl)
        scheme = current_file.get_uri_scheme()

        unsupported_scheme = ['dvd', 'http', 'dvb', 'vcd']
        return scheme not in unsupported_scheme

    @staticmethod
    def check_is_audio(mrl):
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
            self.submit_search_request(feeling_lucky=feeling_lucky)
        else:
            self.disable()

    def __on_totem__file_closed(self, _):
        self.disable()

    def __on_menu_set_subtitle(self, _action, params):
        params = {p: params[i] for i, p in enumerate(['format', 'id'])}
        self.submit_download_request(params)

    #####################################################################
    # Dialog Handlers
    #####################################################################

    def on_language_change(self, index, language):
        plugin_logger.info("Write language %s to index %s", language, index)
        self.language.update_language(index, language)

    def on_search_request(self):
        self.submit_search_request(refresh_cache=True)

    def on_download_request(self, selected_dict):
        self.submit_download_request(selected_dict)

    #####################################################################
    # Subtitles lookup and download
    #####################################################################

    def submit_search_request(self, refresh_cache: bool = False, feeling_lucky: bool = False):
        self.submit_background_work(u'Searching subtitles...', self.search_subtitles, [refresh_cache],
                                    self.handle_search_results, [feeling_lucky])

    def submit_download_request(self, selected_dict):
        self.submit_background_work(u'Downloading subtitles...', self.download_subtitles,
                                    [selected_dict], self.handle_downloaded_subtitle)

    def search_subtitles(self, refresh_cache: bool):
        movie_file_path = self.movie_file().get_path()
        return self.api.search_subtitles(self.language.list, movie_file_path, refresh_cache=refresh_cache)

    def download_subtitles(self, selected_dict: Dict[str, str]):
        subtitle_format = selected_dict['format']
        content = self.api.download_subtitles(selected_dict['id'], subtitle_format)
        return self.save_subtitles(content, subtitle_format)

    def handle_search_results(self, results: Optional[api.Query], feeling_lucky=False):
        if not results:
            return

        self._populate_submenu(results)
        self._populate_treeview(results)

        if feeling_lucky and results.has_results:
            r = results[0]
            self.submit_download_request({'format': r.ext, 'id': r.id})

    def _populate_treeview(self, results: api.Query):
        item_list = []
        for r in results:
            item = r.summary(["language", "file name", "ext", "rating", "id", "size"])
            item_list.append(item)
        self.dialog.populate_treeview(item_list)

    def _populate_submenu(self, results: api.Query):
        self.subs_menu.remove_all()
        for r in results:
            lang_name = r['language']
            file_name = r['file name']
            menu_title = u'\t%s: %s' % (lang_name, file_name)
            menu_item = Gio.MenuItem.new(gettext.gettext(menu_title), "app.set-opensubtitles")

            menu_item.set_action_and_target_value("app.set-opensubtitles", GLib.Variant('as', [r.ext, r.id]))
            self.subs_menu.append_item(menu_item)

    def get_existing_subtitles_files(self):
        for ext in SUPPORTED_SUBTITLES_EXT:
            try:
                subtitle_file = self.subtitle_file(ext)
                if subtitle_file.query_exists():
                    yield subtitle_file
            except Exception as e:
                plugin_logger.exception(e)

    def save_subtitles(self, subtitles, extension):
        if not subtitles or not extension:
            return

        # Delete all previous subtitle for this file in the movie directory
        for subtitle_file in self.get_existing_subtitles_files():
            try:
                subtitle_file.delete()
            except Exception as e:
                plugin_logger.exception(e)

        try:
            f = self.subtitle_file(extension)
            self._write_file(self.subtitle_file(extension), subtitles)
            return f.get_uri()
        except Exception as e:
            plugin_logger.exception("Failed to save subtitles file: %s", e)

        raise Exception("Cannot save subtitle")

    def handle_downloaded_subtitle(self, subtitle_uri):
        if not subtitle_uri:
            return

        self.close_dialog()
        self.totem.set_current_subtitle(subtitle_uri)

    #####################################################################
    # Filesystem helpers
    #####################################################################

    @staticmethod
    def _write_file(file_obj, content):
        flags = Gio.FileCreateFlags.REPLACE_DESTINATION
        stream = file_obj.replace('', False, flags, None)
        try:
            stream.write(content, None)
        finally:
            stream.close()

    @staticmethod
    def _read_file(file_obj):
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

    def subtitle_path(self, ext):
        return os.path.join(self._movie_dir(), f"{self.movie_name()}.{ext}")

    def subtitle_file(self, ext) -> Gio.File:
        return Gio.file_new_for_path(self.subtitle_path(ext))

    def is_subtitle_exists(self):
        return any(self.subtitle_file(ext).query_exists() for ext in SUPPORTED_SUBTITLES_EXT)

    def _movie_dir(self):
        directory = Gio.file_new_for_uri(self.mrl_filename)
        parent = directory.get_parent()
        return parent.get_path()

    ########################################################
    # Background Work
    ########################################################

    def submit_background_work(self, init_message, work_func, work_args,
                               callback_func, callback_args=()):
        work_tracker = {"status": False, "callback": (callback_func, callback_args)}
        self.init_progress(work_tracker, init_message)
        args = [work_tracker, work_func]
        args.extend(work_args)
        threading.Thread(target=self.__background_work, args=args).start()

    @staticmethod
    def __background_work(work_tracker, work_func, *args):
        result = None
        message = None

        try:
            result = work_func(*args)
            message = "Success (%s)" % len(result)
        except Exception as e:
            plugin_logger.exception(e)
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
            GLib.timeout_add(self.PROGRESS_INTERVAL, self.progress, work_tracker)
        except Exception as e:
            plugin_logger.exception(e)
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
            plugin_logger.exception(e)
            if not message:
                message = str(e)
            else:
                message = "%s, but %s" % (message, str(e))

        self.dialog.enable_buttons()
        self.dialog.stop_loading_animation()
        self.dialog.set_progress_message(message)
        self.dialog.progress_reset()
        return False
