import os
import re

QUALITY_OPTIONS = [
    "480p",
    "720p",
    "1080p",
    "2160p",
    "4096p",
    "4K",
]

VIDEO_CONTAINERS = [
    "avi", "mkv",
    "mp4", "mp3", "mpeg", "mpg", "mpg2", "mpeg2", "mpeg3", "mpg3",
    "ogv", "xvid", "divx", "mov", "movw", "wmv", "avchd", "webm",
]

# See: https://en.wikipedia.org/wiki/Pirated_movie_release_types
RELEASE_FORMATS = [
    # CamVCDQuality Terms – Lists recent video releases in the warez scene.: Common; low video and sound quality
    "CAM-Rip", "CAM", "HDCAM",
    # TelesyncTelesync – AfterDawn: Glossary of technology terms & acronyms: Uncommon
    "TS", "HDTS", "TELESYNC", "PDVD", "PreDVDRip",
    # Workprint: Extremely rare
    "WP", "WORKPRINT",
    # Telecine: Very rare
    "TC", "HDTC", "TELECINE",
    # Pay-Per-View Rip: Very rare, WEB-DL is preferred
    "PPVRip", "PPV",
    # Screener: Uncommon
    "SCR", "SCREENER", "DVDSCR", "DVDSCREENER", "BDSCR", "WEBSCREENER",
    # Digital Distribution Copy orDownloadable/Direct Digital Content: Rare
    "DDC",
    # R5: Rare
    "R5", "R5.LINE", "R5.AC3.5.1.HQ",
    # DVD-Rip: Currently sort of rare as a few films are now released on Blu-Ray discs, which have better quality.
    "DVDRip", "DVDMux",
    # DVD-R: Common
    "DVDR", "DVD-Full", "Full-Rip", "ISO-rip", "lossless-rip", "untouched-rip", "DVD-5", "DVD-9",
    # HDTV, PDTV or DSRip: Common. often used for TV programs
    "DSRip", "DSR", "SATRip", "DTHRip", "DVBRip", "HDTV", "PDTV", "DTVRip", "TVRip", "HDTVRip",
    # VODRip: Very rare, WEB-DL is preferred
    "VODRip", "VODR",
    # HC HD-Rip: Common, WEB-DL is some times preferred
    "HC", "HD-Rip",
    # WEBCap: Rare, WEBRip is preferred
    "WEB-Cap", "WEBCAP", "WEB-Cap",
    # HDRip: Common, WEBRip  is preferred
    "HDRip", "WEB-DLRip",
    # WEBRip: Common, WEB-DL is preferred but not available as much as WEBRip is
    "WEBRip", "WEB-Rip", "WEB-Rip",
    # WEB-DL (P2P):
    "WEBDL", "WEB-DL", "WEB-DL", "WEBRip", "WEB-MUX", "WEB",
    # Blu-ray/BD/BRRip: Extremely common. Blu-ray and 4K Blu-ray make up a large share of the market, despite each segment making up a smaller market share than DVD by itself.
    "Blu-Ray", "BluRay", "BLURAY", "BDRip", "BRip", "BRRip",
    "BDR-The.2010.BDR.Releasing.Standards", "BD25", "BD50",
    "BD66", "BD100", "BD5", "BD9", "BDMV", "BDISO", "COMPLETE.BLURAY",
]

# See: https://en.wikipedia.org/wiki/Pirated_movie_release_types
TV_TERMS = [
    "ABC",  # American Broadcasting Company
    "AUBC",  # Australian Broadcasting Corporation
    "ATVP",  # Apple TV +
    "AMZN",  # Amazon Studios / Amazon Prime Video
    "BBC",  # British Broadcasting Corporation
    "BCORE",  # Bravia Core
    "BMS",  # BookMyShow
    "BOOM",  # Boomerang
    "CBC",  # Canadian Broadcasting Corporation / CBC Gem
    "CBS",  # CBS Corporation
    "CC",  # Comedy Central
    "CRAV",  # Crave
    "CRITERION",  # The Criterion Collection
    "CW",  # The CW
    "DCU",  # DC Universe
    "DSCP",  # Discovery Plus
    "DSNP",  # Disney Plus
    "DSNY",  # Disney Networks (Disney Channel, Disney XD, Disney Junior)
    "FBWatch",  # Facebook Watch
    "FREE",  # Freeform
    "FOX",  # Fox Broadcasting Company
    "GPLAY",  # Google Play
    "HMAX",  # HBO Max
    "HULU",  # Hulu Networks
    "HTSR", "HS",  # Hotstar
    "iP",  # BBC iPlayer
    "iT",  # iTunes
    "JC",  # JioCinema
    "LGP",  # Lionsgate Play
    "LIFE",  # Lifetime
    "MA",  # Movies Anywhere
    "MMAX",  # ManoramaMAX
    "MTV",  # MTV Networks
    "MUBI",  # Mubi
    "NBC",  # National Broadcasting Company
    "NF",  # Netflix
    "NICK",  # Nickelodeon
    "OAR",  # Original Aspect Ratio
    "PCOK",  # Peacock
    "PMTP",  # Paramount Plus
    "PF",  # Pureflix
    "RED",  # YouTube Premium (formerly YouTube Red)
    "ROKU",  # Roku
    "SAINA", "SP",  # Saina Play
    "SHO",  # Showtime
    "SS",  # Simply South
    "STAN",  # Stan
    "STZ",  # STARZ
    "TBS",  # Turner Broadcasting System
    "TK",  # Tentkotta
    "TVNZ",  # TVNZ
    "ABC",  # Asahi Hōsō TV / 朝日放送テレビ
    "ADN",  # Anime Digital Network (French)
    "ANIMAX",  # Animax
    "AO",  # Anime Onegai (Spanish)
    "AT-X",  # Anime Theatre X
    "Baha",  # Bahamut Animation Madness (Chinese)
    "B-Global", "Bstation",  # Bilibili
    "BSP",  # NHK BS Premium
    "BS4",  # BS Nippon TV / BS Nitele
    "BS6",  # BS-TBS
    "BS7", "BSJ", "BS-TX",  # BS TV TOKYO / BSテレ東 / BS Teleto
    "BS8", "BS-Fuji",  # BS Fuji
    "BS11",  # Nippon BS Broadcasting
    "BS12",  # BS12 トゥエルビ
    "CR",  # Crunchyroll
    "CS-Fuji ONE",  # Fuji TV One
    "CX",  # Fuji TV
    "EX",  # TV Asahi / テレビ朝日
    "EX-BS", "BS-EX",  # BS TV Asahi
    "CS3", "EX-CS1", "CS-EX1", "CSA",  # TV Asahi Channel 1
    "FOD",  # Fuji TV On Demand
    "FUNi",  # Funimation
    "HIDIVE",  # HIDIVE
    "KBC",  # Kyushu Asahi Broadcasting
    "M-ON!",  # MUSIC ON! TV
    "MX",  # Tokyo MX
    "NHKG",  # NHK General TV
    "NHKE",  # NHK Education TV
    "NTV",  # Nippon TV
    "TBS",  # TBS Television
    "TSC",  # TV Setouchi / テレビせとうち
    "TVA",  # TV Aichi / テレビ愛知
    "TVh",  # TV Hokkaidō / テレビ北海道
    "TVK",  # TV Kanagawa
    "TVO",  # TV Osaka / テレビ大阪
    "TVQ",  # TVQ Kyushu Hoso / TVQ九州放送
    "TX",  # TV TOKYO / テレビ東京
    "U-NEXT",  # U-NEXT
    "WAKA",  # Wakanim
    "WOWOW",  # Wowow
    "YTV",  # Yomiuri TV / 読売テレビ
]

# See: https://en.wikipedia.org/wiki/Pirated_movie_release_types
VIDEO_LABELS = [
    # Remux means the data has been copied without any changes.
    # So a BluRay release without the 'remux' tag means that the media has been reencoded and there is loss
    # of quality, while 'remux' means it is lossless.
    "REMUX", "BDREMUX", "BDRIP",
    # High Efficiency Video Coding (HEVC), also known as H.265 and MPEG-H Part 2, is a video compression standard
    # designed as part of the MPEG-H project as a successor to the widely used Advanced Video Coding
    # (AVC, H.264, or MPEG-4 Part 10).
    "HEVC",
    "H-264", "H-265", "x-264", "x-265",
    "MPEG-4", "MPEG-H", "MPEG",
    # Advanced Video Coding (AVC), which is also called H.264, is the most widely used video compression
    # standard. It is compatible with all major streaming protocols and container formats.
    "AVC",
    # AV1 is a free modern video format developed by the Alliance for Open Media (AOM). It delivers high quality
    # video at lower bitrates than H.264 or even H.265/HEVC. Unlike HEVC, it can be streamed in common web
    # browsers. It is being adopted by YouTube and Netflix, amongst others. As of 2023, a few encoders use AV1.
    "AV-1",
    # In October 1999, DeCSS was released. This program allowed anyone to remove the CSS encryption on a DVD.
    # Although its authors only intended the software to be used for playback purposes,[2] it also meant that one
    # could decode the content perfectly for ripping; combined with the DivX 3.11 Alpha codec released shortly
    # after, the new codec increased video quality from near VHS to almost DVD quality when encoding from a DVD
    # source.
    "DivX",
    # The early DivX releases were mostly internal for group use, but once the codec spread, it became accepted as
    # a standard and quickly became the most widely used format for the scene. With help from associates who
    # either worked for a movie theater, movie production company, or video rental company, groups were supplied
    # with massive amounts of material, and new releases began appearing at a very fast pace. When version 4.0 of
    # DivX was released, the codec went commercial and the need for a free codec, Xvid (then called "XviD", "DivX"
    # backwards), was created. Later, Xvid replaced DivX entirely. Although the DivX codec has evolved from
    # version 4 to 10.6 during this time, it is banned[3] in the warez scene due to its commercial nature.
    "Xvid",
    # HDR10 Media Profile, more commonly known as HDR10, is an open high-dynamic-range video standard announced on
    # August 27, 2015, by the Consumer Technology Association. It is the most widespread HDR format.
    # HDR10 is not backward compatible with SDR. It includes HDR static metadata but not dynamic metadata.
    "HDR-10", "HDR",
    # Ultra-high-definition television today includes 4K UHD and 8K UHD, which are two digital video formats with
    # an aspect ratio of 16:9. These were first proposed by NHK Science & Technology Research Laboratories and
    # later defined and approved by the International Telecommunication Union.
    "UHD",
    # 10-bit refers to the color depth of a video.
    "10-bit"
]

AUDIO_LABELS = [
    # DTS-HD Master Audio is a multichannel, lossless audio codec developed by DTS as an extension of the lossy
    # DTS Coherent Acoustics codec.
    "DTS-HD", "DTS",
    # Advanced Audio Coding (AAC) is an audio coding standard for lossy digital audio compression.
    # Designed to be the successor of the MP3 format, AAC generally achieves higher sound quality than MP3
    # encoders at the same bit rate.
    "AAC",
    # The Audio Codec 3 is a Dolby Digital audio format that allows for up to 6 channels of audio output.
    # It is now also used for other applications such as HDTV broadcast, DVDs, Blu-ray Discs and game consoles.
    # Know more about AC3 file format : AC3 is a file extension for surround sound audio files used on DVDs format.
    "AC-3",
    # Dolby Atmos is a surround sound technology developed by Dolby Laboratories. It expands on existing surround
    # sound systems by adding height channels, allowing sounds to be interpreted as three-dimensional objects with
    # neither horizontal nor vertical limitations.
    "Atmos",
    # Dolby Digital Plus (DDP)
    "DDP", "DDP-A",
    "MultiAudio",
]

SINGLE_SEP = re.compile(r"[.\-_ \t\n[\]]", re.IGNORECASE)
SEP = re.compile(rf"{SINGLE_SEP.pattern}+", re.IGNORECASE)
OPT_SEP = re.compile(rf"{SINGLE_SEP.pattern}*", re.IGNORECASE)
BA = f"(?:$|(?={SINGLE_SEP.pattern}))"
BB = f"(?:^|(?<={SINGLE_SEP.pattern}))"


def make_term_regexp(term: str):
    term = SEP.sub("$", term)
    term = term.replace("|", r"\|")
    term = term.replace("$", OPT_SEP.pattern)
    return term


def make_or_terms_regexp(term_list: list[str]):
    # Make sure we match longest terms first.
    term_list = sorted(set(term_list), key=len, reverse=True)
    terms_re = "|".join(map(make_term_regexp, term_list))
    return f"({terms_re})"


def make_terms_regexp(term_list: list[str]):
    term_re = f"{BB}{make_or_terms_regexp(term_list)}{BA}"
    return re.compile(term_re, re.IGNORECASE)


AUDIO_QUALITY_RE = re.compile(rf"[5-7](\.1|CH){BA}", re.IGNORECASE)
SEARCHES = {
    "year": re.compile(rf"{BB}(19\d{{2}}|20\d{{2}}){BA}", re.IGNORECASE),
    "season-episode": re.compile(rf"{BB}(S(\d{{2}})(?:E(\d{{2}}))?){BA}", re.IGNORECASE),

    "audio-quality": AUDIO_QUALITY_RE,
    "video-quality": make_terms_regexp(QUALITY_OPTIONS),

    "video-container": re.compile(rf"\.{make_or_terms_regexp(VIDEO_CONTAINERS)}$"),
    "release-format": make_terms_regexp(RELEASE_FORMATS),
    "tv-term": make_terms_regexp(TV_TERMS),
    "video-label": make_terms_regexp(VIDEO_LABELS),
    # Audio label is often coupled with the audio quality without a separator.
    "audio-label": re.compile(
        f"{BB}{make_or_terms_regexp(AUDIO_LABELS)}({OPT_SEP.pattern}{AUDIO_QUALITY_RE.pattern}|{BA})",
        re.IGNORECASE,
    ),
}

COLUMNS = "title", *SEARCHES.keys(), "group", "search-term"
ID_COLUMNS = "title", "year", "season-episode"


def parse_filename(movie_file_path: str) -> dict[str, str | list[str]]:
    file_name = os.path.basename(movie_file_path)

    properties: dict[str, str | list[str]] = {}
    s, e = len(file_name), 0
    container_start = len(file_name)
    for k, regex in SEARCHES.items():
        for m in regex.finditer(file_name):
            value = m.group(0)

            s = min(m.start(0), s)
            if k != "video-container":
                e = max(m.end(0), e)
            else:
                container_start = min(m.start(0), container_start)

            if k == "season-episode":
                value = value.upper()
                season = m.group(2)
                episode = m.group(3)
                if season:
                    properties.setdefault("season", []).append(season)
                if episode:
                    properties.setdefault("episode", []).append(episode)

            properties.setdefault(k, []).append(value)

    # Anything that remains before the video container is the group.
    properties["group"] = [SEP.sub(" ", file_name[e:container_start]).strip()]

    properties = {k: list(set(v)) for k, v in properties.items()}

    # The beginning of the filename, before any property, is the title.
    properties["title"] = SEP.sub(" ", file_name[:s]).strip().title()

    # The search term is the title + season-episode + year.
    search_term = properties["title"]
    for k in ['season-episode', 'year']:
        for v in properties.get(k, []):
            search_term += f" {v}"
    properties["search-term"] = search_term

    return properties


def _get_unified_key(p, key):
    v = p.get(key, None)
    if isinstance(v, (list, tuple)):
        v = ", ".join(sorted(str(vv).lower() for vv in v))
    if isinstance(v, str):
        v = v.lower()
    return v


def item_key(p):
    return tuple(_get_unified_key(p, col) for col in ID_COLUMNS)


def is_match(term_key, result):
    name = result.get("name", None)
    if name is None:
        return False

    p = parse_filename(name)
    return term_key == item_key(p)
