import sys
from pathlib import Path

import inquirer

from ytmusic.common import logger
from ytmusic.import_from_spotify import main as import_from_spotify_main
from ytmusic.manage_duplicates import main as manage_duplicates_main


def main() -> None:
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                ("Import tracks from Spotify playlist", "import"),
                ("Find and remove duplicate tracks in YouTube Music playlist", "duplicates"),
            ],
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Action selection cancelled")

    if answers["action"] == "import":
        import_from_spotify_main()
    else:
        manage_duplicates_main()


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main() 