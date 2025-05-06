import tomllib
from pathlib import Path
from logger import FileLogger
from mutagen._file import File
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3._util import ID3NoHeaderError

TOML_PATH = Path("config.toml")
logger = FileLogger(str(Path("local_files") / "local_files.log"))


class Config:
    def __init__(self) -> None:
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        # Get media path from local_files section, default to None if not found
        self.media_path = None
        if "local_files" in config and "path" in config["local_files"]:
            raw_path = config["local_files"]["path"].replace("\\", "")
            self.media_path = Path(raw_path)

        # Discogs config
        discogs_config = config["discogs"]
        self.token = discogs_config["token"]
        self.overwrite_year = discogs_config["overwrite_year"]
        self.overwrite_genre = discogs_config["overwrite_genre"]
        self.embed_cover = discogs_config["embed_cover"]
        self.overwrite_cover = discogs_config["overwrite_cover"]
        self.rename_file = discogs_config["rename_file"]

    @staticmethod
    def write(config_data: dict) -> None:
        """write toml file with current vars"""
        with open(TOML_PATH, "w") as f:
            f.write("[common]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')
            f.write("[discogs]\n")
            f.write(f'token = "{config_data["token"]}"\n')
            f.write(f"overwrite_year = {str(config_data['overwrite_year']).lower()}\n")
            f.write(
                f"overwrite_genre = {str(config_data['overwrite_genre']).lower()}\n"
            )
            f.write(f"embed_cover = {str(config_data['embed_cover']).lower()}\n")
            f.write(
                f"overwrite_cover = {str(config_data['overwrite_cover']).lower()}\n"
            )
            f.write(f"rename_file = {str(config_data['rename_file']).lower()}\n")


def get_audio_files(directory: Path) -> list[Path]:
    """Get all audio files in directory and subdirectories"""
    audio_extensions = {".mp3", ".m4a", ".flac", ".ogg", ".wav"}
    return [
        f
        for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]


def get_track_info(file_path: Path) -> tuple[str, str] | None:
    """Get artist and title from audio file tags"""
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
