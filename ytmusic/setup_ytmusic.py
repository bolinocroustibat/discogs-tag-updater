from ytmusicapi import YTMusic, OAuthCredentials
from pathlib import Path
import sys
import inquirer
from ytmusic.config import Config
from ytmusic.logger import logger

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


def choose_auth_method() -> str:
    """
    Let the user choose between OAuth and browser cookie authentication.

    Returns:
        str: The chosen authentication method ("oauth" or "browser").

    Raises:
        KeyboardInterrupt: If user cancels the selection process.

    Notes:
        - OAuth is recommended for better reliability and security.
        - Browser authentication uses saved cookies from a browser session.
    """
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


def check_ytmusic_setup_oauth() -> None:
    """
    Check if YouTube Music OAuth authentication is properly configured.

    Verifies that OAuth credentials are set up in config.toml and that
    the oauth.json file exists with valid authentication tokens.

    Raises:
        SystemExit: If OAuth setup is incomplete or invalid.

    Notes:
        - Checks for client_id and client_secret in config.toml.
        - Verifies oauth.json file exists.
        - Provides detailed setup instructions if configuration is missing.
    """
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
        logger.info(
            "   - Select 'TVs and Limited Input devices' as the application type"
        )
        logger.info("   - Copy the Client ID and Client Secret")
        logger.info("\nThen add them to your config.toml file:")
        logger.info("[ytmusic]")
        logger.info("client_id = YOUR_CLIENT_ID")
        logger.info("client_secret = YOUR_CLIENT_SECRET")
        logger.info(
            "\nAfter that, run 'uv run ytmusicapi oauth' in your terminal to create oauth.json"
        )
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)

    if not OAUTH_PATH.is_file():
        logger.error("oauth.json file not found.")
        logger.info(
            f"\nRun 'uv run ytmusicapi oauth' in your terminal to create {OAUTH_PATH}"
        )
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)
    logger.success(f"Found oauth.json at: {OAUTH_PATH}")


def check_ytmusic_setup_browser() -> None:
    """
    Check if YouTube Music browser authentication is properly configured.

    Verifies that the browser.json file exists with valid browser cookies
    for YouTube Music authentication.

    Raises:
        SystemExit: If browser setup is incomplete or invalid.

    Notes:
        - Checks for browser.json file in the ytmusic directory.
        - Provides setup instructions if the file is missing.
        - References external documentation for detailed setup steps.
    """
    if not BROWSER_PATH.is_file():
        logger.error("browser.json file not found.")
        logger.info("\nTo set up YouTube Music browser authentication:")
        logger.info("1. Follow the instructions at:")
        logger.info("   https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")
        logger.info(f"2. Create a file {BROWSER_PATH} with your browser credentials")
        sys.exit(1)
    logger.success(f"Found browser.json at: {BROWSER_PATH}")
