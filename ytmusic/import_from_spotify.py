import sys
from pathlib import Path
import time

from ytmusicapi import YTMusic
from tqdm import tqdm

from spotify.common import (
    Config as SpotifyConfig,
    setup_spotify,
    logger,
    select_playlist as select_spotify_playlist,
    get_spotify_track_details,
)
from ytmusic.common import (
    Config as YTMusicConfig,
    setup_ytmusic,
    select_playlist as select_ytmusic_playlist,
    get_ytmusic_track_ids,
    search_ytmusic_tracks,
    select_match,
)

spotify_config = SpotifyConfig()
ytmusic_config = YTMusicConfig()


def add_track_to_ytmusic(
    ytm: YTMusic,
    video_id: str,
    ytmusic_playlist_id: str,
    retry_delay: int,
) -> tuple[bool, int]:
    """Add track to YouTube Music playlist with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if ytmusic_playlist_id == "LM":
                # Special case for Liked Music - use rate_song instead of add_playlist_items
                ytm.rate_song(video_id, "LIKE")
            else:
                # Regular playlist
                ytm.add_playlist_items(ytmusic_playlist_id, [video_id])
            logger.success("Track added to YouTube Music playlist.")
            time.sleep(2)  # Increased delay between requests
            return True, retry_delay
        except Exception as e:
            if "rate/request limit" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Rate limit reached. Waiting {retry_delay} seconds before retry..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error("Max retries reached for rate limit. Skipping track.")
                    return False, retry_delay
            else:
                logger.error(f"Error adding to YouTube Music playlist: {e}")
                logger.error(f"Video ID: {video_id}")
                logger.error(f"Playlist ID: {ytmusic_playlist_id}")
                return False, retry_delay
    return False, retry_delay


def process_tracks(
    ytm: YTMusic,
    tracks: list[dict],
    existing_tracks: set[str],
    ytmusic_playlist_id: str,
) -> tuple[int, int]:
    """Process all tracks and return counts of added and skipped tracks"""
    tracks_added = 0
    tracks_skipped = 0
    auto_first = False
    retry_delay = 5  # Initial delay in seconds

    logger.info("\nProcessing tracks...")
    for track in tqdm(tracks, desc="Processing tracks", unit="track"):
        track_name = track["name"]
        artist_name = track["artist"]

        matches = search_ytmusic_tracks(ytm, track_name, artist_name)
        if matches:
            video_id = select_match(ytm, matches, auto_first)
            if video_id:
                if video_id in existing_tracks:
                    logger.warning(
                        "Track already exists in YouTube Music playlist - skipping"
                    )
                    tracks_skipped += 1
                    continue

                success, retry_delay = add_track_to_ytmusic(
                    ytm, video_id, ytmusic_playlist_id, retry_delay
                )
                if success:
                    tracks_added += 1
                else:
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    return tracks_added, tracks_skipped


def main() -> None:
    # Initialize YouTube Music client
    ytm = setup_ytmusic()

    # Get YouTube Music playlist ID from config or user selection
    ytmusic_playlist_id = select_ytmusic_playlist(ytm, ytmusic_config.playlist_id)

    # Initialize Spotify client
    sp = setup_spotify()

    # Get Spotify playlist ID from config or user selection
    spotify_playlist_id = select_spotify_playlist(sp, spotify_config.playlist_id)

    # Get tracks from Spotify playlist
    tracks = get_spotify_track_details(sp, spotify_playlist_id)

    # Get existing tracks in YouTube Music playlist
    existing_tracks = get_ytmusic_track_ids(ytm, ytmusic_playlist_id)

    # Process tracks
    tracks_added, tracks_skipped = process_tracks(
        ytm, tracks, existing_tracks, ytmusic_playlist_id
    )

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to YouTube Music: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
