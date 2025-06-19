import sys
import tomllib
from pathlib import Path
import re
import inquirer

from local_files.common import logger, get_audio_files, get_track_info


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, "_", filename)


def rename_file(file_path: Path, artist: str, title: str) -> tuple[bool, bool]:
    """Rename file to 'artist - title.ext' format

    Returns:
        tuple[bool, bool]: (was_renamed, was_skipped)
    """
    try:
        # Sanitize artist and title
        artist = sanitize_filename(artist)
        title = sanitize_filename(title)

        # Create new filename
        new_name = f"{artist} - {title}{file_path.suffix}"
        new_path = file_path.parent / new_name

        # Skip if filename is already correct
        if file_path.name == new_name:
            logger.info(f"File already correctly named: {file_path}")
            return False, False

        # Check if target file already exists
        if new_path.exists():
            logger.warning(f"Target file already exists: {new_path}")
            return False, True

        # Ask for confirmation
        questions = [
            inquirer.Confirm(
                "confirm",
                message=f"Rename '{file_path.name}' to '{new_name}'?",
                default=True,
            ),
        ]
        answers = inquirer.prompt(questions)
        if not answers or not answers["confirm"]:
            logger.info(f"Skipping rename of: {file_path}")
            return False, True

        # Rename file
        file_path.rename(new_path)
        logger.success(f"Renamed: {file_path.name} -> {new_name}")
        return True, False

    except Exception as e:
        logger.error(f"Error renaming {file_path}: {e}")
        return False, True


def rename_files_from_tags() -> None:
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
    audio_files = get_audio_files(media_path)
    if not audio_files:
        logger.error("No audio files found")
        sys.exit(1)

    logger.info(f"Found {len(audio_files)} audio files")

    # Process each file
    renamed = 0
    skipped = 0
    already_correct = 0
    for file_path in audio_files:
        track_info = get_track_info(file_path)
        if track_info:
            artist, title = track_info
            was_renamed, was_skipped = rename_file(file_path, artist, title)
            if was_renamed:
                renamed += 1
            elif was_skipped:
                skipped += 1
            else:
                already_correct += 1
        else:
            skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Files renamed: {renamed}")
    logger.info(f"Files already correctly named: {already_correct}")
    logger.warning(f"Files skipped: {skipped}")


if __name__ == "__main__":
    rename_files_from_tags()
