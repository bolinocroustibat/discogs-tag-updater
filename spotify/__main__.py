import sys
from pathlib import Path
import inquirer

from spotify.common import Config, logger
from spotify.add_tracks import main as add_tracks_main
from spotify.manage_duplicates import main as manage_duplicates_main
from spotify.import_from_ytmusic import main as import_from_ytmusic_main

CONFIG_PATH = Path("config.toml")


def main() -> None:
    if not CONFIG_PATH.exists():
        logger.info("No config.toml file found. Let's create one!")
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
            logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data["media_path"] = answers["media_path"]

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
            logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Write config file
        Config.write(config_data)
        logger.info(f"Configuration saved to {CONFIG_PATH}")

    # Show menu
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                ("Add local files to Spotify playlist", "add"),
                ("Find and remove duplicate tracks in Spotify playlist", "duplicates"),
                ("Import tracks from YouTube Music playlist", "import"),
            ],
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        logger.error("No action selected")
        sys.exit(1)

    if answers["action"] == "add":
        add_tracks_main()
    elif answers["action"] == "duplicates":
        manage_duplicates_main()
    else:
        import_from_ytmusic_main()


if __name__ == "__main__":
    main()
