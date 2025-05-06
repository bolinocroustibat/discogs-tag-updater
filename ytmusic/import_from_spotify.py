import sys
from pathlib import Path
import time

from ytmusicapi import YTMusic
from tqdm import tqdm

from spotify.common import (
    Config as SpotifyConfig,
    setup_spotify,
    logger,
    select_playlist as select_spotify_playlist,
)
from ytmusic.common import (
    Config as YTMusicConfig,
    setup_ytmusic,
    select_playlist as select_ytmusic_playlist,
)

spotify_config = SpotifyConfig()
ytmusic_config = YTMusicConfig()


def search_youtube_music(ytm: YTMusic, track_name: str, artist_name: str) -> str | None:
    """Search for track on YouTube Music and return video ID if found"""
    query = f"{track_name} {artist_name}"
    logger.info(f'\nSearching YouTube Music for "{track_name} - {artist_name}"')

    try:
        results = ytm.search(query, filter="songs", limit=5)  # Show only top 5 matches
        results = results[:5]  # Explicitly limit to 5 results
        if not results:
            logger.error("No matches found on YouTube Music")
            return None

        # Show all potential matches
        logger.info("\nPotential matches from YouTube Music:")
        matches: list[str] = []
        for i, track in enumerate(results, 1):
            if not track.get("title") or not track.get("artists"):
                continue

            artist_name = track["artists"][0]["name"]
            track_name = track["title"]
            logger.info(f"{i}. Track: {track_name}")
            logger.info(f"   Artist: {artist_name}")
            matches.append(track["videoId"])

        if not matches:
            logger.error("No valid matches found on YouTube Music")
            return None

        # Let user choose with 1 as default
        choice = (
            input("\nSelect match number (1 is default, 's' to skip): ").strip().lower()
        )
        if choice == "s":
            logger.warning("Track skipped")
            return None

        if choice == "" or choice == "1":
            choice = "1"

        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            video_id = matches[int(choice) - 1]
            track_info = ytm.get_song(video_id)
            if not track_info or not track_info.get("videoDetails"):
                logger.error("Could not get track details from YouTube Music")
                return None
            logger.success(
                f'Selected from YouTube Music: "{track_info["videoDetails"]["title"]} - {track_info["videoDetails"]["author"]}"'
            )
            return video_id

        logger.warning("Invalid choice - track skipped")
        return None

    except Exception as e:
        logger.error(f"Error searching YouTube Music: {e}")
        logger.error(f"Query was: {query}")
        return None


def main() -> None:
    # Initialize Spotify client
    sp = setup_spotify()

    # Get Spotify playlist ID from config or user selection
    spotify_playlist_id = select_spotify_playlist(sp, spotify_config.playlist_id)

    # Initialize YouTube Music client
    ytm = setup_ytmusic()

    # Get YouTube Music playlist ID from config or user selection
    ytmusic_playlist_id = select_ytmusic_playlist(ytm, ytmusic_config.playlist_id)

    # Get tracks from Spotify playlist
    logger.info("Fetching tracks from Spotify playlist...")
    tracks: list[dict] = []
    results = sp.playlist_items(spotify_playlist_id)
    while results:
        for item in results["items"]:
            if not item.get("track"):
                continue
            track = item["track"]
            if not track.get("name") or not track.get("artists"):
                continue
            tracks.append(
                {"name": track["name"], "artist": track["artists"][0]["name"]}
            )
        if results["next"]:
            results = sp.next(results)
        else:
            break

    if not tracks:
        logger.warning("No tracks found in Spotify playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in Spotify playlist")

    # Get existing tracks in YouTube Music playlist
    logger.info("Fetching existing tracks from YouTube Music playlist...")
    existing_tracks: set[str] = set()
    results = ytm.get_playlist(ytmusic_playlist_id)
    for track in results["tracks"]:
        if track.get("videoId"):
            existing_tracks.add(track["videoId"])

    # Process each track
    tracks_added = 0
    tracks_skipped = 0

    logger.info("\nProcessing tracks...")
    for track in tqdm(tracks, desc="Processing tracks", unit="track"):
        track_name = track["name"]
        artist_name = track["artist"]
        video_id = search_youtube_music(ytm, track_name, artist_name)

        if video_id:
            if video_id in existing_tracks:
                logger.warning(
                    "Track already exists in YouTube Music playlist - skipping"
                )
                tracks_skipped += 1
                continue

            try:
                ytm.add_playlist_items(ytmusic_playlist_id, [video_id])
                logger.success("Track added to YouTube Music playlist")
                tracks_added += 1
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error adding to YouTube Music playlist: {e}")
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to YouTube Music: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.ini").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
