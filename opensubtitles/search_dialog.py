"""
OpenSubtitles Download - Totem Plugin (see README.md)
Search Dialog Box

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
import logging
import os
from typing import List, TYPE_CHECKING

from gi.repository import Gdk, Gtk, Pango

from opensubtitles.api.lang import GT, LANGUAGES_2_TO_3, LANGUAGES_NATURAL_TO_2

if TYPE_CHECKING:
    from opensubtitles import OpenSubtitles


class SearchDialog(object):
    def __init__(self, plugin_object: 'OpenSubtitles'):
        """
        :param plugin_object: Should implement:
            - on_close_dialog()
            - on_language_change(index, language)
            - on_search_request()
            - on_download_request(selected_dict)
        """
        self.plugin_object: 'OpenSubtitles' = plugin_object

        self.logger = logging.getLogger("opensubtitles-dialog")

        ui_path = os.path.join(os.path.dirname(__file__), "opensubtitles.ui")
        builder = Gtk.Builder.new_from_file(ui_path)

        self.languages = [
            builder.get_object('main_language'),
            builder.get_object('alt_language')
        ]
        self.language_model = builder.get_object('language_model')
        self.subtitles_dialog = builder.get_object('subtitles_dialog')
        self.progress_bar = builder.get_object('progress_bar')
        self.subtitle_treeview = builder.get_object('subtitle_treeview')
        self.subtitle_model = builder.get_object('subtitle_model')
        self.find_button = builder.get_object('find_button')
        self.apply_button = builder.get_object('apply_button')
        self.close_button = builder.get_object('close_button')

        self.setup_languages()
        self.setup_treeview()
        self.setup_events()

        self.subtitles_dialog.set_transient_for(self.totem_object.get_main_window())
        self.subtitles_dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.clear()
        self.progress_reset()

    @property
    def totem_object(self):
        if self.plugin_object is not None:
            return self.plugin_object.totem
        return None

    ########################################################
    # API
    ########################################################

    def show(self):
        try:
            self.subtitles_dialog.show_all()
        except Exception as e:
            self.logger.exception("Failed show: %s", e)

    def close(self):
        try:
            self.set_cursor(None)
            self.subtitles_dialog.destroy()
        except Exception as e:
            self.logger.exception("Failed close: %s", e)

    def disable_buttons(self):
        try:
            self.find_button.set_sensitive(False)
            self.apply_button.set_sensitive(False)
            self.subtitle_treeview.set_sensitive(False)
        except Exception as e:
            self.logger.exception("Failed disable_buttons: %s", e)

    def enable_buttons(self):
        try:
            self.find_button.set_sensitive(True)
            self.apply_button.set_sensitive(False)
            self.subtitle_treeview.set_sensitive(True)
        except Exception as e:
            self.logger.exception("Failed enable_buttons: %s", e)

    def clear(self):
        try:
            self.subtitle_model.clear()
        except Exception as e:
            self.logger.exception("Failed clear: %s", e)

    def populate_treeview(self, item_list: List):
        try:
            self.subtitle_model.clear()
            for item in item_list:
                self.subtitle_model.append(item)
            self.set_cursor(None)
        except Exception as e:
            self.logger.exception("Failed populate_treeview: %s", e)

    def set_progress_message(self, msg):
        if not msg:
            msg = u' '

        try:
            self.progress_bar.set_text(GT(msg))
        except Exception as e:
            self.logger.exception("Failed set_progress_message: %s", e)

    def start_loading_animation(self):
        try:
            self.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        except Exception as e:
            self.logger.exception("Failed start_loading_animation: %s", e)

    def stop_loading_animation(self):
        try:
            self.set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        except Exception as e:
            self.logger.exception("Failed stop_loading_animation: %s", e)

    def progress_pulse(self):
        try:
            self.progress_bar.pulse()
        except Exception as e:
            self.logger.exception("Failed progress_pulse: %s", e)

    def progress_reset(self):
        try:
            self.progress_bar.set_fraction(0.0)
        except Exception as e:
            self.logger.exception("Failed progress_reset: %s", e)

    ########################################################
    # Helpers
    ########################################################

    def set_cursor(self, cursor=None):
        window = self.subtitles_dialog.get_window()
        if window is None:
            return
        window.set_cursor(cursor)

    ########################################################
    # Initialization
    ########################################################

    def setup_languages(self):
        """ Set up and populate the languages combobox """
        sorted_languages = Gtk.TreeModelSort(model=self.language_model)
        sorted_languages.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        renderer = Gtk.CellRendererText()
        for l_box in self.languages:
            l_box.set_model(sorted_languages)
            l_box.pack_start(renderer, True)
            l_box.add_attribute(renderer, 'text', 0)

        for lang in LANGUAGES_NATURAL_TO_2:
            lang_iter = self.language_model.append(lang)
            i = self.plugin_object.language.language_index(lang[1])
            if i is not None:
                success, parent_iter = sorted_languages.convert_child_iter_to_iter(lang_iter)
                if success:
                    self.languages[i].set_active_iter(parent_iter)

    def setup_treeview(self):
        """ Set up the results treeview """
        renderer = Gtk.CellRendererText()
        self.subtitle_treeview.set_model(self.subtitle_model)
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)

        columns = [(u"Language", False, False),
                   (u"Subtitles", True, True),
                   # This is the file-type of the subtitle file detected
                   (u"Format", False, False),
                   # This is a rating of the quality of the subtitle
                   (u"Rating", False, False)]

        for i, (label, resize, expand) in enumerate(columns):
            column = Gtk.TreeViewColumn(GT(label), renderer, text=i)
            column.set_resizable(resize)
            column.set_expand(expand)
            self.subtitle_treeview.append_column(column)

    def setup_events(self):
        """ Set up signals (connect the callbacks) """
        self.apply_button.connect('clicked', self.__on_apply_clicked)
        self.find_button.connect('clicked', self.__on_find_clicked)

        self.close_button.connect('clicked', self.__on_close_clicked)
        self.subtitles_dialog.connect('delete-event', self.__on_close_clicked)

        for i, l_box in enumerate(self.languages):
            l_box.connect('changed', self.__on_language_changed, i)

        self.subtitles_dialog.connect('key-press-event',
                                      self.__on_window__key_press_event)
        self.subtitle_treeview.get_selection().connect('changed',
                                                       self.__on_treeview__row_change)
        self.subtitle_treeview.connect('row-activated',
                                       self.__on_treeview__row_activate)

    ##########################################################
    # Callbacks Handlers
    ##########################################################

    def __on_close_dialog(self):
        self.close()

    def __on_close_clicked(self, *_args):
        self.__on_close_dialog()

    def __on_window__key_press_event(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.__on_close_dialog()
            return True
        return False

    def __on_treeview__row_change(self, selection):
        if selection.count_selected_rows() > 0:
            self.apply_button.set_sensitive(True)
        else:
            self.apply_button.set_sensitive(False)

    def __on_find_clicked(self, _):
        self.plugin_object.on_search_request()

    def __on_download_request(self):
        model, rows = self.subtitle_treeview.get_selection().get_selected_rows()
        if not rows:
            print('Warning, nothing is really selected')
            return

        subtitle_iter = model.get_iter(rows[0])
        columns = ['language', 'name', 'format', 'rating', 'id-sub', 'size']
        selected_dict = {c: model.get_value(subtitle_iter, i) for i, c in enumerate(columns)}
        self.plugin_object.on_download_request(selected_dict)

    def __on_treeview__row_activate(self, _tree_path, _column, _data):
        self.__on_download_request()

    def __on_apply_clicked(self, _):
        self.__on_download_request()

    def __on_language_changed(self, combobox, index):
        combo_iter = combobox.get_active_iter()
        combo_model = combobox.get_model()
        cur_lang = LANGUAGES_2_TO_3[combo_model.get_value(combo_iter, 1)]
        self.plugin_object.on_language_change(index, cur_lang)
