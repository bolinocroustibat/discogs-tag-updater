from spotify.types import SpotifyPlaylistInfo
import spotipy
from logger import FileLogger

logger = FileLogger("spotify/spotify.log")


def list_user_playlists(sp: spotipy.Spotify) -> list[SpotifyPlaylistInfo]:
    """Get all user playlists from Spotify"""
    logger.info("Fetching your Spotify playlists...")

    try:
        # Get user playlists
        results = sp.current_user_playlists()
        user_playlists: list[SpotifyPlaylistInfo] = []

        for playlist in results["items"]:
            playlist_info: SpotifyPlaylistInfo = {
                "name": playlist["name"],
                "id": playlist["id"],
                "track_count": playlist["tracks"]["total"],
            }
            user_playlists.append(playlist_info)

        return user_playlists

    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return []
