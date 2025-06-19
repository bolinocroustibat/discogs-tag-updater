import sys
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from ytmusic import (
    Config,
    setup_ytmusic,
    select_playlist,
    search_ytmusic_track,
    select_match,
    add_track_to_ytmusic,
)
from logger import FileLogger
from local_files.music_file import MusicFile

config = Config()
logger = FileLogger(Path("scripts") / "local_to_ytmusic.log")


def main() -> None:
    # Initialize YouTube Music client
    ytm = setup_ytmusic()

    # Get playlist ID from config or user selection
    playlist_id = select_playlist(ytm, config.playlist_id)

    # Check if media path is set
    if not config.media_path:
        logger.error("Media path is not set")
        sys.exit(1)

    # Scan directory for music files
    music_files: list[MusicFile] = [
        MusicFile(p)
        for p in sorted(config.media_path.rglob("*"), key=lambda x: x.name.lower())
        if p.suffix.lower() in [".flac", ".mp3", ".m4a"]
    ]

    logger.info(f"Found {len(music_files)} music files in {config.media_path}")

    if not music_files:
        logger.warning("No local .mp3, .flac, or .m4a files found in directory")
        sys.exit(1)

    tracks_added = 0
    tracks_skipped = 0

    # Get existing tracks in playlist
    logger.info("Fetching existing tracks from playlist...")
    existing_tracks: set[str] = set()
    results = ytm.get_playlist(playlist_id)
    for track in results["tracks"]:
        if track.get("videoId"):
            existing_tracks.add(track["videoId"])

    # Process each music file
    logger.info("\nProcessing files...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(music_files))
        for music_file in music_files:
            matches = search_ytmusic_track(
                ytm, music_file.title, music_file.artist, music_file.path.name
            )
            if matches:
                track_id = select_match(ytm, matches)
                if track_id:
                    if track_id in existing_tracks:
                        logger.warning(
                            "Track already exists in YouTube Music playlist - skipping"
                        )
                        tracks_skipped += 1
                        progress.advance(task)
                        continue

                    success, _ = add_track_to_ytmusic(ytm, track_id, playlist_id, 1)
                    if success:
                        tracks_added += 1
                    else:
                        tracks_skipped += 1
                else:
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
            progress.advance(task)

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to YouTube Music: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    main()
