from pathlib import Path
from local_files.logger import logger
from mutagen._file import File
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3._util import ID3NoHeaderError

AUDIO_FILES_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".wav"}


def get_audio_files(directory: Path) -> list[Path]:
    """Get all audio files in directory and subdirectories.

    Recursively searches through the given directory and all its subdirectories
    to find files with supported audio extensions.

    Args:
        directory: The root directory to search for audio files.

    Returns:
        A list of Path objects representing audio files found in the directory
        and its subdirectories.

    Note:
        Supported audio formats: .mp3, .m4a, .flac, .ogg, .wav
    """
    return [
        f
        for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_FILES_EXTENSIONS
    ]


def get_track_info(file_path: Path) -> tuple[str, str] | None:
    """Get artist and title from the tags of an audio file.

    Attempts to extract artist and title metadata from various audio file formats.
    Uses different strategies depending on the file type for optimal tag reading.

    Args:
        file_path: Path to the audio file to read tags from.

    Returns:
        A tuple of (artist, title) strings if both tags are found and valid,
        None if either tag is missing or the file cannot be read.

    Raises:
        Exception: If there's an error reading the file or tags.

    Note:
        - For MP3 files, uses EasyID3 first (more reliable), then falls back to generic tags
        - For other formats, uses the generic mutagen File interface
        - Logs warnings for missing tags and errors for file reading issues
    """
    try:
        audio = File(file_path)
        if audio is None:
            logger.error(f"Could not read audio file: {file_path}")
            return None

        # Try EasyID3 first (more reliable for MP3)
        if isinstance(audio, MP3):
            try:
                tags = EasyID3(file_path)
                if tags is not None:
                    artist = tags.get("artist", [""])[0]
                    title = tags.get("title", [""])[0]
                    if artist and title:
                        return artist, title
            except ID3NoHeaderError:
                pass

        # Fallback to generic tags
        if hasattr(audio, "tags") and audio.tags is not None:
            artist = audio.tags.get("TPE1", [""])[0]
            title = audio.tags.get("TIT2", [""])[0]
            if artist and title:
                return artist, title

        logger.warning(f"Missing artist or title tags in: {file_path}")
        return None

    except Exception as e:
        logger.error(f"Error reading tags from {file_path}: {e}")
        return None
