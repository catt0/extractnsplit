#!/usr/bin/env python3

from loguru import logger
from typing import List
from pathlib import Path
import os
import subprocess
import multiprocessing
from functools import partial

from timestamps import format_timestamp

# Wrapper class to hold all the config options
class SplitConfig:
    def __init__(self, args = None):
        self.num_threads = args.split_num_threads if args is not None else 0
        self.start_offset = args.split_start_offset if args is not None else 1
        self.fade_in = args.split_fade_in if args is not None else 2
        self.end_offset = args.split_end_offset if args is not None else -1
        self.fade_out = args.split_fade_out if args is not None else 3
        self.file_pattern = args.split_file_pattern if args is not None else r'fragment_%n'
        if self.num_threads == 0:
            self.num_threads = multiprocessing.cpu_count()

    def has_fade(self) -> bool:
        return self.fade_in != 0 or self.fade_out != 0

def check_arguments(args) -> bool:
    if r'%n' not in args.split_file_pattern:
        print(r'--split-file-pattern must contain at least one %n.')
        return False
    # dummy call in case more verification is later added to the constructor of SplitConfig
    dummy = SplitConfig(args)
    logger.trace('Created config object {}.', dummy)

    logger.trace('Checking ffmpeg by executing ffmpeg -version.')
    subprocess.check_call(['ffmpeg', '-version'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    logger.trace('ffmpeg is available.')

    return True


def get_config_from_arguments(args) -> SplitConfig:
    return SplitConfig(args)


def split_file(media_file_path: str, config : SplitConfig, proto_ffmpeg_args : List[str], timestamps: List[int], index: int):
    media_file_extension = Path(media_file_path).suffix
    media_file_name = Path(Path(media_file_path).name).stem

    start = timestamps[index] + config.start_offset
    # the fade in starts right at the start of the fragment
    fadestart = start

    end = 0xffffffff
    fadeend = end

    if index < len(timestamps) - 1:
        end = timestamps[index + 1] - config.end_offset
        # need to substract the fade start of the fade out
        # because it needs to start earlier than the end
        fadeend = end - config.fade_out

    end_str = format_timestamp(end) if end != 0xffffffff else '<END>'
    from_to_str = '{} to {}'.format(format_timestamp(start), end_str)
    logger.trace('Splitting fragment index {} from {}.', index, from_to_str)

    my_args = proto_ffmpeg_args[:]

    if config.has_fade():
        my_args[-2] = my_args[-2].format(fadestart, fadeend)

    new_args = [None, '-to', None, None]
    new_args[0] = str(start)
    new_args[2] = str(end)

    # replace % placeholders with references to variables
    file_pattern = config.file_pattern[:]
    file_pattern = file_pattern.replace(r'%n', '{index}')
    file_pattern = file_pattern.replace(r'%f', '{media_file_name}')
    file_name = file_pattern.format(index=index, media_file_name=media_file_name) + media_file_extension
    new_args[3] = file_name
    my_args.extend(new_args)
    cmdline = ' '.join(my_args)
    logger.trace('ffmpeg call for index {}, from {}: {}.', index, from_to_str, cmdline)
    proc = subprocess.run(my_args, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error('Failed processing fragment index {} (from {}) with code {}. stdout: {}, stderr: {}.', index, from_to_str, proc.returncode, proc.stdout, proc.stderr)
        return None
    logger.trace('Split fragment index {} (from {}) to {}.', index, from_to_str, file_name)
    return file_name


def split_files(media_file_path: str, timestamps: List[int], split_destination_directory: str, config: SplitConfig) -> List[str]:
    old_wd = os.getcwd()
    media_file_path = str(Path(media_file_path).resolve())
    os.chdir(split_destination_directory)

    proto_ffmpeg_args = [
        'ffmpeg',
        '-loglevel',
        'error',
        '-y',
        '-hide_banner',
        '-i',
        media_file_path,
    ]
    if config.has_fade():
        proto_ffmpeg_args.extend([
            '-af',
            'afade=t=in:st={{}}:d={},afade=t=out:st={{}}:d={}'.format(
                config.fade_in, config.fade_out),
        ])
    proto_ffmpeg_args.extend([
        '-ss',
    ])

    pool = multiprocessing.Pool(config.num_threads)
    # need to map a new iterable over the indicies
    # each iteration needs access to the full timestamp list
    single_iteration_partial = partial(split_file, media_file_path, config, proto_ffmpeg_args, timestamps)
    logger.trace('Starting splitting with {} threads.', config.num_threads)
    raw_rets = pool.map(single_iteration_partial, range(len(timestamps)))
    logger.debug('Split into {} fragments.', len(raw_rets))

    result_file_paths = []
    for f in raw_rets:
        if f is None:
            continue
        abs_path = str(Path(f).resolve(True))
        logger.trace('Resolved {} to {}.', f, abs_path)
        result_file_paths.append(abs_path)
    
    os.chdir(old_wd)
    return result_file_paths
