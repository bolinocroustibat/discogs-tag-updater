import sys
from pathlib import Path
import inquirer
import tomllib
import discogs_client as dc

from discogs.common import Config as DiscogsConfig, logger as discogs_logger
from discogs.update_tags import main as update_tags_main
from discogs.rename_from_tags import main as rename_files_main

from spotify.common import Config as SpotifyConfig
from spotify.add_local_tracks import main as add_tracks_main
from spotify.manage_duplicates import main as manage_spotify_duplicates_main
from spotify.import_from_ytmusic import main as import_from_ytmusic_main

from ytmusic.common import Config as YTMusicConfig
from ytmusic.import_from_spotify import main as import_from_spotify_main
from ytmusic.manage_duplicates import main as manage_ytmusic_duplicates_main

CONFIG_PATH = Path("config.toml")


def setup_config() -> tuple[DiscogsConfig, SpotifyConfig, YTMusicConfig]:
    """Initialize or create configuration for all services."""
    if not CONFIG_PATH.exists():
        discogs_logger.info("No config.toml file found. Let's create one!")
        config_data = {}

        # Get media path
        questions = [
            inquirer.Text(
                "media_path",
                message="Enter the path to your music files directory",
                default=str(Path.home() / "Music"),
            ),
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data["media_path"] = answers["media_path"]

        # Get Discogs token
        questions = [
            inquirer.Text(
                "token",
                message="Enter your Discogs token",
            ),
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Get Spotify credentials
        questions = [
            inquirer.Text(
                "client_id",
                message="Enter your Spotify client ID",
            ),
            inquirer.Text(
                "client_secret",
                message="Enter your Spotify client secret",
            ),
            inquirer.Text(
                "redirect_uri",
                message="Enter your Spotify redirect URI",
                default="http://localhost:8888/callback",
            ),
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Get YouTube Music credentials
        questions = [
            inquirer.Text(
                "client_id",
                message="Enter your YouTube Music client ID",
            ),
            inquirer.Text(
                "client_secret",
                message="Enter your YouTube Music client secret",
            ),
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Write config file
        DiscogsConfig.write(config_data)
        discogs_logger.info(f"Configuration saved to {CONFIG_PATH}")

    # Initialize configs
    discogs_config = DiscogsConfig()
    spotify_config = SpotifyConfig()
    ytmusic_config = YTMusicConfig()

    return discogs_config, spotify_config, ytmusic_config


def setup_media_path() -> Path:
    """Setup media path if not defined in config."""
    discogs_logger.info("Media path not found in config. Let's set it up!")
    questions = [
        inquirer.Text(
            "media_path",
            message="Enter the path to your music files directory",
            default=str(Path.home() / "Music"),
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        discogs_logger.error("Configuration cancelled by user")
        sys.exit(1)
    
    # Read existing config
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
    
    # Update only the path in the common section
    if "common" not in config:
        config["common"] = {}
    config["common"]["path"] = answers["media_path"]
    
    # Write back the updated config
    with open(CONFIG_PATH, "w") as f:
        f.write("[common]\n")
        f.write(f'path = "{config["common"]["path"]}"\n\n')
        
        # Write discogs section
        if "discogs" in config:
            f.write("[discogs]\n")
            for key, value in config["discogs"].items():
                if isinstance(value, bool):
                    f.write(f"{key} = {str(value).lower()}\n")
                else:
                    f.write(f'{key} = "{value}"\n')
            f.write("\n")
        
        # Write spotify section
        if "spotify" in config:
            f.write("[spotify]\n")
            for key, value in config["spotify"].items():
                f.write(f'{key} = "{value}"\n')
            f.write("\n")
        
        # Write ytmusic section
        if "ytmusic" in config:
            f.write("[ytmusic]\n")
            for key, value in config["ytmusic"].items():
                f.write(f'{key} = "{value}"\n')
    
    return Path(answers["media_path"])


def main() -> None:
    # Setup configurations
    discogs_config, spotify_config, ytmusic_config = setup_config()

    # Initialize Discogs client
    ds = dc.Client("discogs_tag/0.5", user_token=discogs_config.token)

    # Show menu
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                # Discogs options
                (
                    "💿  ➡️  🏷️  Update ID3 tags of the local files using Discogs",
                    "discogs_update",
                ),
                (
                    "🏷️  ➡️  📁  Rename files using their ID3 tags",
                    "discogs_rename",
                ),
                (
                    "💿  ➡️  🏷️  ➡️  📁  Update ID3 tags and rename files",
                    "discogs_both",
                ),
                # Spotify options
                (
                    "🟢  ➕  Add local files to Spotify playlist",
                    "spotify_add",
                ),
                (
                    "🔴  ➡️  🟢  Import tracks from YouTube Music playlist to Spotify Playlist",
                    "spotify_import",
                ),
                (
                    "🟢  🧹  Find and remove duplicate tracks in Spotify playlist",
                    "spotify_duplicates",
                ),
                # YouTube Music options
                (
                    "🟢  ➡️  🔴  Import tracks from Spotify playlist to YouTube Music Playlist",
                    "ytmusic_import",
                ),
                (
                    "🔴  🧹  Find and remove duplicate tracks in YouTube Music playlist",
                    "ytmusic_duplicates",
                ),
            ],
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        discogs_logger.error("No action selected")
        sys.exit(1)

    # Execute selected action
    action = answers["action"]
    
    # Check media path for features that need it
    if action in ["discogs_update", "discogs_rename", "discogs_both", "spotify_add"]:
        if not discogs_config.media_path:
            media_path = setup_media_path()
        else:
            media_path = discogs_config.media_path
        discogs_logger.info(f"\nUsing media directory: {media_path}\n")

    if action == "discogs_update":
        update_tags_main(media_path, discogs_config, ds)
    elif action == "discogs_rename":
        rename_files_main()
    elif action == "discogs_both":
        discogs_logger.info("\nStep 1: Updating ID3 tags from Discogs...")
        update_tags_main(media_path, discogs_config, ds)
        discogs_logger.info("\nStep 2: Renaming files using updated ID3 tags...")
        rename_files_main()
    elif action == "spotify_add":
        add_tracks_main()
    elif action == "spotify_import":
        import_from_ytmusic_main()
    elif action == "spotify_duplicates":
        manage_spotify_duplicates_main()
    elif action == "ytmusic_import":
        import_from_spotify_main()
    elif action == "ytmusic_duplicates":
        manage_ytmusic_duplicates_main()


if __name__ == "__main__":
    main()
