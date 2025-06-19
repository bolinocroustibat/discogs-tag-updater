import os
import sys
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from local_files.common import logger, AUDIO_FILES_EXTENSIONS
from discogs import DTag


def update_tags_from_discogs(directory: Path, config=None, ds=None) -> None:
    """Update music file tags using Discogs metadata.

    Main function that processes all audio files in the specified directory,
    searches for matching releases on Discogs, and updates the file tags
    with metadata including genres, year, and cover art.

    The function creates DTag instances for each audio file, searches Discogs
    for matching releases, and updates the file tags based on the configuration
    settings. It also optionally renames files if the rename_file option is enabled.

    Args:
        directory: Path to the directory containing audio files to process.
        config: Configuration object containing Discogs and file processing settings.
        ds: Authenticated Discogs client instance.

    Raises:
        ValueError: If config or ds parameters are not provided.
        SystemExit: If the directory doesn't exist or is invalid.

    Note:
        - Processes all supported audio files recursively in the directory
        - Uses fuzzy matching to find the best Discogs release for each track
        - Updates genres, year, and cover art based on configuration settings
        - Optionally renames files to 'artist - title.ext' format
        - Provides detailed progress tracking and summary statistics
        - Respects API rate limits with built-in delays and retry logic
    """
    if not config or not ds:
        raise ValueError("config and ds parameters are required")

    # check if directory path exists and valid
    if not directory.is_dir():
        logger.error(f'Directory "{directory}" not found.')
        sys.exit(1)

    # create discogs session
    me = ds.identity()
    logger.log(f"Discogs User: {me}")

    logger.log(f"Looking for files in {directory}")
    logger.warning("Indexing audio files... Please wait\n")
    not_found: int = 0
    found: int = 0
    renamed: int = 0
    total: int = 0
    files = {
        DTag(path=p, suffix=p.suffix, filename=p.name, config=config, ds=ds)
        for p in Path(directory).glob("**/*")
        if p.suffix in AUDIO_FILES_EXTENSIONS
    }

    logger.info("\nProcessing files...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        for tag_file in files:
            total += 1
            logger.log(
                "____________________________________________________________________\n"
                + f"File: {tag_file.filename}"
            )

            # Rename file
            new_filename_start: str = f"{tag_file.artist} - {tag_file.title}"
            if (
                config.rename_file
                and tag_file.artist
                and tag_file.title
                and (
                    not tag_file.filename.startswith(new_filename_start)
                )  # TODO: improve with regex to keep the parenthesis and brackets
            ):
                new_filename: str = f"{new_filename_start}{tag_file.suffix}"
                new_path: Path = Path(tag_file.path).parent / new_filename
                os.rename(tag_file.path, new_path)
                tag_file.path = new_path
                renamed += 1
                logger.success(f"Renamed: {tag_file.filename} ➔ {new_filename}")

            # Search on Discogs and update
            if tag_file.search() is None:
                tag_file.save()
                found += 1
            else:
                not_found += 1

            # Print file results info
            if tag_file.genres_updated:
                logger.success(f"- Genres: {tag_file.local_genres} ➔ {tag_file.genres}")
            else:
                logger.log(f"- Genres: {tag_file.local_genres} ➔ not updated")

            if tag_file.year_updated:
                logger.success(f"- Year: {tag_file.local_year} ➔ {tag_file.year}")
            else:
                logger.log(f"- Year: {tag_file.local_year} ➔ not updated")

            if tag_file.cover_updated:
                logger.success("- Cover: ➔ updated\n")
            else:
                logger.log("- Cover: ➔ not updated\n")

            progress.advance(task)

    logger.log(f"Total files: {total}")
    logger.success(f"With Discogs info found: {found}")
    logger.error(f"With Discogs info not found: {not_found}")
    logger.warning(f"Renamed: {renamed}\n")
    input("Press Enter to exit...")
