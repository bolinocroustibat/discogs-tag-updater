import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .config import Config
from logger import FileLogger

logger = FileLogger("spotify/spotify.log")


def setup_spotify() -> spotipy.Spotify:
    """Initialize Spotify client with proper permissions"""
    config = Config()
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-read user-library-modify"
    logger.info("Initializing Spotify client...")
    logger.info(f"Using client_id: {config.client_id}")
    logger.info(f"Using redirect_uri: {config.redirect_uri}")
    logger.info(f"Using scopes: {scope}")

    try:
        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri,
                scope=scope,
                open_browser=True,
                cache_path="spotify/.spotify_token_cache",
                requests_timeout=30,
            ),
            requests_timeout=30,
        )
        # Test the authentication
        user = sp.current_user()
        logger.success(f"Successfully authenticated as: {user['display_name']}")
        return sp
    except Exception as e:
        logger.error(f"Error during Spotify authentication: {e}")
        raise
