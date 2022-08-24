#!/usr/bin/env python3

from loguru import logger
from typing import Tuple
from pathlib import Path
import os
import subprocess

def is_remote_file(file_path: str) -> bool:
    logger.trace('Checking {}.', file_path)
    return file_path.startswith('http://') or file_path.startswith('https://')


def check_arguments(args) -> bool:
    logger.trace('Checking yt-dlp by executing yt-dlp --version.')
    subprocess.check_call(['yt-dlp', '--version'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    logger.trace('yt-dlp is available.')
    return True


# Returns the file path to the downloaded file and the thumbnail (if downloaded)
def download(media_url: str, destination_directory: Path, audio_format: str, get_thumbnail: bool) -> Tuple[str, str]:
    logger.trace('Downloading from {} to directory {} as {} and fetching thumbnail: {}.', media_url, destination_directory, audio_format, get_thumbnail)
    orig_wd = os.getcwd()
    os.chdir(destination_directory)

    yt_dlp_args = [
        'yt-dlp',
        # suppress any output besides the requested prints
        # warnings and errors are still printed to stderr
        '-q',
    ]

    if get_thumbnail:
        yt_dlp_args.append('--write-thumbnail')

    yt_dlp_args.extend([
        '--restrict-filenames',
        # prints the absolute path to the output file to stdout
        '--exec', 'echo %(filepath)q',
        '--convert-thumbnails', 'jpg',
        # extract audio as requested format
        '-x', '--audio-format', audio_format,
    ])

    yt_dlp_args.append(media_url)

    logger.trace('Calling yt-dlp with arguments: {}.', yt_dlp_args)
    proc = subprocess.run(yt_dlp_args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError('Downloading media {} with yt-dlp failed with code {}, stderr: {}.'.format(media_url, proc.returncode, proc.stderr))

    media_output_path = proc.stdout.strip()
    logger.debug('Media downloaded to {}.', media_output_path)
    
    thumbnail_path = None
    if get_thumbnail:
        thumbnail_path = Path(media_output_path).stem + '.jpg'
        thumbnail_path = Path(destination_directory).joinpath(thumbnail_path)

    os.chdir(orig_wd)

    return media_output_path, thumbnail_path
