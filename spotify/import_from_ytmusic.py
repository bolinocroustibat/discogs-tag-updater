import sys
from pathlib import Path
import time

from tqdm import tqdm
import spotipy

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
    get_ytmusic_track_details,
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


def get_spotify_track_ids(
    sp: spotipy.Spotify, spotify_playlist_id: str
) -> set[str]:
    """Get track IDs from Spotify playlist for duplicate checking"""
    logger.info("Fetching existing tracks from Spotify playlist...")
    existing_tracks: set[str] = set()
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
        else:
            # Regular playlist
            results = sp.playlist_items(spotify_playlist_id)
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)
    return existing_tracks


def add_track_to_spotify(
    sp: spotipy.Spotify,
    track_id: str,
    spotify_playlist_id: str,
    retry_delay: int,
) -> tuple[bool, int]:
    """Add track to Spotify playlist with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if spotify_playlist_id == "liked":
                # Special case for Liked Songs
                sp.current_user_saved_tracks_add([track_id])
            else:
                # Regular playlist
                sp.playlist_add_items(spotify_playlist_id, [track_id])
            logger.success("Track added to Spotify playlist.")
            time.sleep(2)  # Increased delay between requests
            return True, retry_delay
        except Exception as e:
            if "rate/request limit" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Rate limit reached. Waiting {retry_delay} seconds before retry..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error("Max retries reached for rate limit. Skipping track.")
                    return False, retry_delay
            else:
                logger.error(f"Error adding to Spotify playlist: {e}")
                logger.error(f"Track ID: {track_id}")
                logger.error(f"Playlist ID: {spotify_playlist_id}")
                return False, retry_delay
    return False, retry_delay


def process_tracks(
    sp: spotipy.Spotify,
    tracks: list[dict],
    existing_tracks: set[str],
    spotify_playlist_id: str,
) -> tuple[int, int]:
    """Process all tracks and return counts of added and skipped tracks"""
    tracks_added = 0
    tracks_skipped = 0
    auto_first = False
    retry_delay = 5  # Initial delay in seconds

    logger.info("\nProcessing tracks...")
    for track in tqdm(tracks, desc="Processing tracks", unit="track"):
        track_name = track["name"]
        artist_name = track["artist"]

        # Define search function with access to auto_first
        def search_with_auto_first(
            sp: spotipy.Spotify, track_name: str, artist_name: str
        ) -> str | None:
            nonlocal auto_first, retry_delay
            query = f"{track_name} {artist_name}"
            logger.info(f'\nSearching Spotify for "{track_name} - {artist_name}"')

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    results = sp.search(
                        query, type="track", limit=5
                    )  # Show only top 5 matches
                    results = results["tracks"]["items"][
                        :5
                    ]  # Explicitly limit to 5 results
                    if not results:
                        logger.error("No matches found on Spotify")
                        return None

                    # Show all potential matches
                    logger.info("\nPotential matches on Spotify:")
                    matches: list[str] = []
                    for i, track in enumerate(results, 1):
                        if not track.get("name") or not track.get("artists"):
                            continue

                        artist_name = track["artists"][0]["name"]
                        track_name = track["name"]
                        logger.info(f"{i}. Track: {track_name}")
                        logger.info(f"   Artist: {artist_name}")
                        matches.append(track["id"])

                    if not matches:
                        logger.error("No valid matches found on Spotify")
                        return None

                    # Let user choose with 1 as default
                    if auto_first:
                        choice = "1"
                    else:
                        choice = (
                            input(
                                "\nSelect match number (1 is default, 's' to skip, 'a' for auto-first): "
                            )
                            .strip()
                            .lower()
                        )
                        if choice == "a":
                            logger.info(
                                "Auto-first mode enabled - will select first match for all remaining tracks"
                            )
                            auto_first = True
                            choice = "1"

                    if choice == "s":
                        logger.warning("Track skipped")
                        return None

                    if choice == "" or choice == "1":
                        choice = "1"

                    if choice.isdigit() and 1 <= int(choice) <= len(matches):
                        track_id = matches[int(choice) - 1]
                        track_info = sp.track(track_id)
                        if not track_info:
                            logger.error("Could not get track details from Spotify")
                            return None
                        logger.success(
                            f'Selected from Spotify: "{track_info["name"]} - {track_info["artists"][0]["name"]}"'
                        )
                        return track_id

                    logger.warning("Invalid choice - track skipped")
                    return None

                except Exception as e:
                    if "rate/request limit" in str(e).lower():
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Rate limit reached. Waiting {retry_delay} seconds before retry..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            logger.error(
                                "Max retries reached for rate limit. Skipping track."
                            )
                            return None
                    else:
                        logger.error(f"Error searching Spotify: {e}")
                        logger.error(f"Query was: {query}")
                        return None

            return None

        track_id = search_with_auto_first(sp, track_name, artist_name)

        if track_id:
            if track_id in existing_tracks:
                logger.warning("Track already exists in Spotify playlist - skipping")
                tracks_skipped += 1
                continue

            success, retry_delay = add_track_to_spotify(
                sp, track_id, spotify_playlist_id, retry_delay
            )
            if success:
                tracks_added += 1
            else:
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    return tracks_added, tracks_skipped


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
    tracks = get_ytmusic_track_details(ytm, ytmusic_playlist_id)

    # Get existing tracks in Spotify playlist
    existing_tracks = get_spotify_track_ids(sp, spotify_playlist_id)

    # Process tracks
    tracks_added, tracks_skipped = process_tracks(
        sp, tracks, existing_tracks, spotify_playlist_id
    )

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to Spotify: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
