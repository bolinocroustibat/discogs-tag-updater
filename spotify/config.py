from pathlib import Path
import tomllib

TOML_PATH = Path("config.toml")


class Config:
    """Configuration manager for Spotify API credentials and settings.

    Loads Spotify-specific configuration from the main config.toml file,
    including OAuth credentials and optional playlist settings.
    """

    def __init__(self) -> None:
        """Initialize Spotify configuration from config.toml file.

        Loads the following configuration:
        - OAuth credentials (client_id, client_secret, redirect_uri)
        - Optional playlist_id for default playlist selection
        - Media path from local_files section (if available)

        Raises:
            FileNotFoundError: If config.toml file doesn't exist
            KeyError: If required Spotify configuration is missing
        """
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        # Get media path from local_files section, default to None if not found
        self.media_path = None
        if "local_files" in config and "path" in config["local_files"]:
            raw_path = config["local_files"]["path"].replace("\\", "")
            self.media_path = Path(raw_path)

        # Spotify config
        spotify_config = config["spotify"]
        self.client_id = spotify_config["client_id"]
        self.client_secret = spotify_config["client_secret"]
        self.redirect_uri = spotify_config["redirect_uri"]
        # Try to get playlist_id, None if not set
        self.playlist_id = spotify_config.get("playlist_id")
