from ytmusicapi import YTMusic, OAuthCredentials
from pathlib import Path
from ytmusic.config import Config
from ytmusic.check_ytmusic_setup_oauth import check_ytmusic_setup_oauth
from ytmusic.check_ytmusic_setup_browser import check_ytmusic_setup_browser
from ytmusic.choose_auth_method import choose_auth_method

OAUTH_PATH = Path("ytmusic") / "oauth.json"
BROWSER_PATH = Path("ytmusic") / "browser.json"


def setup_ytmusic() -> YTMusic:
    """
    Initialize and authenticate YouTube Music client.

    Sets up a YTMusic client using either OAuth or browser cookie authentication
    based on user preference and available credentials.

    Returns:
        YTMusic: Authenticated YTMusic client instance.

    Raises:
        Exception: If authentication fails or configuration is invalid.

    Notes:
        - Prompts user to choose between OAuth and browser authentication.
        - OAuth requires client_id and client_secret in config.toml.
        - Browser authentication requires browser.json file with cookies.
        - OAuth is recommended for better reliability and security.
    """
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
