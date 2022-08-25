#!/usr/bin/env python3

from loguru import logger
from typing import List
from pathlib import Path

from recognize import Track

def check_arguments(args) -> bool:
    return True


def write_m3u_playlist(tracks: List[Track], file_prefix: str, destination_handle) -> None:
    destination_handle.write('#EXTM3U\n')
    for track in tracks:
        # EXTINF contains the length (-1 means ignore), the artist and the title
        destination_handle.write('#EXTINF:-1,{} - {}\n'.format(track.artist, track.title))
        file_name = Path(track.file_path).name
        destination_handle.write('{}{}\n'.format(file_prefix, file_name))


def create_playlist(tracks: List[Track], same_folder: bool, parent_folder: bool) -> None:
    if not same_folder and not parent_folder:
        return

    same_folder_path = Path(tracks[0].file_path).parent
    same_folder_name = same_folder_path.name
    parent_folder_path = same_folder_path.parent

    if same_folder:
        with open(same_folder_path.joinpath(same_folder_name + '.m3u'), 'w') as f:
            write_m3u_playlist(tracks, '', f)

    if parent_folder:
        with open(parent_folder_path.joinpath(same_folder_name + '.m3u'), 'w') as f:
            write_m3u_playlist(tracks, same_folder_name + '/', f)
