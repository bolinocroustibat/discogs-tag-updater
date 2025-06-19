import spotipy
import sys
from logger import FileLogger

logger = FileLogger("spotify/spotify.log")


def get_spotify_track_ids(sp: spotipy.Spotify, spotify_playlist_id: str) -> set[str]:
    """Get track IDs from Spotify playlist for duplicate checking"""
    logger.info("Fetching existing tracks from Spotify playlist...")
    existing_tracks: set[str] = set()
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
        else:
            # Regular playlist
            results = sp.playlist_items(spotify_playlist_id)
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)
    return existing_tracks
