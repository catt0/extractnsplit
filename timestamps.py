#!/usr/bin/env python3

from loguru import logger
from typing import List
from sys import stdin
import re
import datetime


class Pattern:
    def __init__(self):
        self.pattern = None

    def process(self, m):
        return None

    def match(self, str):
        m = self.pattern.search(str)
        if not m:
            return None
        return self.process(m)


class Pattern1(Pattern):
    def __init__(self):
        self.pattern = re.compile(r'(\d{1,2}):(\d{1,2}):(\d{1,2})')

    def process(self, m):
        hours = int(m.group(1))
        minutes = int(m.group(2))
        seconds = int(m.group(3))

        totalseconds = seconds + minutes * 60 + hours * 3600
        return totalseconds, m.start()

class Pattern2(Pattern):
    def __init__(self):
        self.pattern = re.compile(r'(\d{1,2}):(\d{1,2})')

    def process(self, m):
        minutes = int(m.group(1))
        seconds = int(m.group(2))

        totalseconds = seconds + minutes * 60
        return totalseconds, m.start()

class Pattern3(Pattern):
    def __init__(self):
        self.pattern = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')

    def process(self, m):
        hours = int(m.group(1))
        minutes = int(m.group(2))
        seconds = int(m.group(3))

        totalseconds = seconds + minutes * 60 + hours * 3600
        return totalseconds, m.start()

class Pattern4(Pattern):
    def __init__(self):
        self.pattern = re.compile(r'(\d{1,2})\.(\d{1,2})')

    def process(self, m):
        minutes = int(m.group(1))
        seconds = int(m.group(2))

        totalseconds = seconds + minutes * 60
        return totalseconds, m.start()

patterns = [
    Pattern1(),
    Pattern2(),
    Pattern3(),
    Pattern4(),
]

def check_arguments(args) -> bool:
    return True


def format_timestamp(seconds: int) -> str:
    return str(datetime.timedelta(seconds=seconds))

def get_timestamps(timestamps_file_path: str) -> List[int]:
    logger.trace('Parsing timestamps from {}.', timestamps_file_path)
    lines = []
    if timestamps_file_path == 'stdin':
        print('Paste timestamps below. Terminate with two empty lines or EOF (CTRL-D).')
        empty_lines = 0
        # loops until EOF
        for line in stdin:
            # break after two empty lines
            if len(line.strip()) == 0:
                empty_lines += 1
                if empty_lines >= 2:
                    break
                continue
            
            empty_lines = 0
            lines.append(line.strip())
    else:
        lines = list(open(timestamps_file_path, 'r').readlines())
    
    logger.trace('Read {} lines from {}.', len(lines), timestamps_file_path)
    
    timestamps = []
    for line in lines:
        matches = []
        if len(line.strip()) == 0:
            continue
        logger.trace('Matching line "{}".', line)
        for pattern in patterns:
            m = pattern.match(line)
            if m is not None:
                matches.append(m)
        logger.trace('Matches: {}.', matches)
        if len(matches) > 0:
            seconds = min(matches, key=lambda v : v[1])[0]
            timestamps.append(seconds)
            logger.trace('Found timestamp {} ({}) in "{}".', seconds, format_timestamp(seconds), line)
    
    logger.debug('Parsed {} timestamps from {}.', len(timestamps), timestamps_file_path)
    return timestamps
