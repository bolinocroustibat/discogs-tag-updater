import sys
from pathlib import Path
import time
from typing import Optional

import spotipy
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from spotify.common import Config, setup_spotify, logger, select_playlist


class MusicFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.suffix = path.suffix
        self.artist = ""
        self.title = ""
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

    def search_spotify(self, sp: spotipy.Spotify) -> Optional[str]:
        """Search for track on Spotify and return track ID if found"""
        if not self.artist or not self.title:
            logger.error(f"Missing tags for {self.path.name}")
            return None

        query = f"track:{self.title} artist:{self.artist}"
        logger.info(f'\nFile: "{self.path.name}"')
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

            # Show all potential matches
            logger.info("\nPotential matches:")
            matches = []
            for i, track in enumerate(results["tracks"]["items"], 1):
                if not track.get("name") or not track.get("artists"):
                    continue

                artist_name = track["artists"][0]["name"]
                track_name = track["name"]
                logger.info(f"{i}. {track_name} - {artist_name}")
                matches.append(track["id"])

            if not matches:
                logger.error("No valid matches found")
                return None

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
                track_id = matches[int(choice) - 1]
                track_info = sp.track(track_id)
                logger.success(
                    f'Selected: "{track_info["name"]} - {track_info["artists"][0]["name"]}"'
                )
                return track_id

            logger.warning("Invalid choice - track skipped")
            return None

        except Exception as e:
            logger.error(f"Error searching Spotify: {e}")
            logger.error(f"Query was: {query}")
            return None


def main() -> None:
    # Initialize Spotify client
    sp = setup_spotify()

    # Get playlist ID from config or user selection
    playlist_id = select_playlist(sp, config.playlist_id)

    # Scan directory for music files
    logger.info(f"Scanning directory: {config.media_path}")

    # Debug: Check if path exists
    if not config.media_path.exists():
        logger.error(f"Directory does not exist: {config.media_path}")
        sys.exit(1)

    # Debug: List all files in directory
    logger.info("Files found in directory:")
    for p in Path(config.media_path).glob("**/*"):
        logger.info(f"Found file: {p.name} (suffix: {p.suffix})")

    music_files = [
        MusicFile(p)
        for p in Path(config.media_path).glob("**/*")
        if p.suffix.lower() in [".flac", ".mp3", ".m4a"]
    ]

    logger.info(f"Number of music files found: {len(music_files)}")

    if not music_files:
        logger.warning("No .mp3, .flac, or .m4a files found in directory")
        sys.exit(1)

    total_files = len(music_files)
    tracks_added = 0
    tracks_skipped = 0

    # Get existing tracks in playlist
    existing_tracks = set()
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
        logger.info(f"\nProcessing file {index}/{total_files}")
        track_id = music_file.search_spotify(sp)
        if track_id:
            if track_id in existing_tracks:
                logger.warning("Track already exists in playlist - skipping")
                tracks_skipped += 1
                continue

            try:
                sp.playlist_add_items(playlist_id, [track_id])
                logger.success("Track added to playlist")
                tracks_added += 1
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error adding to playlist: {e}")
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    config = Config()
    main()
