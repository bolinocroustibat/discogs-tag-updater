import sys
import tomllib
from pathlib import Path

from local_files import logger, get_music_files, MusicFile, rename_file


def rename_files_from_tags() -> None:
    """Rename music files based on their ID3 tags.

    Main function that processes all audio files in the configured media directory.
    For each file, extracts artist and title information from the file's metadata
    and renames it to follow the 'artist - title.ext' format.

    The function reads the media directory path from config.toml and processes
    all supported audio files recursively. It provides user confirmation for
    each rename operation and generates a summary of the results.

    Raises:
        SystemExit: If the configuration file is missing, invalid, or if the
                   media directory doesn't exist.

    Note:
        - Reads media directory path from config.toml [local_files] section
        - Processes all audio files in the directory and subdirectories
        - Prompts user for confirmation before each rename
        - Provides detailed logging and summary statistics
        - Skips files that cannot be read or have missing tags
    """
    # Get media directory from config
    config_path = Path("config.toml")
    if not config_path.is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            media_path = Path(config["local_files"]["path"].replace("\\", ""))
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        sys.exit(1)

    if not media_path.is_dir():
        logger.error(f"Media directory not found: {media_path}")
        sys.exit(1)

    # Show media path to user
    logger.info(f"Using media directory: {media_path}")

    # Get all audio files
    audio_files: list[MusicFile] = get_music_files(media_path)
    if not audio_files:
        logger.error("No audio files found")
        sys.exit(1)

    logger.info(f"Found {len(audio_files)} audio files")

    # Process each file
    renamed = 0
    skipped = 0
    already_correct = 0
    for music_file in audio_files:
        # Check if we have valid artist and title tags
        if music_file.artist and music_file.title:
            was_renamed, was_skipped = rename_file(music_file)
            if was_renamed:
                renamed += 1
            elif was_skipped:
                skipped += 1
            else:
                already_correct += 1
        else:
            logger.warning(f"Missing artist or title tags in: {music_file.path}")
            skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Files renamed: {renamed}")
    logger.info(f"Files already correctly named: {already_correct}")
    logger.warning(f"Files skipped: {skipped}")


if __name__ == "__main__":
    rename_files_from_tags()
