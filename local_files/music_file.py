from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from local_files.logger import logger


class MusicFile:
    """Represents a music file with metadata extraction capabilities.

    This class provides a unified interface for reading artist and title tags
    from various audio file formats including MP3, FLAC, and M4A.

    Attributes:
        path: The file path of the music file.
        suffix: The file extension (e.g., '.mp3', '.flac').
        artist: The artist name extracted from the file tags.
        title: The track title extracted from the file tags.
    """

    def __init__(self, path: Path) -> None:
        """Initialize a MusicFile instance and extract metadata.

        Args:
            path: Path to the music file to process.

        Note:
            Automatically calls _get_tags() to extract artist and title
            information from the file upon initialization.
        """
        self.path: Path = path
        self.suffix: str = path.suffix
        self.artist: str = ""
        self.title: str = ""
        self._get_tags()

    def _get_tags(self) -> None:
        """Extract artist and title tags from music files.

        Reads metadata from the music file based on its format. Supports
        FLAC, MP3, and M4A files. Sets the artist and title attributes
        if the tags are successfully read.

        Note:
            - FLAC: Reads from FLAC metadata tags
            - MP3: Reads from ID3 tags using EasyID3
            - M4A: Reads from MP4 metadata tags
            - Logs errors if tag reading fails for any format
        """
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
