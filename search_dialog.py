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
from gi.repository import Peas, Gtk, Gdk
from gi.repository import Gio, Pango, Totem

from language_settings import LANGUAGES_STR_CODE, LANGUAGES_CODE_MAP, GT


class SearchDialog(object):
    def __init__(self, plugin_object, totem_object, pre_selected_languages=()):
        """
        :param plugin_object: Should implement:
            - on_close_dialog()
            - on_language_change(index, language)
            - on_search_request()
            - on_download_request(selected_dict)
        :param totem_object:
        :param pre_selected_languages:
        """
        self.plugin_object = plugin_object
        self.totem_object = totem_object

        # Future members
        self.languages = None
        self.language_model = None
        self.dialog = None
        self.progress = None
        self.tree_view = None
        self.list_store = None
        self.find_button = None
        self.apply_button = None
        self.close_button = None

        # Otherwise it is a fake dialog
        if not self.is_fake:
            self.build()
            self.setup_languages(pre_selected_languages)
            self.setup_treeview()
            self.setup_events()

            self.dialog.set_transient_for(self.totem_object.get_main_window())
            self.dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

            self.clear()
            self.progress_reset()

    @classmethod
    def create_fake(cls):
        return cls(None, None, [])

    @property
    def is_fake(self):
        return not self.plugin_object or not self.totem_object

    ########################################################
    # API
    ########################################################

    def show(self):
        if self.is_fake:
            return
        try:
            self.dialog.show_all()
        except:
            pass

    def close(self):
        if self.is_fake:
            return
        try:
            self.dialog.get_window().set_cursor(None)
            self.dialog.destroy()
        except:
            pass

    def disable_buttons(self):
        if self.is_fake:
            return
        try:
            self.find_button.set_sensitive(False)
            self.apply_button.set_sensitive(False)
            self.tree_view.set_sensitive(False)
        except:
            pass

    def enable_buttons(self):
        if self.is_fake:
            return
        try:
            self.find_button.set_sensitive(True)
            self.apply_button.set_sensitive(False)
            self.tree_view.set_sensitive(True)
        except:
            pass

    def clear(self):
        if self.is_fake:
            return
        try:
            self.list_store.clear()
        except:
            pass

    def populate_treeview(self, item_list=[]):
        if self.is_fake:
            return
        try:
            self.list_store.clear()
            for item in item_list:
                self.list_store.append(item)
            self.dialog.get_window().set_cursor(None)
        except:
            pass

    def set_progress_message(self, msg):
        if self.is_fake:
            return
        if not msg:
            msg = u' '

        try:
            self.progress.set_text(GT(msg))
        except:
            pass

    def start_loading_animation(self):
        if self.is_fake:
            return
        try:
            cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)
            self.dialog.get_window().set_cursor(cursor)
        except:
            pass

    def stop_loading_animation(self):
        if self.is_fake:
            return
        try:
            cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
            self.dialog.get_window().set_cursor(cursor)
        except:
            pass

    def progress_pulse(self):
        if self.is_fake:
            return
        try:
            self.progress.pulse()
        except:
            pass

    def progress_reset(self):
        if self.is_fake:
            return
        try:
            self.progress.set_fraction(0.0)
        except:
            pass

    ########################################################
    # Initialization
    ########################################################

    def build(self):
        """ Build and obtain all the widgets we need to initialize """
        builder = Totem.plugin_load_interface("opensubtitles",
                                              "opensubtitles.ui", True,
                                              self.totem_object.get_main_window(),
                                              None)

        self.languages = [builder.get_object('main_language'),
                          builder.get_object('alt_language')]
        self.language_model = builder.get_object('language_model')
        self.dialog = builder.get_object('subtitles_dialog')
        self.progress = builder.get_object('progress_bar')
        self.tree_view = builder.get_object('subtitle_treeview')
        self.list_store = builder.get_object('subtitle_model')
        self.find_button = builder.get_object('find_button')
        self.apply_button = builder.get_object('apply_button')
        self.close_button = builder.get_object('close_button')

    def setup_languages(self, pre_selected_languages=[]):
        """ Set up and populate the languages combobox """
        sorted_languages = Gtk.TreeModelSort(model=self.language_model)
        sorted_languages.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        renderer = Gtk.CellRendererText()
        for lang in self.languages:
            lang.set_model(sorted_languages)
            lang.pack_start(renderer, True)
            lang.add_attribute(renderer, 'text', 0)

        for lang in LANGUAGES_STR_CODE:
            lang_iter = self.language_model.append(lang)
            cur_lang = LANGUAGES_CODE_MAP[lang[1]]
            for l, l_box in zip(pre_selected_languages, self.languages):
                if cur_lang != l:
                    continue
                success, parent_iter = sorted_languages.convert_child_iter_to_iter(lang_iter)
                if not success:
                    continue
                l_box.set_active_iter(parent_iter)

    def setup_treeview(self):
        """ Set up the results treeview """
        renderer = Gtk.CellRendererText()
        self.tree_view.set_model(self.list_store)
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
            self.tree_view.append_column(column)

    def setup_events(self):
        """ Set up signals (connect the callbacks) """
        self.apply_button.connect('clicked', self.__on_apply_clicked)
        self.find_button.connect('clicked', self.__on_find_clicked)

        self.close_button.connect('clicked', self.__on_close_clicked)
        self.dialog.connect('delete-event', self.__on_close_clicked)

        for i, l_box in enumerate(self.languages):
            l_box.connect('changed', self.__on_language_changed, i)

        self.dialog.connect('key-press-event',
                            self.__on_window__key_press_event)
        self.tree_view.get_selection().connect('changed',
                                               self.__on_treeview__row_change)
        self.tree_view.connect('row-activated',
                               self.__on_treeview__row_activate)

    ##########################################################
    # Callbacks Handlers
    ##########################################################

    def __on_close_dialog(self):
        self.close()
        self.plugin_object.on_close_dialog()

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
        model, rows = self.tree_view.get_selection().get_selected_rows()
        if not rows:
            print('Warning, nothing is really selected')
            return

        subtitle_iter = model.get_iter(rows[0])
        columns = ['language', 'name', 'format', 'rating', 'id', 'size']
        selected_dict = {c: model.get_value(subtitle_iter, i) for i, c in enumerate(columns)}
        self.plugin_object.on_download_request(selected_dict)

    def __on_treeview__row_activate(self, _tree_path, _column, _data):
        self.__on_download_request()

    def __on_apply_clicked(self, _):
        self.__on_download_request()

    def __on_language_changed(self, combobox, index):
        combo_iter = combobox.get_active_iter()
        combo_model = combobox.get_model()
        cur_lang = LANGUAGES_CODE_MAP[combo_model.get_value(combo_iter, 1)]
        self.plugin_object.on_language_change(index, cur_lang)
