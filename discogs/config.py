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

    @staticmethod
    def write(config_data: dict) -> None:
        """write toml file with current vars"""
        with open(TOML_PATH, "w") as f:
            f.write("[common]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')
            f.write("[discogs]\n")
            f.write(f'token = "{config_data["token"]}"\n')
            f.write(f"overwrite_year = {str(config_data['overwrite_year']).lower()}\n")
            f.write(
                f"overwrite_genre = {str(config_data['overwrite_genre']).lower()}\n"
            )
            f.write(f"embed_cover = {str(config_data['embed_cover']).lower()}\n")
            f.write(
                f"overwrite_cover = {str(config_data['overwrite_cover']).lower()}\n"
            )
            f.write(f"rename_file = {str(config_data['rename_file']).lower()}\n")
