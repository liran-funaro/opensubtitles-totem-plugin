# opensubtitles-totem-plugin

OpenSubtitles Download ([Totem](https://github.com/GNOME/totem) Plugin) downloads subtitles automatically upon opening a
file from [OpenSubtitles.org](https://www.opensubtitles.org).

This plugin extends the [original plugin](https://github.com/GNOME/totem/tree/master/src/plugins/opensubtitles) that is
supplied with totem.

# Features

- Automatic search and download on open.
- Add context menu under "Subtitles" that allow downloading alternative subtitles (from previous search results) to
  quickly find the most fitting subtitles for your video.
- Search multiple languages: \<your language> and English (for example), if there are no available subtitles in your
  language.
- Cache search results and downloaded subtitles.

# Install

Download the content of this repository to `~/.local/share/totem/plugins/opensubtitles-totem-plugin`.
Or clone the repository to the plugins' folder:

```bash
cd ~/.local/share/totem/plugins
git clone https://github.com/liran-funaro/opensubtitles-totem-plugin.git
```

Finally, enable the plugin in the "Preferences->General->Plugins..." menu.

It is also recommended to mark "Load subtitle files when a movie is loaded" in "Preferences->General" so previously
downloaded subtitles will be loaded automatically.

# First Usage

Open totem and goto "Subtitles->Search OpenSubtitles..." menu.
A dialog box will open.
On the "Subtitle language(s)" select first the main language, and in the second combo-box select an alternative one.
You can press the "Find" button if a video is currently opened.
This will list the available subtitles for the current video, sorted by language (main then alternative) and then by
their ranking on "OpenSubtitles.org".

You can return to this dialog box at any time to change the search settings.
To change subtitles, simply use the "Subtitles" context menu.

# Usage

Once a video file is opened, the plugin will search for matching subtitles according to the languages that were set on
the last search (see "First Usage") and will download the best match.
Subtitles will appear automatically once it finishes downloading.

If the chosen subtitle does not match, simply go to the context menu ("Subtitles") and choose another subtitle from
there.

The search results and downloaded subtitles are cached for a single day and deleted afterward.
This allows switching subtitles back and forth when none of the subtitles is a perfect fit.
The currently used subtitle would be saved next to the video file under the same filename, but with its own extension.

# License

[GPL](LICENSE.txt)
