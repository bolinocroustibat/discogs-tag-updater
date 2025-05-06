import sys
import time
from pathlib import Path
from typing import TypedDict

import spotipy

from spotify.common import setup_spotify, logger, select_playlist


class TrackInstance(TypedDict):
    name: str
    added_at: str


def find_duplicates(
    sp: spotipy.Spotify, playlist_id: str
) -> dict[str, list[TrackInstance]]:
    """Find duplicate tracks in a playlist"""
    logger.info("Fetching playlist tracks...")
    logger.info(f"Using playlist ID: {playlist_id}")

    # Special case for Liked Songs
    if playlist_id == "liked":
        logger.info("Note: Liked Songs cannot contain duplicates by design - Spotify automatically prevents this.")
        return {}

    # Get all tracks from playlist
    tracks: dict[
        str, list[TrackInstance]
    ] = {}  # key: track_id, value: list of [track_info, added_at]
    try:
        # Regular playlist
        results = sp.playlist_items(
            playlist_id,
            fields="items.track.id,items.track.name,items.track.artists,items.added_at,next",
        )
        logger.info("Successfully connected to Spotify API")
    except Exception as e:
        logger.error(f"Error fetching playlist items: {e}")
        return {}

    total_tracks = 0
    while results:
        try:
            batch_size = len(results["items"])
            total_tracks += batch_size
            logger.info(
                f"Processing batch of {batch_size} tracks (total: {total_tracks})"
            )

            for item in results["items"]:
                if not item["track"]:  # Skip empty tracks
                    continue

                track = item["track"]
                track_id = track["id"]
                artist = (
                    track["artists"][0]["name"]
                    if track["artists"]
                    else "Unknown Artist"
                )
                track_name = f"{track['name']} - {artist}"  # Keep for display purposes

                track_instance: TrackInstance = {
                    "name": track_name,
                    "added_at": item["added_at"],
                }

                if track_id in tracks:
                    tracks[track_id].append(track_instance)
                else:
                    tracks[track_id] = [track_instance]

            if results["next"]:
                logger.info("Fetching next batch of tracks...")
                results = sp.next(results)
            else:
                logger.info("Finished fetching all tracks")
                break
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            break

    # Filter only duplicates
    duplicates = {k: v for k, v in tracks.items() if len(v) > 1}
    logger.info(f"Found {len(duplicates)} tracks with duplicates")
    return duplicates


def remove_duplicates(
    sp: spotipy.Spotify, playlist_id: str, duplicates: dict[str, list[TrackInstance]]
) -> None:
    """Remove duplicate tracks keeping the oldest one"""
    if not duplicates:
        return

    tracks_to_remove: list[str] = []
    for track_id, instances in duplicates.items():
        # Sort by added_at date in ascending order (oldest first, newest last)
        sorted_by_date = sorted(instances, key=lambda x: x["added_at"])
        # Keep the first (oldest) track and remove all newer duplicates
        newest_duplicates = sorted_by_date[1:]
        # Add the track ID for each duplicate instance
        tracks_to_remove.extend([track_id] * len(newest_duplicates))

    if tracks_to_remove:
        try:
            # Spotify API can only remove 100 tracks at a time
            for i in range(0, len(tracks_to_remove), 100):
                chunk = tracks_to_remove[i : i + 100]
                sp.playlist_remove_all_occurrences_of_items(playlist_id, chunk)
                time.sleep(1)  # Rate limiting
            logger.success(
                f"Successfully removed {len(tracks_to_remove)} duplicate tracks"
            )
        except Exception as e:
            logger.error(f"Error removing tracks: {e}")


def main() -> None:
    sp = setup_spotify()

    # Get playlist ID from user selection
    playlist_id = select_playlist(sp)

    duplicates = find_duplicates(sp, playlist_id)

    if not duplicates:
        logger.success("No duplicates found!")
        return

    logger.info(
        f"\nFound {sum(len(v) - 1 for v in duplicates.values())} duplicate tracks:"
    )
    for track_id, instances in duplicates.items():
        # Get the track name from the first instance (they're all the same track)
        track_name = instances[0]["name"]
        logger.info(f"\n{track_name}")
        for i, track in enumerate(sorted(instances, key=lambda x: x["added_at"]), 1):
            logger.info(f"  {i}. Added on: {track['added_at']}")

    if input("\nDo you want to remove duplicates? (y/N): ").lower() == "y":
        remove_duplicates(sp, playlist_id, duplicates)


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
