from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from logger import FileLogger

logger = FileLogger("discogs/discogs.log")


class MusicFile:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.suffix: str = path.suffix
        self.artist: str = ""
        self.title: str = ""
        self._get_tags()

    def _get_tags(self) -> None:
        """Extract artist and title tags from music files"""
        if self.suffix == ".flac":
            try:
                audio = FLAC(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
            except Exception as e:
                logger.error(f"Error reading FLAC tags: {e}")

        elif self.suffix == ".mp3":
            try:
                audio = EasyID3(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
            except Exception as e:
                logger.error(f"Error reading MP3 tags: {e}")

        elif self.suffix == ".m4a":
            try:
                audio = MP4(self.path)
                self.artist = audio["\xa9ART"][0]
                self.title = audio["\xa9nam"][0]
            except Exception as e:
                logger.error(f"Error reading M4A tags: {e}")
