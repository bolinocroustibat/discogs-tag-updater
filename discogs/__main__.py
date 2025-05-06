import sys
from pathlib import Path
import inquirer
import discogs_client as dc
from colorama import init

from discogs.common import Config, logger
from discogs.tag_updater import main as tag_updater_main

# colorama
init(autoreset=True)

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
    
    # Initialize Discogs client
    ds = dc.Client("discogs_tag/0.5", user_token=config.token)
    
    # Run tag updater
    tag_updater_main(Path(config.media_path), config, ds)


if __name__ == "__main__":
    main()
