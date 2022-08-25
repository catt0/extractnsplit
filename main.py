#!/usr/bin/env python3

import shutil
from loguru import logger
import argparse
import sys
from pathlib import Path
import os

import download
import timestamps
import split
import recognize
import rename
import tag

from pprint import pprint


def check_args(args) -> bool:
    if not download.check_arguments(args):
        return False
    if not timestamps.check_arguments(args):
        return False
    if not split.check_arguments(args):
        return False
    if not recognize.check_arguments(args):
        return False
    if not rename.check_arguments(args):
        return False
    if not tag.check_arguments(args):
        return False

    if download.is_remote_file(args.media_file_path) and args.timestamps_file_path == 'stdin' and args.dest is None:
        print('With a remote file and reading timestamps from stdin, the --dest argument is required.')
        return False

    if not download.is_remote_file(args.media_file_path) and args.use_thumbnail:
        print('Can only fetch thumbnail when providing a media URL.')
        return False

    if not download.is_remote_file(args.media_file_path) and args.audio_format is not None:
        print('audio-format can only be specified in combination with a remote file.')
        return False

    if args.thumbnail_file_path is not None:
        try:
            open(args.thumbnail_file_path, 'rb')
        except:
            print('Thumbnail {} is not readable.'.format(args.thumbnail_file_path))
            return False

    return True


def parse_args(args: list[str]):
    parser = argparse.ArgumentParser(description='Download, split, detect, tag, rename and create a playlist based a video')

    parser.add_argument('media_file_path', type=str, help='URL to download from or local path to the media file. Any site supported by yt-dlp can be provided.')
    parser.add_argument('timestamps_file_path', type=str, default='stdin', nargs='?',
        help='Path to a file containing the timestamps of the individual tracks. '
        'Each timestamp marks the start of a track. '
        'If multiple timestamps are present in a line, the first one is chosen. '
        'Common formats like hh:mm:ss, mm:ss, hh.mm.ss. and mm.ss are supported. '
        'If "stdin" is specified (the default) take the timestamps from stdin. '
        'If providing interactively via stdin, terminate the timestmaps with 2 empty lines or with EOF (CTRL+D).')
    parser.add_argument('--dest', type=str, help='Destination directory for the output. '
        'If it does not exist, it will be created. '
        'By default the directory is either the directory of the media file (if local) or the directory of the timestamp file. '
        'If the media file is remote and timestamps are passed via stdin, this option is required.')

    parser.add_argument('--use-thumbnail', action=argparse.BooleanOptionalAction, help='Download the thumbnail from the media URL and use it when tagging. By default fetch the thumbnail when downloading a remote media file.')
    parser.add_argument('--audio-format', type=str, help='Audio format to use. All split files will be of the same type. Any audio format supported by yt-dlp can be used. Recommended: "flac" or "mp3". Default is "mp3"')
    parser.add_argument('--thumbnail-file-path', type=str, help='Path to the thumbnail to use, implies --use-thumbnail.')

    parser.add_argument('--split-file-pattern', type=str, default=r'fragment_%n', help='File name pattern used for fragments after splitting. The fragments are generated in the destination folder. '
        r'Following replacements are supported: %%n - fragment number (from 0), %%f - media filename without extension. '
        r'The pattern must include at least one %%n. The default is "fragment_%%n". The extension is appended automatically.')
    parser.add_argument('--split-num-threads', type=int, default=0, help='How many splits to perform in parralel. The default value of 0 means to use the same number as cpu cores.')
    parser.add_argument('--split-start-offset', type=int, default=1, help='Offset from the start timestamp to actually start the fragment, supports positive and negative values, default = 1.')
    parser.add_argument('--split-fade-in', type=int, default=2, help='Over how many seconds to fade in the sound after the start timestamp, default = 2.')
    parser.add_argument('--split-end-offset', type=int, default=-1, help='Offset from the end timestamp to actually end the fragment, supports positive and negative values, default = -1.')
    parser.add_argument('--split-fade-out', type=int, default=3, help='Over how many seconds to fade out the sound before the end timestamp, default = 3.')

    parser.add_argument('--recognize-num-threads', type=int, default=8, help='Number of parallel songrec calls, default = 8.')

    parser.add_argument('--rename-name-pattern', type=str, default=r'%N - %t', help=r'The file name pattern used when renaming tracks. Following placeholders are supported: %%t - title, %%a - artist, %%n - track number, %N - track number, leading zero(s), %%l - aLbum, %%m - media file name.'
        r'The extension is appended automatically, default = %%N - %%t')

    args = parser.parse_args(args[1:])
    return args


@logger.catch
def main(args: list[str]) -> int:
    args = parse_args(args)
    logger.trace('Got arguments: {}', args)

    if not check_args(args):
        logger.debug('Arguments failed check_args: {}.', args)
        return 1

    media_file_path = args.media_file_path
    timestamps_file_path = args.timestamps_file_path
    destination_directory = args.dest
    use_thumbnail = args.use_thumbnail
    if destination_directory is None:
        if not download.is_remote_file(media_file_path):
            destination_directory = Path(media_file_path).parent
        elif timestamps_file_path != 'stdin':
            destination_directory = Path(timestamps_file_path).parent
    if destination_directory is None:
        raise ValueError('Unreachable: check_args() should have prevent this case (remote file and stdin as timestamps, but no --dest).')

    if download.is_remote_file(media_file_path) and use_thumbnail is None:
        use_thumbnail = True

    audio_format = args.audio_format
    if download.is_remote_file(media_file_path) and audio_format is None:
        audio_format = "mp3"

    timestamps_list = timestamps.get_timestamps(timestamps_file_path)
    logger.trace('Got {} timestamps.', len(timestamps_list))

    # create destination directory
    os.makedirs(destination_directory, exist_ok=True)

    if download.is_remote_file(media_file_path):
        logger.trace('Attempting download of {} as {}.', media_file_path, audio_format)
        media_file_path, thumbnail_file_path = download.download(media_file_path, Path(destination_directory), audio_format, use_thumbnail)
        logger.trace('Download complete. Destination {}, thumbnail at {}.', media_file_path, thumbnail_file_path)

    if args.thumbnail_file_path is not None:
        use_thumbnail = True
        thumbnail_file_path = args.thumbnail_file_path

    # create a directory named the same as the downloaded file (the video title) and move media and optional thumbnail into this folder
    # we do this after the download, because we only now know the file name
    file_name = Path(media_file_path).name
    file_name_stem = Path(file_name).stem
    media_directory = Path(destination_directory).joinpath(file_name_stem)
    logger.trace('Moving media files to {}.', media_directory)
    os.makedirs(media_directory, exist_ok=True)
    media_file_path_destination = media_directory.joinpath(file_name)
    # if processing local files, the file might already be at the correct location
    if not Path(media_file_path_destination).exists() or not Path(media_file_path).samefile(media_file_path_destination):
        try:
            os.remove(media_file_path_destination)
        except FileNotFoundError:
            pass
        # do not remove files that got passed as an argument
        if download.is_remote_file(args.media_file_path):
            os.rename(media_file_path, media_file_path_destination)
        else:
            shutil.copy(media_file_path, media_file_path_destination)
        media_file_path = media_file_path_destination
    
    if use_thumbnail:
        thumbnail_name = Path(thumbnail_file_path).name
        thumbnail_file_path_destination = media_directory.joinpath(thumbnail_name)
        # if processing local files, the file might already be at the correct location
        if not Path(thumbnail_file_path_destination).exists() or not Path(thumbnail_file_path).samefile(thumbnail_file_path_destination):
            try:
                os.remove(thumbnail_file_path_destination)
            except FileNotFoundError:
                pass
            # do not remove files that got passed as an argument
            if args.thumbnail_file_path is None:
                os.rename(thumbnail_file_path, thumbnail_file_path_destination)
            else:
                shutil.copy(thumbnail_file_path, thumbnail_file_path_destination)
            thumbnail_file_path = thumbnail_file_path_destination
    else:
        thumbnail_file_path = None

    split_config = split.get_config_from_arguments(args)
    splitted_files = split.split_files(media_file_path, timestamps_list, media_directory, split_config)
    logger.debug('Split into {} files.', len(splitted_files))

    recognize_num_threads = args.recognize_num_threads
    tracks = recognize.recognize_tracks(splitted_files, recognize_num_threads)

    rename_name_pattern = args.rename_name_pattern
    tracks = rename.rename_tracks(tracks, media_file_path, rename_name_pattern)

    tag.tag_tracks(tracks, thumbnail_file_path)
    
    return 0

if __name__ == '__main__':
    exit(main(sys.argv))
