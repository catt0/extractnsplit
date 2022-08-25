#!/usr/bin/env python3

from math import ceil, log10
from loguru import logger
from typing import List
from pathlib import Path
import shutil

from recognize import Track

def check_arguments(args) -> bool:
    return True


def rename_tracks(tracks: List[Track], media_file: str, rename_name_pattern: str) -> List[Track]:
    format_str = rename_name_pattern
    format_str = format_str.replace(r'%n', '{track_number}')
    digits_needed = ceil(log10(len(tracks) + 1))
    format_str = format_str.replace(r'%N', '{{track_number:0{}}}'.format(digits_needed))
    format_str = format_str.replace(r'%t', '{title}')
    format_str = format_str.replace(r'%a', '{artist}')
    format_str = format_str.replace(r'%l', '{album}')
    format_str = format_str.replace(r'%m', '{media_name}')
    format_str += '{extension}'
    logger.debug('Constructed format string: {}.', format_str)

    for track in tracks:
        track_number = track.position + 1
        title = track.title
        title = 'Unknown Title' if title is None else title
        artist = track.artist
        artist = 'Unknown Artist' if artist is None else artist
        album = track.album
        album = 'Unknown Album' if album is None else album
        media_name = Path(Path(media_file).name).stem
        extension = Path(media_file).suffix

        target_path = Path(media_file).parent
        file_name = format_str.format(track_number=track_number, title=title, artist=artist, album=album, media_name=media_name, extension=extension)
        target_path = str(target_path.joinpath(file_name))

        logger.trace('Renaming {} to {}.', track.file_path, target_path)
        shutil.move(track.file_path, target_path)
        track.file_path = target_path

    return tracks
