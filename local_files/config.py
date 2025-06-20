import tomllib
from pathlib import Path

TOML_PATH = Path("config.toml")


class Config:
    def __init__(self) -> None:
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        # Get media path from local_files section, default to None if not found
        self.media_path = None
        if "local_files" in config and "path" in config["local_files"]:
            raw_path = config["local_files"]["path"].replace("\\", "")
            self.media_path = Path(raw_path)

        # Discogs config
        discogs_config = config["discogs"]
        self.token = discogs_config["token"]
        self.overwrite_year = discogs_config["overwrite_year"]
        self.overwrite_genre = discogs_config["overwrite_genre"]
        self.embed_cover = discogs_config["embed_cover"]
        self.overwrite_cover = discogs_config["overwrite_cover"]
        self.rename_file = discogs_config["rename_file"]
