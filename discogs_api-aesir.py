from configparser import ConfigParser
import json
import logging
import logging.handlers
import os
from pathlib import Path
import re
import requests
import sys
import time
from typing import Optional

import discogs_client as dc
from colorama import Fore, Style, init
from discogs_client.exceptions import HTTPError
from fuzzywuzzy import process
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, FLACNoHeaderError, Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3, HeaderNotFoundError, MutagenError
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError

TOKEN_PATH = "discogs-token"
INI_PATH = "discogs_tag.ini"
parser = ConfigParser()

# colorama
init(autoreset=True)


class Cfg(object):
    def __init__(self) -> None:
        parser.read(INI_PATH)
        self.token = parser.get("discogs", "token")
        self.media_path = parser.get("discogs", "path")
        self.overwrite_year = parser.getboolean("discogs", "overwrite_year")
        self.overwrite_genre = parser.getboolean("discogs", "overwrite_genre")
        self.embed_cover = parser.getboolean("discogs", "embed_cover")
        self.overwrite_cover = parser.getboolean("discogs", "overwrite_cover")

    def write() -> None:
        """write ini file, with current vars"""
        with open(INI_PATH, "w") as f:
            parser.write(f)


class DTag(object):
    def __init__(self, path: str, suffix: str, file_name: str):
        self.path: str = path
        self.file_name: str = file_name
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
        self.style_found: bool = False
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
            "file": self.path,
            "local": {
                "genre": self.local_genres,
                "year": self.local_year,
                "picture": self.cover_embedded,
            },
            "discogs": {
                "genre_found": self.style_found,
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
            except (FLACNoHeaderError, Exception) as e:
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

            except (HeaderNotFoundError, MutagenError, KeyError) as e:
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
            except (KeyError, MP4StreamInfoError, MutagenError) as e:
                pass

    def save(self) -> None:
        """
        flac and mp3 support the same keys from mutagen,
        .m4a does not
        """
        if self.year_found is False and self.style_found is False:
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

        if self.style_found:
            if cfg.overwrite_genre:
                audio["genre"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["genre"] = self.genres
                    self.genres_updated = True

        if self.year_found:
            if cfg.overwrite_year:
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
        if self.style_found:
            if cfg.overwrite_genre:
                audio["\xa9gen"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["\xa9gen"] = self.genres
                    self.genres_updated = True

        if self.year_found:
            if cfg.overwrite_year:
                audio["\xa9day"] = self.year
                self.year_updated = True
            else:
                if self.local_year == "":
                    audio["\xa9day"] = self.year
                    self.year_updated = True
        # save image
        if hasattr(self, "image") and cfg.embed_cover:
            if cfg.overwrite_cover:
                audio["covr"] = [
                    MP4Cover(
                        requests.get(self.image).content,
                        imageformat=MP4Cover.FORMAT_JPEG,
                    )
                ]
                self.cover_updated = True
        audio.save()

    def _image_flac(self) -> None:
        if hasattr(self, "image") and cfg.embed_cover:
            audio = FLAC(self.path)
            img = Picture()
            img.type = 3
            img.data = requests.get(self.image).content
            if cfg.overwrite_cover:
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
        def _update_image(path: str, data: bytes) -> None:
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
        if hasattr(self, "image") and cfg.embed_cover:
            if cfg.overwrite_cover:
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
            print(Fore.RED + "Track does not have the required tags for searching.")
            return False

        print(Fore.YELLOW + f'Searching for "{self.title} {self.artist}"...')
        # discogs api limit: 60/1minute
        # retry option added
        time.sleep(0.5)
        try:
            res = ds.search(type="master", artist=self.artist, track=self.title)
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

                # check if style is missing
                if res[best_one].genres:
                    genres = ", ".join(sorted([x for x in res[best_one].genres]))
                    self.genres = genres
                    self.style_found = True

                if res[best_one].data["year"]:
                    year = res[best_one].data["year"]
                    self.year = str(year)
                    self.year_found = True

                if res[best_one].images:
                    self.image = res[best_one].images[0]["uri"]
            else:
                print(Fore.RED + "Not Found")
                return False
        except HTTPError as e:
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


def main(directory: str) -> None:
    print(
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
    print(f"Directory: {directory}")
    # check if directory path exists and valid
    if not os.path.exists(directory):
        print(Fore.RED + f'Directory "{directory}" not found.')
        sys.exit(1)

    # create discogs session
    me = ds.identity()
    print(f"{me}")
    log.info("Discogs Tag started")

    log.info(f"Looking for files in {directory}")
    print(Fore.YELLOW + "Indexing audio files... Please wait\n")
    not_found: int = 0
    found: int = 0
    total: int = 0
    files = {
        DTag(path=str(p), suffix=p.suffix, file_name=p.name)
        for p in Path(directory).glob("**/*")
        if p.suffix in [".flac", ".mp3", ".m4a"]
    }
    for tag_file in files:
        total += 1
        print(f"File: {tag_file.file_name}")
        log.info(tag_file.tags_log)
        if tag_file.search() is None:
            tag_file.save()
            found += 1
        else:
            not_found += 1
        if tag_file.genres_updated:
            print(
                Fore.RESET
                + "- Genres:  "
                + Style.BRIGHT
                + tag_file.local_genres
                + Style.NORMAL
                + " ➔ "
                + Fore.GREEN
                + Style.BRIGHT
                + tag_file.genres
            )
        else:
            print(
                Fore.RESET
                + "- Genres:  "
                + Style.BRIGHT
                + tag_file.local_genres
                + Style.NORMAL
                + ", not updated"
            )
        if tag_file.year_updated:
            print(
                Fore.RESET
                + "- Year:    "
                + Style.BRIGHT
                + tag_file.local_year
                + Style.NORMAL
                + " ➔ "
                + Fore.GREEN
                + Style.BRIGHT
                + tag_file.year
            )
        else:
            print(
                Fore.RESET
                + "- Year:    "
                + Style.BRIGHT
                + tag_file.local_year
                + Style.NORMAL
                + ", not updated"
            )
        if tag_file.cover_updated:
            print("- Cover:   " + Fore.GREEN + "updated\n")
        else:
            print("- Cover:   not updated\n")

    print(
        f"Total Files {total}, "
        + Fore.GREEN
        + f"Found {found}, "
        + Fore.RED
        + f"Not Found: {not_found}"
    )
    input("Press Enter to exit...")


if __name__ == "__main__":
    # read config
    if os.path.exists(INI_PATH) is False:
        # first run
        print("\n\n\n")
        print(Fore.GREEN + "First run, config file will be created.")
        print(
            "If multiple options are available they will be in square brackets. The one in uppercase is the default value."
        )
        token = input("Discogs token -> ")
        media_path = input("Media Path -> ")
        if media_path == "":
            media_path = os.path.dirname(os.path.abspath(__file__))
        # apple user
        if os.name == "posix":
            media_path = media_path.replace("\\", "")

        # year tag
        overwrite_year = input("Overwrite Year Tag [TRUE/false] -> ")
        if overwrite_year.lower() == "false":
            overwrite_year = False
        else:
            overwrite_year = True

        # genre tag
        overwrite_genre = input("Overwrite Genre Tag [TRUE/false] -> ")
        if overwrite_genre.lower() == "false":
            overwrite_genre = False
        else:
            overwrite_genre = True

        # cover options
        cover_download = input("Embed Cover Art [true/FALSE] -> ")
        if cover_download.lower() == "true":
            cover_download = True
        else:
            cover_download = False

        overwrite_cover = input("Overwrite existing cover [true/FALSE] -> ")
        if overwrite_cover.lower() == "true":
            overwrite_cover = True
        else:
            overwrite_cover = False

        # write config file
        with open(INI_PATH, "w") as f:
            f.write("[discogs]\n")
            f.write(f"token = {token}\n")
            f.write(f"path = {media_path}\n")
            f.write(f"overwrite_year = {overwrite_year}\n")
            f.write(f"overwrite_genre = {overwrite_genre}\n")
            f.write(f"embed_cover = {cover_download}\n")
            f.write(f"overwrite_cover = {overwrite_cover}\n")

    # config file exists now
    cfg = Cfg()

    # logger
    log = logging.getLogger("discogs_tag")
    log.setLevel(20)

    # handler
    five_mbytes = 10 ** 6 * 5
    handler = logging.handlers.RotatingFileHandler(
        "discogs_tag.log", maxBytes=five_mbytes, encoding="UTF-8", backupCount=0
    )
    handler.setLevel(20)

    # create formater
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # add formater to handler
    handler.setFormatter(formatter)

    # add handler to logger
    log.addHandler(handler)

    # init discogs session
    ds = dc.Client("discogs_tag/0.5", user_token=cfg.token)
    main(directory=cfg.media_path)
