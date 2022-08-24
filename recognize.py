#!/usr/bin/env python3

from loguru import logger
from typing import List

import subprocess
import json
import tempfile

import split


class Track:
    def __init__(self):
        self.artist = None
        self.title = None
        self.album = None
        self.year = None
        # position in original media
        self.position = None
        # path on disc
        self.file_path = None

    def __str__(self) -> str:
        return 'Track {} at {}: title {}, artist {}, album {}, year {}'.format(
            self.position, self.file_path, self.title, self.artist, self.album, self.year)

    def is_same_track(self, other) -> bool:
        return self.file_path == other.file_path and self.position == other.position


def check_arguments(args) -> bool:
    logger.trace('Checking songrec by executing songrec --version.')
    subprocess.check_call(['songrec', '--version'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    logger.trace('songrec is available.')
    return True


def recognize_track(track_path: str, position: int) -> Track:
    songrec_args = [
        'songrec',
        'audio-file-to-recognized-song',
        track_path
    ]
    logger.trace('Calling songrec with arguments: {}.', songrec_args)

    proc = subprocess.run(songrec_args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError('Identifying track {} failed with code {}, stderr: {}, stdout: {}.'.format(
            track_path, proc.returncode, proc.stderr, proc.stdout))

    jsons = proc.stdout
    song_info = json.loads(jsons)

    track = Track()
    track.position = position
    track.file_path = track_path
    if 'track' not in song_info:
        logger.warning('Unable to recognize {}.', track_path)
        logger.debug('Response from songrec for {}: {}.', track_path, song_info)
        return track
    track.title = song_info['track']['title']
    track.artist = song_info['track']['subtitle']

    for section in song_info['track']['sections']:
        if 'metadata' in section:
            for metadata in section['metadata']:
                if metadata['title'] == 'Album':
                    track.album = metadata['text']
                elif metadata['title'] == 'Released':
                    track.year = metadata['text']

    logger.trace('Recognized as {}.', track)
    return track


# extracts a part from the track fruther from the start
# this might allow songrec to recognize it in case of overlap between tracks
def extract_part(track_path: str, tmpdir: str) -> str:
    # customize split config for speed and accuracy
    split_config = split.SplitConfig()
    split_config.fade_in = 0
    split_config.fade_out = 0
    split_config.start_offset = 0
    split_config.end_offset = 0
    split_config.file_pattern = 'temp_cut_fragment_%n'

    # extract one minute starting at 30 seconds
    timestamps = [30, 90]
    splits = split.split_files(track_path, timestamps, tmpdir, split_config)

    num_splits = len(splits)
    if num_splits == 0:
        logger.debug('Track {} is too short for extraction.', track_path)
        return track_path
    elif num_splits in [1, 2]:
        # 1 - track length between 30s and 90s
        # 2 - track length > 90s
        return splits[0]
    else:
        raise ValueError('Unreachable: track {} was split into {} fragments.'.format(track_path, num_splits))


# tries a different part of the track
def recheck_track(track : Track) -> Track:
    with tempfile.TemporaryDirectory() as tmpdir:
        part_path = extract_part(track.file_path, tmpdir)
        logger.debug('Split part from {} to {}.', track.file_path, part_path)
        new_track = recognize_track(part_path, track.position)
        logger.debug('Re-recognized track: {}.', new_track)

        return new_track


def recognize_tracks(track_paths: List[str]) -> List[Track]:
    tracks = []
    recognized = 0
    rechecked = 0
    recognized_after_recheck = 0
    for i, track_path in enumerate(track_paths):
        track = recognize_track(track_path, i)

        if track.title is None:
            rechecked += 1
            track = recheck_track(track)
            if track.title is not None:
                recognized_after_recheck += 1

        tracks.append(track)
        if track.title is not None:
            recognized += 1

    logger.debug('Recognized {} of {} tracks. Rechecked {} tracks, success on {} of them.',
        recognized, len(tracks), rechecked, recognized_after_recheck)

    return tracks
