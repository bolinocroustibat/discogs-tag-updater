import sys
import time
from pathlib import Path

import spotipy

from spotify.common import setup_spotify, logger, select_playlist


def find_duplicates(sp: spotipy.Spotify, playlist_id: str) -> dict:
    """Find duplicate tracks in a playlist"""
    logger.info("Fetching playlist tracks...")

    # Get all tracks from playlist
    tracks = {}  # key: track_id, value: list of [track_info, added_at]
    results = sp.playlist_items(
        playlist_id,
        fields="items.track.id,items.track.name,items.track.artists,items.added_at,next",
    )

    while results:
        for item in results["items"]:
            if not item["track"]:  # Skip empty tracks
                continue

            track = item["track"]
            track_id = track["id"]
            artist = (
                track["artists"][0]["name"] if track["artists"] else "Unknown Artist"
            )
            track_name = f"{track['name']} - {artist}"  # Keep for display purposes

            if track_id in tracks:
                tracks[track_id].append(
                    {"name": track_name, "added_at": item["added_at"]}
                )
            else:
                tracks[track_id] = [{"name": track_name, "added_at": item["added_at"]}]

    # Filter only duplicates
    duplicates = {k: v for k, v in tracks.items() if len(v) > 1}
    return duplicates


def remove_duplicates(sp: spotipy.Spotify, playlist_id: str, duplicates: dict) -> None:
    """Remove duplicate tracks keeping the oldest one"""
    if not duplicates:
        return

    tracks_to_remove = []
    for track_name, instances in duplicates.items():
        # Sort by added_at date in ascending order (oldest first, newest last)
        sorted_by_date = sorted(instances, key=lambda x: x["added_at"])
        # Keep the first (oldest) track and remove all newer duplicates
        newest_duplicates = sorted_by_date[1:]
        tracks_to_remove.extend([t["id"] for t in newest_duplicates])

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
        f"\nFound {sum(len(v)-1 for v in duplicates.values())} duplicate tracks:"
    )
    for track_name, instances in duplicates.items():
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
