from ytmusicapi import YTMusic, OAuthCredentials
from configparser import ConfigParser
from pathlib import Path
import inquirer
import sys
from typing import TypedDict

from logger import FileLogger

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.parent
INI_PATH = SCRIPT_DIR / "config.ini"
OAUTH_PATH = SCRIPT_DIR / "ytmusic" / "oauth.json"
BROWSER_PATH = SCRIPT_DIR / "ytmusic" / "browser.json"
parser = ConfigParser()
logger = FileLogger("ytmusic.log")


class PlaylistInfo(TypedDict):
    name: str
    id: str
    track_count: int


class Config:
    def __init__(self) -> None:
        global parser
        parser.read(INI_PATH)
        # Remove escape characters from the path and convert to Path object
        raw_path = parser.get("common", "path").replace("\\", "")
        self.media_path = Path(raw_path)
        # Try to get playlist_id, None if not set
        self.playlist_id = parser.get("ytmusic", "playlist_id", fallback=None)
        self.client_id = parser.get("ytmusic", "client_id", fallback=None)
        self.client_secret = parser.get("ytmusic", "client_secret", fallback=None)

    @staticmethod
    def write() -> None:
        """write ini file, with current vars"""
        global parser
        with open(INI_PATH, "w") as f:
            parser.write(f)


def check_ytmusic_setup_oauth() -> None:
    """Check if YouTube Music is properly set up using OAuth"""
    config = Config()
    if not config.client_id or not config.client_secret:
        logger.error("YouTube Music OAuth credentials not set up.")
        logger.info("\nTo set up YouTube Music OAuth authentication:")
        logger.info("1. Go to https://console.cloud.google.com")
        logger.info("2. Create a new project or select an existing one")
        logger.info("3. Enable the YouTube Data API v3")
        logger.info("4. Go to APIs & Services > OAuth consent screen")
        logger.info("   - Set User Type to 'External'")
        logger.info("   - Fill in required fields (App name, User support email, etc.)")
        logger.info("   - Add your Google account email under 'Test users'")
        logger.info("5. Go to APIs & Services > Credentials")
        logger.info("   - Create OAuth 2.0 Client ID")
        logger.info("   - Select 'TVs and Limited Input devices' as the application type")
        logger.info("   - Copy the Client ID and Client Secret")
        logger.info("\nThen add them to your config.ini file:")
        logger.info("[ytmusic]")
        logger.info("client_id = YOUR_CLIENT_ID")
        logger.info("client_secret = YOUR_CLIENT_SECRET")
        logger.info("\nAfter that, run 'uv run ytmusicapi oauth' in your terminal to create oauth.json")
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)

    if not OAUTH_PATH.is_file():
        logger.error("oauth.json file not found.")
        logger.info(f"\nRun 'uv run ytmusicapi oauth' in your terminal to create {OAUTH_PATH}")
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)
    logger.success(f"Found oauth.json at: {OAUTH_PATH}")


def check_ytmusic_setup_browser() -> None:
    """Check if YouTube Music is properly set up using browser cookies"""
    if not BROWSER_PATH.is_file():
        logger.error("browser.json file not found.")
        logger.info("\nTo set up YouTube Music browser authentication:")
        logger.info("1. Follow the instructions at:")
        logger.info("   https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")
        logger.info(f"2. Create a file {BROWSER_PATH} with your browser credentials")
        sys.exit(1)
    logger.success(f"Found browser.json at: {BROWSER_PATH}")


def choose_auth_method() -> str:
    """Let user choose between OAuth and browser cookie authentication"""
    questions = [
        inquirer.List(
            "auth_method",
            message="Choose YouTube Music authentication method",
            choices=[
                ("OAuth (recommended)", "oauth"),
                ("Browser Cookies", "browser"),
            ],
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Authentication method selection cancelled")
    return answers["auth_method"]


def setup_ytmusic() -> YTMusic:
    """Initialize YouTube Music client"""
    auth_method = choose_auth_method()
    
    if auth_method == "oauth":
        check_ytmusic_setup_oauth()
        config = Config()
        oauth_credentials = OAuthCredentials(
            client_id=config.client_id,
            client_secret=config.client_secret
        )
        return YTMusic(str(OAUTH_PATH), oauth_credentials=oauth_credentials)
    else:  # browser method
        check_ytmusic_setup_browser()
        return YTMusic(str(BROWSER_PATH))


def list_user_playlists(ytm: YTMusic) -> list[PlaylistInfo]:
    """Get all playlists owned by the user

    Returns:
        list: List of dicts containing playlist info (name, id, track_count)
    """
    logger.info("Fetching your YouTube Music playlists...")
    playlists = ytm.get_library_playlists()

    # Format output
    user_playlists: list[PlaylistInfo] = []
    for playlist in playlists:
        try:
            if playlist["playlistId"] == "LM":
                # Special case for Liked Music
                try:
                    liked_tracks = ytm.get_liked_songs()
                    track_count = liked_tracks.get("trackCount", 0)
                except Exception as e:
                    logger.warning(f"Could not get liked songs count: {e}")
                    track_count = 0
            else:
                # Regular playlist
                try:
                    playlist_details = ytm.get_playlist(playlist["playlistId"])
                    track_count = playlist_details.get("trackCount", 0)
                except Exception as e:
                    logger.warning(f"Could not get track count for playlist {playlist['title']}: {e}")
                    track_count = 0

            user_playlists.append(
                {
                    "name": playlist["title"],
                    "id": playlist["playlistId"],
                    "track_count": track_count,
                }
            )
        except Exception as e:
            logger.warning(f"Error processing playlist {playlist.get('title', 'Unknown')}: {e}")
            continue

    return user_playlists


def select_playlist(ytm: YTMusic, playlist_id: str | None = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            playlist = ytm.get_playlist(playlist_id)
            logger.success(f'Using YouTube Music playlist: "{playlist["title"]}"')
            return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(ytm)

    if not playlists:
        raise Exception("No playlists found for user")

    # Create choices list for inquirer with formatted display
    choices = [
        (f"{playlist['name']} ({playlist['track_count']} tracks)", playlist["id"])
        for playlist in playlists
    ]

    questions = [
        inquirer.List(
            "playlist_id",
            message="Select a playlist",
            choices=choices,
            carousel=True,
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using YouTube Music playlist: "{selected_name}"')
    return selected_id
