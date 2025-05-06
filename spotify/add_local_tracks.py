import sys
from pathlib import Path
import time

from tqdm import tqdm

from spotify.common import (
    Config,
    setup_spotify,
    logger,
    select_playlist,
    search_spotify,
    select_match,
)
from discogs.music_file import MusicFile

config = Config()


def main() -> None:
    # Initialize Spotify client
    sp = setup_spotify()

    # Get playlist ID from config or user selection
    playlist_id = select_playlist(sp, config.playlist_id)

    # Check if media path is set
    if not config.media_path:
        logger.error("Media path is not set")
        sys.exit(1)

    # Scan directory for music files
    music_files: list[MusicFile] = [
        MusicFile(p)
        for p in sorted(
            Path(config.media_path).glob("**/*"), key=lambda x: x.name.lower()
        )
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
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            if item["track"] and item["track"]["id"]:
                existing_tracks.add(item["track"]["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break

    # Process each music file
    logger.info("\nProcessing files...")
    for music_file in tqdm(music_files, desc="Processing files", unit="file"):
        matches = search_spotify(
            sp, music_file.title, music_file.artist, music_file.path.name
        )
        if matches:
            track_id = select_match(sp, matches)
            if track_id:
                if track_id in existing_tracks:
                    logger.warning(
                        "Track already exists in Spotify playlist - skipping"
                    )
                    tracks_skipped += 1
                    continue

                try:
                    sp.playlist_add_items(playlist_id, [track_id])
                    logger.success("Track added to Spotify playlist.")
                    tracks_added += 1
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error adding to Spotify playlist: {e}")
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to Spotify: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    main()
