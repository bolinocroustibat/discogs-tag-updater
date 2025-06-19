import spotipy
import sys
from spotify.logger import logger


def get_spotify_track_details(
    sp: spotipy.Spotify, spotify_playlist_id: str
) -> list[dict]:
    """Get track details (name, artist) from Spotify playlist for searching"""
    logger.info(f'Fetching tracks from Spotify playlist "{spotify_playlist_id}"...')
    tracks: list[dict] = []
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("name") or not track.get("artists"):
                        continue
                    tracks.append(
                        {"name": track["name"], "artist": track["artists"][0]["name"]}
                    )
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
                    if not track.get("name") or not track.get("artists"):
                        continue
                    tracks.append(
                        {"name": track["name"], "artist": track["artists"][0]["name"]}
                    )
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in Spotify playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in Spotify playlist")
    return tracks
