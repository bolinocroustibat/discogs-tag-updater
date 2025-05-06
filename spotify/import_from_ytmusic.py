import sys
from pathlib import Path
import time

import spotipy
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


def search_spotify(
    sp: spotipy.Spotify, track_name: str, artist_name: str
) -> list[dict] | None:
    """Search for track on Spotify and return list of potential matches"""
    query = f"track:{track_name} artist:{artist_name}"
    logger.info(f'\nSearching Spotify for "{track_name} - {artist_name}"')

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

            matches.append(
                {
                    "id": track["id"],
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                }
            )

        if not matches:
            logger.error("No valid matches found on Spotify")
            return None

        return matches

    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        logger.error(f"Query was: {query}")
        return None


def select_match(sp: spotipy.Spotify, matches: list[dict]) -> str | None:
    """Let user select a match from the list of potential matches"""
    # Show all potential matches
    logger.info("\nPotential matches on Spotify:")
    for i, track in enumerate(matches, 1):
        logger.info(f"{i}. Track: {track['name']}")
        logger.info(f"   Artist: {track['artist']}")

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
        track_id = matches[int(choice) - 1]["id"]
        track_info = sp.track(track_id)
        if (
            not track_info
            or not track_info.get("name")
            or not track_info.get("artists")
        ):
            logger.error("Could not get track details from Spotify")
            return None
        logger.success(
            f'Selected from Spotify: "{track_info["name"]} - {track_info["artists"][0]["name"]}"'
        )
        return track_id

    logger.warning("Invalid choice - track skipped")
    return None


def main() -> None:
    # Initialize YouTube Music client
    ytm = setup_ytmusic()

    # Get YouTube Music playlist ID from config or user selection
    ytmusic_playlist_id = select_ytmusic_playlist(ytm, ytmusic_config.playlist_id)

    # Initialize Spotify client
    sp = setup_spotify()

    # Get Spotify playlist ID from config or user selection
    spotify_playlist_id = select_spotify_playlist(sp, spotify_config.playlist_id)

    # Get tracks from YouTube Music playlist
    logger.info(f'Fetching tracks from YouTube Music playlist "{ytmusic_playlist_id}"...')
    tracks: list[dict] = []
    try:
        if ytmusic_playlist_id == "LM":
            # Special case for Liked Music
            results = ytm.get_liked_songs()
            total_tracks = 0
            while results:
                batch_size = len(results["tracks"])
                total_tracks += batch_size
                logger.info(f"Processing batch of {batch_size} tracks (total: {total_tracks})")
                
                for track in results["tracks"]:
                    if not track.get("title") or not track.get("artists"):
                        continue
                    artist_name = (
                        track["artists"][0]["name"] if track["artists"] else "Unknown Artist"
                    )
                    tracks.append({"name": track["title"], "artist": artist_name})
                
                # Get next page if available
                if "continuationContents" in results:
                    results = ytm.get_liked_songs(continuation=results["continuationContents"]["musicShelfContinuation"]["continuation"])
                else:
                    break
        else:
            # Regular playlist
            playlist = ytm.get_playlist(ytmusic_playlist_id)
            for track in playlist["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                artist_name = (
                    track["artists"][0]["name"] if track["artists"] else "Unknown Artist"
                )
                tracks.append({"name": track["title"], "artist": artist_name})
    except Exception as e:
        logger.error(f"Error fetching YouTube Music playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in YouTube Music playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in YouTube Music playlist")

    # Get existing tracks in Spotify playlist
    logger.info("Fetching existing tracks from Spotify playlist...")
    existing_tracks: set[str] = set()
    
    if spotify_playlist_id == "liked":
        # Special case for Liked Songs
        results = sp.current_user_saved_tracks()
        while results:
            for item in results["items"]:
                if item["track"] and item["track"]["id"]:
                    existing_tracks.add(item["track"]["id"])
            if results["next"]:
                results = sp.next(results)
            else:
                break
    else:
        # Regular playlist
        results = sp.playlist_items(spotify_playlist_id)
        while results:
            for item in results["items"]:
                if item["track"] and item["track"]["id"]:
                    existing_tracks.add(item["track"]["id"])
            if results["next"]:
                results = sp.next(results)
            else:
                break

    # Process each track
    tracks_added = 0
    tracks_skipped = 0

    logger.info("\nProcessing tracks...")
    for track in tqdm(tracks, desc="Processing tracks", unit="track"):
        track_name = track["name"]
        artist_name = track["artist"]
        matches = search_spotify(sp, track_name, artist_name)

        if matches:
            track_id = select_match(sp, matches)
            if track_id:
                if track_id in existing_tracks:
                    logger.warning(
                        "Track already exists in Spotify playlist - skipping"
                    )
                    tracks_skipped += 1
                    continue

                try:
                    if spotify_playlist_id == "liked":
                        # Special case for Liked Songs
                        sp.current_user_saved_tracks_add([track_id])
                    else:
                        # Regular playlist
                        sp.playlist_add_items(spotify_playlist_id, [track_id])
                    logger.success("Track added to Spotify playlist.")
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
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
