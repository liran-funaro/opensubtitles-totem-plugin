import argparse
import logging
import os

from opensubtitles.api import OpenSubtitlesApi
from opensubtitles.api.lang import LANGUAGES_ALL_TO_3


def extant_file_exist(input_path: str) -> str:
    path = os.path.expanduser(input_path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("path does not exist")
    return path


def main():
    logging.basicConfig(level=logging.DEBUG)
    p = argparse.ArgumentParser(description="Opensubtitles.org Downloader")
    p.add_argument("-f", "--file-path", type=extant_file_exist, default=None)
    p.add_argument("-t", "--title", type=str, default=None)
    p.add_argument("-o", "--op", action="append", default=["query"], choices=["query", "download"])
    p.add_argument("-i", "--index", type=int)
    p.add_argument("-l", "--language", nargs="*", default=["he", "en"], choices=LANGUAGES_ALL_TO_3.keys())
    args = p.parse_args()

    if args.file_path is None and args.title is None:
        raise Exception("Must supply either file-path or title")

    open_sub = OpenSubtitlesApi('Totem')
    for op in args.op:
        if op == "query":
            ret = open_sub.search_subtitles(args.languages, movie_file_path=args.file_path, movie_title=args.title)
            print(ret)
        elif op == "download":
            pass


if __name__ == "__main__":
    main()
