from pathlib import Path
import sys
from logger import FileLogger

BROWSER_PATH = Path("ytmusic") / "browser.json"
logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


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
