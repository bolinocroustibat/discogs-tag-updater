import sys
from pathlib import Path
import inquirer
import discogs_client as dc

from discogs.common import Config, logger
from discogs.update_tags import main as update_tags_main
from discogs.rename_from_tags import main as rename_files_main

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

        # Get Discogs token
        questions = [
            inquirer.Text(
                "token",
                message="Enter your Discogs token",
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

    # Initialize config
    config = Config()

    # Show media path to user
    logger.info(f"\nUsing media directory: {config.media_path}\n")

    # Initialize Discogs client
    ds = dc.Client("discogs_tag/0.5", user_token=config.token)

    # Show menu
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                ("💿 ➡️ 🏷️ Update ID3 tags of the local files using Discogs", "update"),
                ("🏷️ ➡️ 📁 Rename files using their ID3 tags", "rename"),
                ("💿 ➡️ 🏷️ ➡️ 📁 Update ID3 tags and rename files", "both"),
            ],
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        logger.error("No action selected")
        sys.exit(1)

    if answers["action"] == "💿 ✏️ 🏷️ Update ID3 tags of the local files using Discogs":
        update_tags_main(config.media_path, config, ds)
    elif answers["action"] == "�� ✏️ 📁 Rename files using their ID3 tags":
        rename_files_main()
    else:  # 💿 ✏️ 🏷️ ➡️ 📁 Update ID3 tags and rename files
        logger.info("\nStep 1: Updating ID3 tags from Discogs...")
        update_tags_main(config.media_path, config, ds)
        logger.info("\nStep 2: Renaming files using updated ID3 tags...")
        rename_files_main()


if __name__ == "__main__":
    main()
