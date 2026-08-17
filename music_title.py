#!/usr/bin/env python3

import argparse
import os
import re

from mutagen.easyid3 import EasyID3
from mutagen.id3 import COMM, ID3


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


def read_comment(args):
    """Возвращает комментарий из --comment или UTF-8 файла."""
    if args.comment is not None and args.comment_file is not None:
        raise ValueError("--comment and --comment-file cannot be used together")

    if args.comment_file:
        with open(
            os.path.expanduser(args.comment_file),
            "r",
            encoding="utf-8",
        ) as fh:
            return fh.read().rstrip("\n")

    return args.comment


def set_comment(path, comment):
    """Записывает многострочный Unicode-комментарий в ID3v2.3 COMM."""
    tags = ID3(path)

    # Убираем старые COMM, чтобы не оставлять несколько вариантов комментария.
    tags.delall("COMM")

    if comment is not None:
        tags.add(
            COMM(
                encoding=1,  # UTF-16: совместимо с ID3v2.3 и кириллицей
                lang="rus",
                desc="soundlabel",
                text=comment,
            )
        )

    tags.save(path, v2_version=3)


def main():
    parser = argparse.ArgumentParser(
        description="Fill MP3 Artist/Title tags from filenames and optionally set a comment."
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
    parser.add_argument(
        "-a",
        "--artist",
        help="Set the same artist for all files."
    )
    parser.add_argument(
        "-c",
        "--comment",
        help=(
            "Set the same MP3 comment for all files. "
            "Supports multiline text via shell quoting."
        ),
    )
    parser.add_argument(
        "--comment-file",
        help="Read the MP3 comment from a UTF-8 text file."
    )

    args = parser.parse_args()

    try:
        comment = read_comment(args)
    except (OSError, ValueError) as e:
        parser.error(str(e))

    directory = os.path.abspath(os.path.expanduser(args.directory))

    if os.path.isfile(directory):
        if not directory.lower().endswith(".mp3"):
            parser.error(f"{directory} is not an MP3 file")
        mp3_files = [(os.path.dirname(directory), os.path.basename(directory))]
    elif os.path.isdir(directory):
        mp3_files = []
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(".mp3"):
                    mp3_files.append((root, filename))
    else:
        parser.error(f"{directory} is neither a file nor a directory")

    for root, filename in mp3_files:
        path = os.path.join(root, filename)
        name = os.path.splitext(filename)[0]

        if args.artist:
            # Имя файла целиком считается названием трека
            artist = args.artist
            title = clean_name(name)
        else:
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
                tags.save(path, v2_version=3)
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

            if comment is not None:
                set_comment(path, comment)
                changed = True

            if changed:
                print(f"Fixed: {filename}")

        except Exception as e:
            print(f"Skip {filename}: {e}")


if __name__ == "__main__":
    main()
