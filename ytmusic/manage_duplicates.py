import sys
import time
from pathlib import Path
from typing import TypedDict

from ytmusicapi import YTMusic

from ytmusic.common import setup_ytmusic, logger, select_playlist


class TrackInfo(TypedDict):
    name: str
    videoId: str
    setVideoId: str


def find_duplicates(ytm: YTMusic, playlist_id: str) -> dict[str, list[TrackInfo]]:
    """Find duplicate tracks in a YouTube Music playlist"""
    logger.info("Fetching YouTube Music playlist tracks...")

    # Check if this is Liked Music playlist
    is_liked_music = playlist_id == "LM"
    if is_liked_music:
        logger.warning("Liked Music playlist cannot be modified directly. Please use a regular playlist.")
        return {}

    # Get all tracks from playlist
    tracks: dict[str, list[TrackInfo]] = {}  # key: video_id, value: list of track_info
    try:
        # First get basic playlist info
        playlist = ytm.get_playlist(playlist_id)
        logger.info(f"Successfully connected to YouTube Music API - Playlist: {playlist.get('title')}")

    except Exception as e:
        logger.error(f"Error accessing playlist: {e}")
        return {}

    total_tracks = 0
    try:
        for track in playlist["tracks"]:
            # Skip if track is not a dictionary
            if not isinstance(track, dict):
                continue

            if not track.get("videoId"):  # Skip empty tracks
                continue

            total_tracks += 1
            video_id = track["videoId"]
            
            # Safely get artist name with fallbacks
            artist = "Unknown Artist"
            if track.get("artists") and isinstance(track["artists"], list) and track["artists"]:
                artist = track["artists"][0].get("name", "Unknown Artist")
            
            # Safely get title
            title = track.get("title", "Unknown Title")
            track_name = f"{title} - {artist}"

            track_info: TrackInfo = {
                "name": track_name,
                "videoId": video_id,
                "setVideoId": track.get("setVideoId", video_id)  # Try to get setVideoId from track
            }

            if video_id in tracks:
                tracks[video_id].append(track_info)
            else:
                tracks[video_id] = [track_info]

        logger.info(f"Processed {total_tracks} tracks from YouTube Music playlist")
    except Exception as e:
        logger.error(f"Error processing tracks: {e}")
        return {}

    # Filter only duplicates
    duplicates = {k: v for k, v in tracks.items() if len(v) > 1}
    return duplicates


def remove_duplicates(ytm: YTMusic, playlist_id: str, duplicates: dict[str, list[TrackInfo]]) -> None:
    """Remove duplicate tracks from YouTube Music playlist keeping the first instance"""
    if not duplicates:
        return

    # Check if this is Liked Music playlist
    if playlist_id == "LM":
        logger.error("Cannot modify Liked Music playlist directly. Please use a regular playlist.")
        return

    tracks_to_remove: list[dict[str, str]] = []
    for video_id, instances in duplicates.items():
        # Keep the first instance and remove the rest
        for instance in instances[1:]:  # Skip first instance
            track_info = {
                "videoId": instance["videoId"],
                "setVideoId": instance.get("setVideoId", instance["videoId"])
            }
            tracks_to_remove.append(track_info)

    if tracks_to_remove:
        try:
            logger.info(f"Attempting to remove {len(tracks_to_remove)} tracks")
            for track in tracks_to_remove:
                try:
                    ytm.remove_playlist_items(playlist_id, [track])
                except Exception as e:
                    logger.error(f"Error removing track: {e}")
                time.sleep(1)  # Rate limiting
            logger.success(
                f"Successfully removed {len(tracks_to_remove)} duplicate tracks from YouTube Music playlist"
            )
        except Exception as e:
            logger.error(f"Error removing tracks from YouTube Music playlist: {e}")
            logger.error("Please make sure you have the necessary permissions to modify this playlist.")


def main() -> None:
    ytm = setup_ytmusic()

    # Get playlist ID from user selection
    playlist_id = select_playlist(ytm)

    duplicates = find_duplicates(ytm, playlist_id)

    if not duplicates:
        logger.success("No duplicates found in YouTube Music playlist!")
        return

    logger.info(f"\nFound {sum(len(v)-1 for v in duplicates.values())} duplicate tracks in YouTube Music playlist:")
    for video_id, instances in duplicates.items():
        # Get the track name from the first instance (they're all the same track)
        track_name = instances[0]["name"]
        logger.info(f"\n{track_name}")
        logger.info(f"  Found {len(instances)} instances")

    if input("\nDo you want to remove duplicates from YouTube Music playlist? (y/N): ").lower() == "y":
        remove_duplicates(ytm, playlist_id, duplicates)


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main() 