from ytmusicapi import YTMusic, OAuthCredentials
from pathlib import Path
from .config import Config
from .check_ytmusic_setup_oauth import check_ytmusic_setup_oauth
from .check_ytmusic_setup_browser import check_ytmusic_setup_browser
from .choose_auth_method import choose_auth_method
from logger import FileLogger

OAUTH_PATH = Path("ytmusic") / "oauth.json"
BROWSER_PATH = Path("ytmusic") / "browser.json"
logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def setup_ytmusic() -> YTMusic:
    """Initialize YouTube Music client"""
    auth_method = choose_auth_method()

    if auth_method == "oauth":
        check_ytmusic_setup_oauth()
        config = Config()
        oauth_credentials = OAuthCredentials(
            client_id=config.client_id, client_secret=config.client_secret
        )
        return YTMusic(str(OAUTH_PATH), oauth_credentials=oauth_credentials)
    else:  # browser method
        check_ytmusic_setup_browser()
        return YTMusic(str(BROWSER_PATH))
