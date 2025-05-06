import sys
from pathlib import Path
import inquirer

from ytmusic.common import Config, logger
from ytmusic.import_from_spotify import main as import_from_spotify_main
from ytmusic.manage_duplicates import main as manage_duplicates_main

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
                ("Import tracks from Spotify playlist", "import"),
                ("Find and remove duplicate tracks in YouTube Music playlist", "duplicates"),
            ],
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        logger.error("No action selected")
        sys.exit(1)
    
    if answers["action"] == "import":
        import_from_spotify_main()
    else:
        manage_duplicates_main()


if __name__ == "__main__":
    main() 