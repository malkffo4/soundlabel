#!/usr/bin/env python3

import argparse
import os
import re

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3


def clean_name(text: str) -> str:
    """Удаляет номер трека в начале."""
    return re.sub(r"^\d+[\s._-]*", "", text).strip()


def split_filename(name: str, separators):
    """
    Разделяет имя файла по первому найденному разделителю.
    """
    for sep in separators:
        pattern = rf"\s*{re.escape(sep)}\s*"
        parts = re.split(pattern, name, maxsplit=1)
        if len(parts) == 2:
            return parts

    return None


parser = argparse.ArgumentParser(
    description="Fill MP3 Artist/Title tags from filenames."
)

parser.add_argument(
    "directory",
    help="Directory with mp3 files"
)

parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="Overwrite existing Artist and Title tags."
)

parser.add_argument(
    "-r",
    "--reverse",
    action="store_true",
    help="Filename format is 'Title - Artist' instead of 'Artist - Title'."
)

parser.add_argument(
    "-s",
    "--separator",
    action="append",
    default=["-"],
    help=(
        "Separator between artist and title. "
        "Can be specified multiple times. "
        "Example: -s '-' -s '—' -s '|'"
    ),
)

args = parser.parse_args()

directory = os.path.abspath(os.path.expanduser(args.directory))

if not os.path.isdir(directory):
    parser.error(f"{directory} is not a directory")

for root, _, files in os.walk(directory):
    for filename in files:

        if not filename.lower().endswith(".mp3"):
            continue

        path = os.path.join(root, filename)
        name = os.path.splitext(filename)[0]

        parts = split_filename(name, args.separator)

        if not parts:
            print(f"Skip: {filename} (separator not found)")
            continue

        left = clean_name(parts[0])
        right = parts[1].strip()

        if args.reverse:
            artist = right
            title = left
        else:
            artist = left
            title = right

        try:
            try:
                audio = EasyID3(path)
            except Exception:
                tags = ID3()
                tags.save(path)
                audio = EasyID3(path)

            current_artist = audio.get("artist", [""])[0].strip()
            current_title = audio.get("title", [""])[0].strip()

            changed = False

            if args.force:
                if current_artist != artist:
                    audio["artist"] = artist
                    changed = True

                if current_title != title:
                    audio["title"] = title
                    changed = True
            else:
                if not current_artist or current_artist.isdigit():
                    audio["artist"] = artist
                    changed = True

                if not current_title:
                    audio["title"] = title
                    changed = True

            if changed:
                audio.save(v2_version=3)
                print(f"Fixed: {filename}")

        except Exception as e:
            print(f"Skip {filename}: {e}")
