import argparse
import logging
import os
from pprint import pprint

from opensubtitles_api import LANGUAGES_CODE_MAP, OpenSubtitlesApi


def extant_file_exist(input_path: str) -> str:
    path = os.path.expanduser(input_path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("path does not exist")
    return path


def main():
    logging.basicConfig(level=logging.DEBUG)
    p = argparse.ArgumentParser(description="Opensubtitles.org Downloader")
    p.add_argument("-f", "--file-path", type=extant_file_exist)
    p.add_argument("-t", "--title", type=str)
    p.add_argument("-o", "--op", action="append", default=["query"], choices=["query", "download"])
    p.add_argument("-i", "--index", type=int)
    p.add_argument("-l", "--language", nargs="*", default=["he", "en"], choices=LANGUAGES_CODE_MAP.keys())
    args = p.parse_args()

    if args.file_path is None and args.title is None:
        raise Exception("Must supply either file-path or title")
    if args.file_path is not None and args.title is not None:
        raise Exception("Must supply either file-path or title")

    languages = get_language_term(args.language)

    open_sub = OpenSubtitlesApi('Totem')
    for op in args.op:
        if op == "query":
            if args.file_path is not None:
                ret = open_sub.search_subtitles(languages, args.file_path)
            else:
                ret = open_sub.search_subtitles_with_title(languages, args.title)

            for r in ret:
                pprint(r)
        elif op == "download":
            pass


if __name__ == "__main__":
    main()
