#!/usr/bin/env python3

from typing import List
from loguru import logger
import music_tag

from recognize import Track

def check_arguments(args) -> bool:
    return True


def tag_tracks(tracks: List[Track], thumbnail_path: str or None):
    thumbnail_data = None
    if thumbnail_path is not None:
        thumbnail_data = open(thumbnail_path, 'rb').read()
    logger.debug('Read {} bytes from {}', len(thumbnail_data) if thumbnail_path is not None else 0, thumbnail_path)
    for track in tracks:
        f = music_tag.load_file(track.file_path)
        f['title'] = track.title if track.title is not None else "Unknown Title"
        f['album'] = track.album if track.album is not None else "Unknown Album"
        f['artist'] = track.artist if track.artist is not None else "Unknown Artist"
        f['tracknumber'] = track.position + 1
        if track.year is not None:
            f['year'] = track.year
        if thumbnail_data is not None:
            f['artwork'] = thumbnail_data
        f.save()
        logger.trace('Tagged {}.', track.file_path)
