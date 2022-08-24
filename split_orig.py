#!/usr/bin/env python3

import re
from pprint import pprint
import sys
from pathlib import Path
import subprocess
from functools import partial
from multiprocessing.dummy import Pool
import multiprocessing

from loguru import logger

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

mediafile = sys.argv[1]
timestampfile = sys.argv[2]

timestamps = []
for line in open(timestampfile, 'r').readlines():
    matches = []
    for pattern in patterns:
        m = pattern.match(line)
        if m is not None:
            matches.append(m)
    if len(matches) > 0:
        seconds = min(matches, key=lambda v : v[1])[0]
        timestamps.append(seconds)

pprint(timestamps)
targetfolder = Path(mediafile).parent
extension = Path(mediafile).suffix
print(targetfolder)
print(extension)
args = [
    'ffmpeg',
    '-loglevel',
    'error',
    '-y',
    '-hide_banner',
    '-i',
    mediafile,
    '-af',
    'afade=t=in:st={}:d=3,afade=t=out:st={}:d=3',
    '-ss',
]

commands = []

for i in range(len(timestamps)):
    start = timestamps[i] + 1
    fadestart = start
    end = 0xffffffff
    fadeend = end
    if i < len(timestamps) - 1:
        end = timestamps[i + 1] - 1
        fadeend = end - 3
    my_args = args[:]
    my_args[-2] = my_args[-2].format(fadestart, fadeend)
    new_args = [None, '-to', None, None]
    new_args[0] = str(start)
    new_args[2] = str(end)
    new_args[3] = '{}/part_{}{}'.format(targetfolder, i, extension)
    my_args.extend(new_args)
    cmdline = ' '.join(my_args)
    print(cmdline)
    commands.append(my_args[:])

pool = Pool(multiprocessing.cpu_count())
