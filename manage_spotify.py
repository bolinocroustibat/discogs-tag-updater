import sys
from pathlib import Path

import inquirer

from spotify.common import logger
from spotify.add_tracks import main as add_tracks_main
from spotify.manage_duplicates import main as manage_duplicates_main


def main() -> None:
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                ("Add local files to Spotify playlist", "add"),
                ("Find and remove duplicate tracks", "duplicates"),
            ],
        )
    ]

    answers = inquirer.prompt(questions)

    if answers["action"] == "add":
        add_tracks_main()
    else:
        manage_duplicates_main()


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
