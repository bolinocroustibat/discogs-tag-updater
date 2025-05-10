import sys
from pathlib import Path
import tomllib
import discogs_client as dc

from local_files.common import Config as DiscogsConfig, logger as discogs_logger
from local_files.update_tags_from_discogs import main as update_tags_main
from local_files.rename_from_tags import main as rename_files_main

from spotify.common import Config as SpotifyConfig
from spotify.add_local_tracks import main as add_tracks_main
from spotify.manage_duplicates import main as manage_spotify_duplicates_main
from spotify.import_from_ytmusic import main as import_from_ytmusic_main

from ytmusic.common import Config as YTMusicConfig
from ytmusic.import_from_spotify import main as import_from_spotify_main
from ytmusic.manage_duplicates import main as manage_ytmusic_duplicates_main
from ytmusic.add_local_tracks import main as add_ytmusic_tracks_main

from dataclasses import dataclass
from mininterface import run, Mininterface


CONFIG_PATH = Path("config.toml")


def setup_config(m: Mininterface) -> tuple[DiscogsConfig, SpotifyConfig, YTMusicConfig]:
    """Initialize or create configuration for all services."""
    if not CONFIG_PATH.exists():
        discogs_logger.info("No config.toml file found. Let's create one!")
        
        # Use Mininterface's form to get configuration
        config_data = m.form({
            "media_path": str(m.env.media_path),
            "discogs_token": m.env.discogs_token,
            "spotify_client_id": m.env.spotify_client_id,
            "spotify_client_secret": m.env.spotify_client_secret,
            "spotify_redirect_uri": m.env.spotify_redirect_uri,
            "ytmusic_client_id": m.env.ytmusic_client_id,
            "ytmusic_client_secret": m.env.ytmusic_client_secret,
            "overwrite_year": m.env.overwrite_year,
            "overwrite_genre": m.env.overwrite_genre,
            "embed_cover": m.env.embed_cover,
            "overwrite_cover": m.env.overwrite_cover,
            "rename_file": m.env.rename_file,
        }, title="Music Sync Toolbox Configuration")

        if not config_data:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)

        # Write config file
        with open(CONFIG_PATH, "w") as f:
            f.write("[local_files]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')

            f.write("[discogs]\n")
            f.write(f'token = "{config_data["discogs_token"]}"\n')
            f.write(f'overwrite_year = {str(config_data["overwrite_year"]).lower()}\n')
            f.write(f'overwrite_genre = {str(config_data["overwrite_genre"]).lower()}\n')
            f.write(f'embed_cover = {str(config_data["embed_cover"]).lower()}\n')
            f.write(f'overwrite_cover = {str(config_data["overwrite_cover"]).lower()}\n')
            f.write(f'rename_file = {str(config_data["rename_file"]).lower()}\n\n')

            f.write("[spotify]\n")
            f.write(f'client_id = "{config_data["spotify_client_id"]}"\n')
            f.write(f'client_secret = "{config_data["spotify_client_secret"]}"\n')
            f.write(f'redirect_uri = "{config_data["spotify_redirect_uri"]}"\n\n')

            f.write("[ytmusic]\n")
            f.write(f'client_id = "{config_data["ytmusic_client_id"]}"\n')
            f.write(f'client_secret = "{config_data["ytmusic_client_secret"]}"\n')

        discogs_logger.info(f"Configuration saved to {CONFIG_PATH}")

    # Initialize configs
    discogs_config = DiscogsConfig()
    spotify_config = SpotifyConfig()
    ytmusic_config = YTMusicConfig()

    return discogs_config, spotify_config, ytmusic_config


def setup_media_path(m: Mininterface) -> Path:
    """Setup media path if not defined in config."""
    discogs_logger.info("Media path not found in config. Let's set it up!")
    
    # Use Mininterface's form to get the media path
    form_data = m.form({
        "media_path": str(Path.home() / "Music")
    })

    if not form_data:
        discogs_logger.error("Configuration cancelled by user")
        sys.exit(1)

    media_path = str(form_data["media_path"])  # Convert to string first

    # Read existing config
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)

    # Update only the path in the local_files section
    if "local_files" not in config:
        config["local_files"] = {}
    config["local_files"]["path"] = media_path

    # Write back the updated config
    with open(CONFIG_PATH, "w") as f:
        f.write("[local_files]\n")
        f.write(f'path = "{media_path}"\n\n')

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

    return Path(media_path)


def main(m: Mininterface) -> None:
    # Setup configurations
    discogs_config, spotify_config, ytmusic_config = setup_config(m)

    # Initialize Discogs client
    ds = dc.Client("discogs_tag/0.5", user_token=discogs_config.token)

    # Define menu options
    menu_options = [
        # Discogs options
        "💿  ➡️  🏷️  Update ID3 tags of the local files using Discogs",
        "🏷️  ➡️  📁  Rename files using their ID3 tags",
        "💿  ➡️  🏷️  ➡️  📁  Update ID3 tags and rename files",
        # Spotify options
        "🟢  ➕  Add local files to Spotify playlist",
        "🔴  ➡️  🟢  Import tracks from YouTube Music playlist to Spotify Playlist",
        "🟢  🧹  Find and remove duplicate tracks in Spotify playlist",
        # YouTube Music options
        "🔴  ➕  Add local files to YouTube Music playlist",
        "🟢  ➡️  🔴  Import tracks from Spotify playlist to YouTube Music Playlist",
        "🔴  🧹  Find and remove duplicate tracks in YouTube Music playlist",
    ]

    # Show menu using Mininterface
    action = m.select(
        menu_options,
        title="What would you like to do?\n",
        tips=["Select an action to perform"],
        skippable=False
    )

    if not action:
        discogs_logger.error("No action selected")
        sys.exit(1)

    # Map the selected option to the corresponding action
    action_map = {
        menu_options[0]: "discogs_update",
        menu_options[1]: "discogs_rename",
        menu_options[2]: "discogs_both",
        menu_options[3]: "spotify_add",
        menu_options[4]: "spotify_import",
        menu_options[5]: "spotify_duplicates",
        menu_options[6]: "ytmusic_add",
        menu_options[7]: "ytmusic_import",
        menu_options[8]: "ytmusic_duplicates",
    }

    action = action_map[action]

    # Check media path for features that need it
    if action in [
        "discogs_update",
        "discogs_rename",
        "discogs_both",
        "spotify_add",
        "ytmusic_add",
    ]:
        if not discogs_config.media_path:
            media_path = setup_media_path(m)
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
    elif action == "ytmusic_add":
        add_ytmusic_tracks_main()
    elif action == "spotify_import":
        import_from_ytmusic_main()
    elif action == "spotify_duplicates":
        manage_spotify_duplicates_main(m)
    elif action == "ytmusic_import":
        import_from_spotify_main()
    elif action == "ytmusic_duplicates":
        manage_ytmusic_duplicates_main(m)

@dataclass
class Env:
    """Configuration for Music Sync Toolbox."""

    media_path: Path = Path.home() / "Music"
    """Path to your music files directory"""

    discogs_token: str = ""
    """Your Discogs API token"""

    spotify_client_id: str = ""
    """Your Spotify application client ID"""

    spotify_client_secret: str = ""
    """Your Spotify application client secret"""

    spotify_redirect_uri: str = "http://localhost:8888/callback"
    """The redirect URI for Spotify OAuth authentication"""

    ytmusic_client_id: str = ""
    """Your YouTube Music OAuth client ID"""

    ytmusic_client_secret: str = ""
    """Your YouTube Music OAuth client secret"""

    overwrite_year: bool = False
    """If year tag is set on the file, it will not overwrite it"""

    overwrite_genre: bool = False
    """If genre tag is set on the file, it will not overwrite it"""

    embed_cover: bool = True
    """Enable or disable cover embedding feature"""

    overwrite_cover: bool = False
    """If cover is set on the file, it will not overwrite it"""

    rename_file: bool = False
    """If file is already named correctly, it will not rename it"""

if __name__ == "__main__":
    with run(Env, title="Music Sync Toolbox") as m:
        main(m)
