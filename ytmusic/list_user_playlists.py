from ytmusic.types import YTMusicPlaylistInfo
from ytmusicapi import YTMusic
from ytmusic.logger import logger


def list_user_playlists(ytm: YTMusic) -> list[YTMusicPlaylistInfo]:
    """Get all user playlists from YouTube Music"""
    logger.info("Fetching your YouTube Music playlists...")

    try:
        # Get user playlists
        results = ytm.get_library_playlists()
        user_playlists: list[YTMusicPlaylistInfo] = []
        liked_music: YTMusicPlaylistInfo | None = None

        # Add Liked Music as first option
        try:
            liked_tracks = ytm.get_liked_songs()
            liked_music = {
                "name": "Liked Music",
                "id": "LM",  # Special ID for liked music
                "track_count": len(liked_tracks),
            }
            user_playlists.append(liked_music)
        except Exception as e:
            logger.warning(f"Could not get liked music: {e}")

        # Add regular playlists
        for playlist in results:
            playlist_info: YTMusicPlaylistInfo = {
                "name": playlist["title"],
                "id": playlist["playlistId"],
                "track_count": playlist["count"],
            }
            user_playlists.append(playlist_info)

        return user_playlists

    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return []
