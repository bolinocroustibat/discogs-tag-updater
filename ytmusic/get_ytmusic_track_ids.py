from ytmusicapi import YTMusic
from logger import FileLogger
from pathlib import Path

logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def get_ytmusic_track_ids(ytm: YTMusic, ytmusic_playlist_id: str) -> set[str]:
    """
    Get all track video IDs from a YouTube Music playlist.

    Args:
        ytm: Authenticated YTMusic client instance.
        ytmusic_playlist_id: Playlist ID.

    Returns:
        set[str]: Set of YouTube Music video IDs.

    Notes:
        - Only regular playlists are supported (not Liked Music).
    """
    logger.info("Fetching existing tracks from YouTube Music playlist...")
    existing_tracks: set[str] = set()
    results = ytm.get_playlist(ytmusic_playlist_id)
    for track in results["tracks"]:
        if track.get("videoId"):
            existing_tracks.add(track["videoId"])
    return existing_tracks
