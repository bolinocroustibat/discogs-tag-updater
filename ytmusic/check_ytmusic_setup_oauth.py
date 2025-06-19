from pathlib import Path
import sys
from ytmusic.config import Config
from logger import FileLogger

OAUTH_PATH = Path("ytmusic") / "oauth.json"
logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


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
