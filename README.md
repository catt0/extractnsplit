# extractnsplit - extract and split mixes into individual songs
This tool can be used to:

1. download media from [yt-dlp](https://github.com/yt-dlp/yt-dlp) supported sites,
2. split the file based on timestamps into individual songs with [ffmpeg](https://ffmpeg.org/),
3. recognize the songs using [SongRec](https://github.com/marin-m/SongRec),
4. rename the files based on the song,
5. tag the files with the proper metadata (e.g. ID3) with [music-tag](https://github.com/KristoforMaynard/music-tag),
6. create a playlist of the songs.

# Dependencies
You need the following native programs installed:

- yt-dlp - for downloading the media, not needed if only processing local files
- ffmpeg - for converting and cutting media files
- SongRec - for recognizing the songs
- Python >= 3.9 - to run this program

The following Python packages are required:

- loguru - logging library
- music-tag - wrapper around [Mutagen](https://github.com/quodlibet/mutagen) for tagging

You can use the provided Pipfile to simplify the python setup, e.g. with pipenv:
1. Clone/download this repo and unpack if needed
2. cd into the folder containing the main.py
3. run pipenv shell
4. run python main.py -h

# Simple usage
You will always need 1) a media file and 2) a list of timestamps.
To get 1) either download one manually or provide it via an URL supported by yt-dlp.
For 2) your best bet is checking comments on the file, e.g. YouTube comments or descriptions often have a track list.

The simplest usage is:
```python main.py https://youtube.com/watch?v=<ID> timestamps.txt```
This will download the video, convert it into an mp3 file and split it based on the timestamps in timestamps.txt. The output will be placed in a new folder named after the video and placed next to the timestamps.txt file.

If you are browsing for videos you can use this command without having to create the timestamps file:
```python main.py --dest <folder_name> https://youtube.com/watch?v=<ID> stdin```
The program will ask you to paste the timestamps into the console. Confirm the input either with two empty lines or with EOF (CTRL+D). In this case you need to specify the destination folfder as there is no local file to use as a reference point.

In both cases a playlist named after the media file will be created next to the individual tracks. The playlist is ordered the same as in the input mix.

# Timestamps
The program supports the most common formats found:

- hh:mm:ss
- mm:ss
- hh.mm.ss
- mm.ss

It will always use the first timestamp found on a line and then move to the next line. Anything after the timestamp is ignored, including other timestamps on the same line. Each timestamp marks the start of a track. Formats can be mixed in the same file.

# Advanced usage
The program supports multiple options, view them with the -h switch.

As timestamps are often human created and only second accurate, there is some inherent inaccuracy. By default the program tries to hide this by fading the tracks in and out. It also cuts off a second at the beginning and end of each track. I find it less annoying to have a fade into an already started song or lose a second at the end instead of hearing the last second of a previous song before the actual song starts.

You can control these timings with:
- --split-start-offset
- --split-fade-in
- --split-end-offset
- --split-fade-out

A special case is setting both fade times to 0. In this case ffmpeg can copy the stream over directly, saving a lot of transcoding time. If you are experimenting this can save a lot of time, especially if combined with providing the already downloaded and converted file instead of a link as source.

By default the playlist is created in the same folder as the output files. However you can also enable a playlist that goes in the partent folder of that folder. It will then reference the tracks relative to this parent folder.

Control the playlist creation with these options, both and none can be provided:
- --playlist-create-same-folder
- --playlist-create-parent-folder

The patterns used for naming the tracks before recognition and after can be configured. Each option supports a set of placeholders like title and track number. In case a recognition fails, the file will use "Unknown Artist" and similar. See the help output for the following arguments:
- --split-file-pattern
- --rename-name-pattern

The splitting and recognizing can potentially take a long time to complete. By default these steps are using multiple threads. The split by default uses all available cores, each split (with a potential re-encode due to fade in/out) is single threaded itself. The calls to SongRec by default use 8 threads. In my tests with fast quite fast and did not trigger any API limits of Shazam. You can tweak both parameters using these arguments:
- --split-num-threads
- --recognize-num-threads

# Recognition details
This program used [SongRec](https://github.com/marin-m/SongRec) which in turn uses [Shazam](https://www.shazam.com/). It only uploads a fingerprint of the file, not the entire file. The recognition is in general pretty fast and reliable. In case a track fails recognition, a second try is performed by cutting off the first 30s of the track and trying it with the following 60s. This should fix even fairly inaccurate timestamps. Even after this some songs will not be recognized. There is currently no way of fixing this. The files will still be playable and tagged, but only as "Unknown Artist" and similar. You can fix this manually, but if you also adjust the file names make sure to fix the playlist as well. As m3u is a simple ASCII file, this can be done with a text editor.
