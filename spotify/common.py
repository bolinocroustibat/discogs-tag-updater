import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pathlib import Path
import inquirer
from typing import TypedDict
import tomllib
import sys

from logger import FileLogger

TOML_PATH = Path("config.toml")
logger = FileLogger("spotify/spotify.log")


class PlaylistInfo(TypedDict):
    name: str
    id: str
    track_count: int


class Config:
    def __init__(self) -> None:
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        # Get media path from common section, default to None if not found
        self.media_path = None
        if "common" in config and "path" in config["common"]:
            raw_path = config["common"]["path"].replace("\\", "")
            self.media_path = Path(raw_path)

        # Spotify config
        spotify_config = config["spotify"]
        self.client_id = spotify_config["client_id"]
        self.client_secret = spotify_config["client_secret"]
        self.redirect_uri = spotify_config["redirect_uri"]
        # Try to get playlist_id, None if not set
        self.playlist_id = spotify_config.get("playlist_id")

    @staticmethod
    def write(config_data: dict) -> None:
        """write toml file with current vars"""
        with open(TOML_PATH, "w") as f:
            f.write("[common]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')
            f.write("[spotify]\n")
            f.write(f'client_id = "{config_data["client_id"]}"\n')
            f.write(f'client_secret = "{config_data["client_secret"]}"\n')
            f.write(f'redirect_uri = "{config_data["redirect_uri"]}"\n')
            if config_data.get("playlist_id"):
                f.write(f'playlist_id = "{config_data["playlist_id"]}"\n')


def setup_spotify() -> spotipy.Spotify:
    """Initialize Spotify client with proper permissions"""
    config = Config()
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-read user-library-modify"
    logger.info("Initializing Spotify client...")
    logger.info(f"Using client_id: {config.client_id}")
    logger.info(f"Using redirect_uri: {config.redirect_uri}")
    logger.info(f"Using scopes: {scope}")

    try:
        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri,
                scope=scope,
                open_browser=True,
                cache_path="spotify/.spotify_token_cache",
            )
        )
        # Test the authentication
        user = sp.current_user()
        logger.success(f"Successfully authenticated as: {user['display_name']}")
        return sp
    except Exception as e:
        logger.error(f"Error during Spotify authentication: {e}")
        raise


def list_user_playlists(sp: spotipy.Spotify) -> list[PlaylistInfo]:
    """Get all playlists owned by the user

    Returns:
        list: List of dicts containing playlist info (name, id, track_count)
    """
    logger.info("Fetching your Spotify playlists...")
    user_id = sp.current_user()["id"]

    # Filter playlists owned by user and format output
    user_playlists: list[PlaylistInfo] = []

    # Add Liked Songs as first option
    try:
        liked_tracks = sp.current_user_saved_tracks()
        user_playlists.append(
            {
                "name": "Liked Songs",
                "id": "liked",  # Special ID for liked songs
                "track_count": liked_tracks["total"],
            }
        )
    except Exception as e:
        logger.warning(f"Could not get liked songs count: {e}")

    # Add regular playlists with pagination
    playlists_response = sp.current_user_playlists(limit=50)  # Get max items per page
    while playlists_response:
        for playlist in playlists_response["items"]:
            if playlist["owner"]["id"] == user_id:
                user_playlists.append(
                    {
                        "name": playlist["name"],
                        "id": playlist["id"],
                        "track_count": playlist["tracks"]["total"],
                    }
                )

        # Get next page if available
        if playlists_response["next"]:
            playlists_response = sp.next(playlists_response)
        else:
            break

    # Sort playlists alphabetically, keeping Liked Songs first
    regular_playlists = user_playlists[1:]  # All playlists except Liked Songs
    sorted_regular_playlists = sorted(
        regular_playlists, key=lambda x: x["name"].lower()
    )
    return [
        user_playlists[0]
    ] + sorted_regular_playlists  # Liked Songs + sorted regular playlists


def select_playlist(sp: spotipy.Spotify, playlist_id: str | None = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            if playlist_id == "liked":
                # Special case for Liked Songs
                try:
                    sp.current_user_saved_tracks(
                        limit=1
                    )  # Just check if we can access liked tracks
                    logger.success('Using Spotify playlist "Liked Songs"')
                    return playlist_id
                except Exception as e:
                    logger.error(f"Error accessing liked songs: {e}")
                    # Fall through to manual selection
            else:
                playlist = sp.playlist(playlist_id)
                logger.success(f'Using Spotify playlist "{playlist["name"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(sp)

    if not playlists:
        raise Exception("No playlists found for user")

    # Create choices list for inquirer with formatted display
    choices = [
        (f"{playlist['name']} ({playlist['track_count']} tracks)", playlist["id"])
        for playlist in playlists
    ]

    questions = [
        inquirer.List(
            "playlist_id",
            message="Select a Spotify playlist",
            choices=choices,
            carousel=True,  # Show all options without scrolling
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using Spotify playlist "{selected_name}"')
    return selected_id


def get_spotify_track_details(
    sp: spotipy.Spotify, spotify_playlist_id: str
) -> list[dict]:
    """Get track details (name, artist) from Spotify playlist for searching"""
    logger.info(f'Fetching tracks from Spotify playlist "{spotify_playlist_id}"...')
    tracks: list[dict] = []
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
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
        else:
            # Regular playlist
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
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in Spotify playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in Spotify playlist")
    return tracks


def get_spotify_track_ids(sp: spotipy.Spotify, spotify_playlist_id: str) -> set[str]:
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


def search_spotify(
    sp: spotipy.Spotify, track_name: str, artist_name: str, file_name: str | None = None
) -> list[dict] | None:
    """Search for track on Spotify and return list of potential matches

    Args:
        sp: Spotify client
        track_name: Name of the track
        artist_name: Name of the artist
        file_name: Optional name of the local file (for logging purposes)

    Returns:
        list[dict] | None: List of potential matches with id, name, and artist, or None if no matches
    """
    if not track_name or not artist_name:
        if file_name:
            logger.error(f"Missing tags for local file {file_name}")
        return None

    query = f"track:{track_name} artist:{artist_name}"
    if file_name:
        logger.info(f'\nLocal file: "{file_name}"')
    logger.info(f'Searching Spotify for "{track_name} - {artist_name}"')

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
    """Let user select a match from the list of potential matches

    Args:
        sp: Spotify client
        matches: List of potential matches with id, name, and artist

    Returns:
        str | None: Selected track ID or None if skipped/invalid
    """
    # Show all potential matches
    logger.info("\nPotential matches from Spotify:")
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
