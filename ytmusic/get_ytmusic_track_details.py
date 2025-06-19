from ytmusicapi import YTMusic
import sys
from logger import FileLogger
from pathlib import Path

logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def get_ytmusic_track_details(ytm: YTMusic, ytmusic_playlist_id: str) -> list[dict]:
    """Get track details (name, artist) from YouTube Music playlist for searching"""
    logger.info(
        f'Fetching tracks from YouTube Music playlist "{ytmusic_playlist_id}"...'
    )
    tracks: list[dict] = []
    try:
        if ytmusic_playlist_id == "LM":
            # Special case for Liked Music
            results = ytm.get_liked_songs()
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
        else:
            # Regular playlist
            results = ytm.get_playlist(ytmusic_playlist_id)
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
    except Exception as e:
        logger.error(f"Error fetching YouTube Music playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in YouTube Music playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in YouTube Music playlist")
    return tracks
