import sys
from pathlib import Path
import time
from typing import Optional

import spotipy
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from spotify.common import Config, setup_spotify, logger, select_playlist

config = Config()


class MusicFile:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.suffix: str = path.suffix
        self.artist: str = ""
        self.title: str = ""
        self._get_tags()

    def _get_tags(self) -> None:
        """Extract artist and title tags from music files"""
        if self.suffix == ".flac":
            try:
                audio = FLAC(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
            except Exception as e:
                logger.error(f"Error reading FLAC tags: {e}")

        elif self.suffix == ".mp3":
            try:
                audio = EasyID3(self.path)
                self.artist = audio["artist"][0]
                self.title = audio["title"][0]
            except Exception as e:
                logger.error(f"Error reading MP3 tags: {e}")

        elif self.suffix == ".m4a":
            try:
                audio = MP4(self.path)
                self.artist = audio["\xa9ART"][0]
                self.title = audio["\xa9nam"][0]
            except Exception as e:
                logger.error(f"Error reading M4A tags: {e}")

    def search_spotify(self, sp: spotipy.Spotify) -> Optional[list[dict]]:
        """Search for track on Spotify and return list of potential matches"""
        if not self.artist or not self.title:
            logger.error(f"Missing tags for local file {self.path.name}")
            return None

        query = f"track:{self.title} artist:{self.artist}"
        logger.info(f'\nLocal file: "{self.path.name}"')
        logger.info(f'Searching Spotify for "{self.title} - {self.artist}"')

        try:
            results = sp.search(query, type="track", limit=5)
            if (
                not results
                or not results.get("tracks")
                or not results["tracks"].get("items")
            ):
                logger.error("No matches found on Spotify")
                return None

            # Format matches
            matches: list[dict] = []
            for track in results["tracks"]["items"]:
                if not track.get("name") or not track.get("artists"):
                    continue

                matches.append({
                    "id": track["id"],
                    "name": track["name"],
                    "artist": track["artists"][0]["name"]
                })

            if not matches:
                logger.error("No valid matches found on Spotify")
                return None

            return matches

        except Exception as e:
            logger.error(f"Error searching Spotify: {e}")
            logger.error(f"Query was: {query}")
            return None

    def select_match(self, sp: spotipy.Spotify, matches: list[dict]) -> Optional[str]:
        """Let user select a match from the list of potential matches"""
        # Show all potential matches
        logger.info("\nPotential matches from Spotify:")
        for i, track in enumerate(matches, 1):
            logger.info(f"{i}. Track: {track['name']}")
            logger.info(f"   Artist: {track['artist']}")

        # Let user choose with 1 as default
        choice = (
            input("\nSelect match number (1 is default, 's' to skip): ")
            .strip()
            .lower()
        )
        if choice == "s":
            logger.warning("Track skipped")
            return None

        if choice == "" or choice == "1":
            choice = "1"

        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            track_id = matches[int(choice) - 1]["id"]
            track_info = sp.track(track_id)
            if not track_info or not track_info.get("name") or not track_info.get("artists"):
                logger.error("Could not get track details from Spotify")
                return None
            logger.success(
                f'Selected from Spotify: "{track_info["name"]} - {track_info["artists"][0]["name"]}"'
            )
            return track_id

        logger.warning("Invalid choice - track skipped")
        return None


def main() -> None:
    # Initialize Spotify client
    sp = setup_spotify()

    # Get playlist ID from config or user selection
    playlist_id = select_playlist(sp, config.playlist_id)

    # Scan directory for music files
    logger.info(f"Scanning local directory: {config.media_path}")

    # Debug: Check if path exists
    if not config.media_path.exists():
        logger.error(f"Local directory does not exist: {config.media_path}")
        sys.exit(1)

    # Debug: List all files in directory
    logger.info("Local files found in directory:")
    for p in sorted(Path(config.media_path).glob("**/*"), key=lambda x: x.name.lower()):
        logger.info(f"Found local file: {p.name} (suffix: {p.suffix})")

    music_files: list[MusicFile] = [
        MusicFile(p)
        for p in sorted(Path(config.media_path).glob("**/*"), key=lambda x: x.name.lower())
        if p.suffix.lower() in [".flac", ".mp3", ".m4a"]
    ]

    logger.info(f"Number of local music files found: {len(music_files)}")

    if not music_files:
        logger.warning("No local .mp3, .flac, or .m4a files found in directory")
        sys.exit(1)

    total_files = len(music_files)
    tracks_added = 0
    tracks_skipped = 0

    # Get existing tracks in playlist
    existing_tracks: set[str] = set()
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            if item["track"] and item["track"]["id"]:
                existing_tracks.add(item["track"]["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break

    # Process each music file
    for index, music_file in enumerate(music_files, 1):
        logger.info(f"\nProcessing local file {index}/{total_files}")
        matches = music_file.search_spotify(sp)
        if matches:
            track_id = music_file.select_match(sp, matches)
            if track_id:
                if track_id in existing_tracks:
                    logger.warning("Track already exists in Spotify playlist - skipping")
                    tracks_skipped += 1
                    continue

                try:
                    sp.playlist_add_items(playlist_id, [track_id])
                    logger.success("Track added to Spotify playlist")
                    tracks_added += 1
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error adding to Spotify playlist: {e}")
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to Spotify: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    main()
