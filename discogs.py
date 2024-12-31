import json
import os
import re
import sys
import time
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

import requests
import discogs_client as dc
from colorama import Fore, init
from discogs_client.exceptions import HTTPError
from fuzzywuzzy import process
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, FLACNoHeaderError, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError
from mutagen._util import MutagenError
from logger import FileLogger
import inquirer

TOKEN_PATH = "discogs-token"
INI_PATH = "config.ini"
parser = ConfigParser()

# colorama
init(autoreset=True)

logger = FileLogger("discogs.log")


class Config(object):
    def __init__(self) -> None:
        parser.read(INI_PATH)
        # Remove escape characters from the path and convert to Path object
        raw_path = parser.get("common", "path").replace("\\", "")
        self.media_path = Path(raw_path)
        self.token = parser.get("discogs", "token")
        self.overwrite_year = parser.getboolean("discogs", "overwrite_year")
        self.overwrite_genre = parser.getboolean("discogs", "overwrite_genre")
        self.embed_cover = parser.getboolean("discogs", "embed_cover")
        self.overwrite_cover = parser.getboolean("discogs", "overwrite_cover")
        self.rename_file = parser.getboolean("discogs", "rename_file")

    @staticmethod
    def write() -> None:
        """write ini file, with current vars"""
        with open(INI_PATH, "w") as f:
            parser.write(f)


class DTag(object):
    def __init__(self, path: Path, suffix: str, filename: str) -> None:
        self.path: Path = path
        self.filename: str = filename
        self.suffix: str = suffix
        self.cover_embedded = False
        self.artist: str = ""
        self.title: str = ""
        self.local_genres = ""
        self.genres: str = ""
        self.local_year: str = ""
        self.year: str = ""
        self._get_tag()
        self.year_found: bool = False
        self.genres_found: bool = False
        self.year_updated: bool = False
        self.genres_updated: bool = False
        self.cover_updated: bool = False

        # clean title and artist tags
        self.artist: str = clean(string=self.artist)
        self.title: str = clean(string=self.title)

    def __repr__(self) -> str:
        return f"File: {self.path}"

    @property
    def tags_log(self) -> str:
        tags = {
            "file": str(self.path),
            "local": {
                "genre": self.local_genres,
                "year": self.local_year,
                "picture": self.cover_embedded,
            },
            "discogs": {
                "genre_found": self.genres_found,
                "genre": self.genres,
                "year_found": self.year_found,
                "year": self.year,
                "image_found": True if hasattr(self, "image") else False,
            },
        }
        return json.dumps(tags)

    def _get_tag(self) -> None:
        if self.suffix == ".flac":
            try:
                audio = FLAC(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
                if audio.get("genre"):
                    self.local_genres = audio["genre"][0]
                if audio.get("date"):
                    self.local_year = audio["date"][0]

                if audio.pictures:
                    self.cover_embedded = True
            except (FLACNoHeaderError, Exception):
                pass

        elif self.suffix == ".mp3":
            try:
                audio = EasyID3(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
                if audio.get("genre"):
                    self.local_genres = audio["genre"][0]
                if audio.get("date"):
                    self.local_year = audio["date"][0]

                audio = MP3(self.path)
                for k in audio.keys():
                    if "covr" in k or "APIC" in k:
                        self.cover_embedded = True

            except (HeaderNotFoundError, MutagenError, KeyError):
                pass

        elif self.suffix == ".m4a":
            try:
                audio = MP4(self.path)
                self.artist = audio["\xa9ART"][0]
                self.title = audio["\xa9nam"][0]
                if audio.get("\xa9gen"):
                    self.local_genres = audio["\xa9gen"][0]
                if audio.get("\xa9day"):
                    self.local_year = audio["\xa9day"][0]
                if audio.get("covr"):
                    self.cover_embedded = True
            except (KeyError, MP4StreamInfoError, MutagenError):
                pass

    def save(self) -> None:
        """
        flac and mp3 support the same keys from mutagen,
        .m4a does not
        """
        if self.year_found is False and self.genres_found is False:
            return

        if self.suffix == ".flac":
            self._image_flac()
            audio = FLAC(self.path)
        elif self.suffix == ".mp3":
            self._image_mp3()
            audio = EasyID3(self.path)
        elif self.suffix == ".m4a":
            self._save_m4a()
            return

        if self.genres_found and (self.local_genres != self.genres):
            if config.overwrite_genre:
                audio["genre"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["genre"] = self.genres
                    self.genres_updated = True

        if self.year_found and (self.local_year != self.year):
            if config.overwrite_year:
                audio["date"] = self.year
                self.year_updated = True
            else:
                if self.local_year == "":
                    audio["date"] = self.year
                    self.year_updated = True

        audio.save()

    def _save_m4a(self) -> None:
        """
        code duplication from self.save
        """
        audio = MP4(self.path)
        if self.genres_found and (self.local_genres != self.genres):
            if config.overwrite_genre:
                audio["\xa9gen"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["\xa9gen"] = self.genres
                    self.genres_updated = True

        if self.year_found and (self.local_year != self.year):
            if config.overwrite_year:
                audio["\xa9day"] = self.year
                self.year_updated = True
            else:
                if self.local_year == "":
                    audio["\xa9day"] = self.year
                    self.year_updated = True
        # save image
        if hasattr(self, "image") and config.embed_cover:
            if config.overwrite_cover:
                audio["covr"] = [
                    MP4Cover(
                        requests.get(self.image).content,
                        imageformat=MP4Cover.FORMAT_JPEG,
                    )
                ]
                self.cover_updated = True
        audio.save()

    def _image_flac(self) -> None:
        if hasattr(self, "image") and config.embed_cover:
            audio = FLAC(self.path)
            img = Picture()
            img.type = 3
            img.data = requests.get(self.image).content
            if config.overwrite_cover:
                audio.clear_pictures()
                audio.add_picture(img)
                self.cover_updated = True
            else:
                if self.cover_embedded is False:
                    audio.clear_pictures()
                    audio.add_picture(img)
                    self.cover_updated = True
            audio.save()

    def _image_mp3(self) -> None:
        def _update_image(path: Path, data: bytes) -> None:
            # del image
            audio_id3 = ID3(path)
            audio_id3.delall("APIC")
            audio_id3.save()

            # update
            audio = MP3(self.path, ID3=ID3)
            audio.tags.add(
                APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=data)
            )
            audio.save()

        # check if image was found
        if hasattr(self, "image") and config.embed_cover:
            if config.overwrite_cover:
                _update_image(self.path, requests.get(self.image).content)
                self.cover_updated = True
            else:
                if self.cover_embedded is False:
                    _update_image(self.path, requests.get(self.image).content)
                    self.cover_updated = True

    def search(self, retry: int = 3) -> Optional[bool]:
        retry -= 1
        # check if track has required tags for searching
        if self.artist == "" and self.title == "":
            logger.error(
                "Track does not have the required tags for searching on Discogs."
            )
            return False

        logger.info(f'Searching for "{self.title} {self.artist}" on Discogs...')
        # discogs api limit: 60/1minute
        # retry option added
        time.sleep(0.5)
        try:
            # Add timeout to the search operation
            start_time = time.time()
            res = ds.search(type="master", artist=self.artist, track=self.title)
            if time.time() - start_time > 10:
                logger.error("Search timed out after 10 seconds, skipping...")
                return False
            
            local_string = f"{self.title} {self.artist}"
            discogs_list = []
            if res.count > 0:
                for i, track in enumerate(res):
                    d_artist = ""
                    if track.data.get("artist"):
                        d_artist = d_artist["artist"][0]["name"]
                    d_title = track.title

                    # create string for comparison
                    discogs_string = f"{d_title} {d_artist}"

                    # append to list
                    discogs_list.append({"index": i, "str": discogs_string})

                # get best match from list
                best_one = process.extractBests(local_string, discogs_list, limit=1)[0][
                    0
                ]["index"]

                # check if genre is missing
                if res[best_one].genres:
                    genres = ", ".join(sorted([x for x in res[best_one].genres]))
                    self.genres = genres
                    self.genres_found = True

                if res[best_one].data["year"]:
                    year = res[best_one].data["year"]
                    self.year = str(year)
                    self.year_found = True

                if res[best_one].images:
                    self.image = res[best_one].images[0]["uri"]
            else:
                print(Fore.RED + "Not Found on Discogs.")
                return False
        except HTTPError:
            if retry == 0:
                print(f"Too many API calls, skipping {self}")
                return False
            print(
                Fore.MAGENTA
                + f"Too many API calls. {retry} retries left, next retry in 5 sec."
            )
            time.sleep(5)
            self.search(retry=retry)


def clean(string: str) -> str:
    string = re.sub(r"\([^)]*\)", "", string).strip()
    if "," in string:
        string = string.split(",")[0].strip()
    if "&" in string:
        string = string.split("&")[0].strip()
    blacklist = ["'", "(Deluxe)"]
    for c in blacklist:
        string = string.replace(c, "")
    return string


def main(directory: Path) -> None:
    logger.log(
        """
              @@@@@@@@@@@@
          @@@               ###########
       @@                  #          #
     @@                   #   COVER   #
   @@                      #          #
  @@                        ###########
 @@
 @              @@@@@@@     ###########
@@            @@@@@@@@@@   #          #
@            @@@@@  @@@@@ #   STYLE   #
@            @@@@@  @@@@@  #          #
@@            @@@@@@@@@@    ###########
 @             @@@@@@@@
 @@          @@@            ###########
  @@       @@@             #          #
    @    @@@@             #    YEAR   #
     @@@@@@@               #          #
       @@@@@                ###########
            @@@@@@@@@@@@@@

      Discogs Tag Updater by Aesir

    """
    )
    # check if directory path exists and valid
    if not directory.is_dir():
        logger.error(f'Directory "{directory}" not found.')
        sys.exit(1)

    # create discogs session
    me = ds.identity()
    logger.log(f"Discogs User: {me}")

    logger.log(f"Looking for files in {directory}")
    logger.warning("Indexing audio files... Please wait\n")
    not_found: int = 0
    found: int = 0
    renamed: int = 0
    total: int = 0
    files = {
        DTag(path=p, suffix=p.suffix, filename=p.name)
        for p in Path(directory).glob("**/*")
        if p.suffix in [".flac", ".mp3", ".m4a"]
    }
    for tag_file in files:
        total += 1
        logger.log(
            "____________________________________________________________________\n"
            + f"File: {tag_file.filename}"
        )
        # print(tag_file.tags_log)

        # Rename file
        new_filename_start: str = f"{tag_file.artist} - {tag_file.title}"
        if (
            config.rename_file
            and tag_file.artist
            and tag_file.title
            and (
                not tag_file.filename.startswith(new_filename_start)
            )  # TODO: improve with regex to keep the parenthesis and brackets
        ):
            new_filename: str = f"{new_filename_start}{tag_file.suffix}"
            new_path: Path = Path(tag_file.path).parent / new_filename
            os.rename(tag_file.path, new_path)
            tag_file.path = new_path
            renamed += 1
            logger.success(f"Renamed: {tag_file.filename} ➔ {new_filename}")

        # Search on Discogs and update
        if tag_file.search() is None:
            tag_file.save()
            found += 1
        else:
            not_found += 1

        # Print file results info
        if tag_file.genres_updated:
            logger.success(f"- Genres: {tag_file.local_genres} ➔ {tag_file.genres}")
        else:
            logger.log(f"- Genres: {tag_file.local_genres} ➔ not updated")

        if tag_file.year_updated:
            logger.success(f"- Year: {tag_file.local_year} ➔ {tag_file.year}")
        else:
            logger.log(f"- Year: {tag_file.local_year} ➔ not updated")

        if tag_file.cover_updated:
            logger.success("- Cover: ➔ updated\n")
        else:
            logger.log("- Cover: ➔ not updated\n")

    logger.log(f"Total files: {total}")
    logger.success(f"With Discogs info found: {found}")
    logger.error(f"With Discogs info not found: {not_found}")
    logger.warning(f"Renamed: {renamed}\n")
    input("Press Enter to exit...")


if __name__ == "__main__":
    # read config
    if Path(INI_PATH).is_file() is False:
        print("\n\n\n")
        print(Fore.GREEN + "First run, config file will be created.")

        questions = [
            inquirer.Text("token", message="Enter your Discogs token"),
            inquirer.Text(
                "media_path",
                message="Enter media path",
                default=os.path.dirname(os.path.abspath(__file__)),
            ),
            inquirer.Confirm(
                "overwrite_year", message="Overwrite existing year tags?", default=True
            ),
            inquirer.Confirm(
                "overwrite_genre",
                message="Overwrite existing genre tags?",
                default=True,
            ),
            inquirer.Confirm("embed_cover", message="Embed cover art?", default=False),
            inquirer.Confirm(
                "overwrite_cover", message="Overwrite existing cover?", default=False
            ),
            inquirer.Confirm(
                "rename_file",
                message="Rename files as [artist] - [track].xxx?",
                default=False,
            ),
        ]

        answers = inquirer.prompt(questions)

        # Handle macOS path
        if os.name == "posix":
            answers["media_path"] = answers["media_path"].replace("\\", "")

        # write config file
        with open(INI_PATH, "w") as f:
            f.write("[common]\n")
            f.write(f"path = {answers['media_path']}\n\n")
            f.write("[discogs]\n")
            f.write(f"token = {answers['token']}\n")
            f.write(f"overwrite_year = {answers['overwrite_year']}\n")
            f.write(f"overwrite_genre = {answers['overwrite_genre']}\n")
            f.write(f"embed_cover = {answers['embed_cover']}\n")
            f.write(f"overwrite_cover = {answers['overwrite_cover']}\n")
            f.write(f"rename_file = {answers['rename_file']}\n")

    # config file exists now
    config = Config()

    # init discogs session
    ds = dc.Client("discogs_tag/0.5", user_token=config.token)
    main(directory=config.media_path)
