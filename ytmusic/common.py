from ytmusicapi import YTMusic, OAuthCredentials
from pathlib import Path
import inquirer
import sys
from typing import TypedDict
import tomllib
import time

from logger import FileLogger

TOML_PATH = Path("config.toml")
OAUTH_PATH = Path("ytmusic") / "oauth.json"
BROWSER_PATH = Path("ytmusic") / "browser.json"
logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


class PlaylistInfo(TypedDict):
    name: str
    id: str
    track_count: int


class Config:
    def __init__(self) -> None:
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        # Get media path from local_files section, default to None if not found
        self.media_path = None
        if "local_files" in config and "path" in config["local_files"]:
            raw_path = config["local_files"]["path"].replace("\\", "")
            self.media_path = Path(raw_path)

        # YouTube Music config
        ytmusic_config = config["ytmusic"]
        self.client_id = ytmusic_config["client_id"]
        self.client_secret = ytmusic_config["client_secret"]
        # Try to get playlist_id, None if not set
        self.playlist_id = ytmusic_config.get("playlist_id")

    @staticmethod
    def write(config_data: dict) -> None:
        """write toml file with current vars"""
        with open(TOML_PATH, "w") as f:
            f.write("[local_files]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')
            f.write("[ytmusic]\n")
            f.write(f'client_id = "{config_data["client_id"]}"\n')
            f.write(f'client_secret = "{config_data["client_secret"]}"\n')
            if config_data.get("playlist_id"):
                f.write(f'playlist_id = "{config_data["playlist_id"]}"\n')


def check_ytmusic_setup_oauth() -> None:
    """Check if YouTube Music is properly set up using OAuth"""
    config = Config()
    if not config.client_id or not config.client_secret:
        logger.error("YouTube Music OAuth credentials not set up.")
        logger.info("\nTo set up YouTube Music OAuth authentication:")
        logger.info("1. Go to https://console.cloud.google.com")
        logger.info("2. Create a new project or select an existing one")
        logger.info("3. Enable the YouTube Data API v3")
        logger.info("4. Go to APIs & Services > OAuth consent screen")
        logger.info("   - Set User Type to 'External'")
        logger.info("   - Fill in required fields (App name, User support email, etc.)")
        logger.info("   - Add your Google account email under 'Test users'")
        logger.info("5. Go to APIs & Services > Credentials")
        logger.info("   - Create OAuth 2.0 Client ID")
        logger.info(
            "   - Select 'TVs and Limited Input devices' as the application type"
        )
        logger.info("   - Copy the Client ID and Client Secret")
        logger.info("\nThen add them to your config.toml file:")
        logger.info("[ytmusic]")
        logger.info("client_id = YOUR_CLIENT_ID")
        logger.info("client_secret = YOUR_CLIENT_SECRET")
        logger.info(
            "\nAfter that, run 'uv run ytmusicapi oauth' in your terminal to create oauth.json"
        )
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)

    if not OAUTH_PATH.is_file():
        logger.error("oauth.json file not found.")
        logger.info(
            f"\nRun 'uv run ytmusicapi oauth' in your terminal to create {OAUTH_PATH}"
        )
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)
    logger.success(f"Found oauth.json at: {OAUTH_PATH}")


def check_ytmusic_setup_browser() -> None:
    """Check if YouTube Music is properly set up using browser cookies"""
    if not BROWSER_PATH.is_file():
        logger.error("browser.json file not found.")
        logger.info("\nTo set up YouTube Music browser authentication:")
        logger.info("1. Follow the instructions at:")
        logger.info("   https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")
        logger.info(f"2. Create a file {BROWSER_PATH} with your browser credentials")
        sys.exit(1)
    logger.success(f"Found browser.json at: {BROWSER_PATH}")


def choose_auth_method() -> str:
    """Let user choose between OAuth and browser cookie authentication"""
    questions = [
        inquirer.List(
            "auth_method",
            message="Choose YouTube Music authentication method",
            choices=[
                ("OAuth (recommended)", "oauth"),
                ("Browser Cookies", "browser"),
            ],
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Authentication method selection cancelled")
    return answers["auth_method"]


def setup_ytmusic() -> YTMusic:
    """Initialize YouTube Music client"""
    auth_method = choose_auth_method()

    if auth_method == "oauth":
        check_ytmusic_setup_oauth()
        config = Config()
        oauth_credentials = OAuthCredentials(
            client_id=config.client_id, client_secret=config.client_secret
        )
        return YTMusic(str(OAUTH_PATH), oauth_credentials=oauth_credentials)
    else:  # browser method
        check_ytmusic_setup_browser()
        return YTMusic(str(BROWSER_PATH))


def list_user_playlists(ytm: YTMusic) -> list[PlaylistInfo]:
    """Get all playlists owned by the user

    Returns:
        list: List of dicts containing playlist info (name, id, track_count)
    """
    logger.info("Fetching your YouTube Music playlists...")
    playlists = ytm.get_library_playlists()

    # Format output
    user_playlists: list[PlaylistInfo] = []
    liked_music: PlaylistInfo | None = None

    for playlist in playlists:
        try:
            if playlist["playlistId"] == "LM":
                # Special case for Liked Music
                try:
                    ytm.get_liked_songs()
                except Exception as e:
                    logger.warning(f"Could not get liked songs count: {e}")
                liked_music = {
                    "name": playlist["title"],
                    "id": playlist["playlistId"],
                    "track_count": 0,
                }
                continue
            else:
                # Regular playlist
                try:
                    playlist_details = ytm.get_playlist(playlist["playlistId"])
                    track_count = playlist_details.get("trackCount", 0)
                except Exception as e:
                    logger.warning(
                        f"Could not get track count for playlist {playlist['title']}: {e}"
                    )
                    track_count = 0

                user_playlists.append(
                    {
                        "name": playlist["title"],
                        "id": playlist["playlistId"],
                        "track_count": track_count,
                    }
                )
        except Exception as e:
            logger.warning(
                f"Error processing playlist {playlist.get('title', 'Unknown')}: {e}"
            )
            continue

    # Sort regular playlists alphabetically
    user_playlists.sort(key=lambda x: x["name"].lower())

    # Add Liked Music first if it exists
    if liked_music:
        return [liked_music] + user_playlists
    return user_playlists


def select_playlist(ytm: YTMusic, playlist_id: str | None = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            if playlist_id == "LM":
                # Special case for Liked Music
                try:
                    ytm.get_liked_songs()
                except Exception as e:
                    logger.warning(f"Could not get liked songs count: {e}")
                logger.success('Using YouTube Music playlist "Liked Music"')
                return "LM"
            else:
                playlist = ytm.get_playlist(playlist_id)
                logger.success(f'Using YouTube Music playlist "{playlist["title"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    while True:
        # Get user's playlists
        playlists = list_user_playlists(ytm)

        if not playlists:
            raise Exception("No playlists found for user")

        # Create choices list for inquirer with formatted display
        choices = [
            (f"{playlist['name']} ({playlist['track_count']} tracks)", playlist["id"])
            for playlist in playlists
        ]
        # Add create new playlist option at the end
        choices.append(("Create new playlist", "new"))

        questions = [
            inquirer.List(
                "playlist_id",
                message="Select a YouTube Music playlist",
                choices=choices,
                carousel=True,
            ),
        ]

        answers = inquirer.prompt(questions)
        if not answers:  # User pressed Ctrl+C
            raise KeyboardInterrupt("YouTube Music playlist selection cancelled.")

        selected_id = answers["playlist_id"]

        if selected_id == "new":
            # Prompt for new playlist details
            questions = [
                inquirer.Text(
                    "name",
                    message="Enter playlist name",
                ),
                inquirer.Text(
                    "description",
                    message="Enter playlist description (optional)",
                    default="",
                ),
            ]
            answers = inquirer.prompt(questions)
            if not answers:  # User pressed Ctrl+C
                continue  # Go back to playlist selection

            try:
                # Create new playlist
                playlist_id = create_playlist(
                    ytm, answers["name"], answers["description"]
                )
                logger.success(f'Created and selected new playlist "{answers["name"]}"')
                return playlist_id
            except Exception as e:
                logger.error(f"Failed to create playlist: {e}")
                continue  # Go back to playlist selection

        # For existing playlist selection
        selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
        logger.success(f'Using YouTube Music playlist "{selected_name}"')
        return selected_id


def get_ytmusic_track_details(ytm: YTMusic, ytmusic_playlist_id: str) -> list[dict]:
    """Get track details (name, artist) from YouTube Music playlist for searching"""
    logger.info(
        f'Fetching tracks from YouTube Music playlist "{ytmusic_playlist_id}"...'
    )
    tracks: list[dict] = []
    try:
        if ytmusic_playlist_id == "LM":
            # Special case for Liked Music
            results = ytm.get_liked_songs()
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
        else:
            # Regular playlist
            results = ytm.get_playlist(ytmusic_playlist_id)
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
    except Exception as e:
        logger.error(f"Error fetching YouTube Music playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in YouTube Music playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in YouTube Music playlist")
    return tracks


def get_ytmusic_track_ids(ytm: YTMusic, ytmusic_playlist_id: str) -> set[str]:
    """Get track IDs from YouTube Music playlist for duplicate checking"""
    logger.info("Fetching existing tracks from YouTube Music playlist...")
    existing_tracks: set[str] = set()
    results = ytm.get_playlist(ytmusic_playlist_id)
    for track in results["tracks"]:
        if track.get("videoId"):
            existing_tracks.add(track["videoId"])
    return existing_tracks


def create_playlist(ytm: YTMusic, name: str, description: str = "") -> str:
    """Create a new YouTube Music playlist

    Args:
        ytm: YouTube Music client
        name: Name of the playlist
        description: Optional description for the playlist

    Returns:
        str: ID of the created playlist

    Raises:
        Exception: If playlist creation fails
    """
    try:
        logger.info(f'Creating new YouTube Music playlist "{name}"...')
        result = ytm.create_playlist(name, description)
        playlist_id = result if isinstance(result, str) else result.get("playlistId")
        if not playlist_id:
            raise Exception("Failed to get playlist ID from response")
        logger.success(f'Created playlist "{name}" with ID: {playlist_id}')
        return playlist_id
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        raise


def search_ytmusic_tracks(
    ytm: YTMusic, track_name: str, artist_name: str, file_name: str | None = None
) -> list[dict] | None:
    """Search for track on YouTube Music and return list of potential matches

    Args:
        ytm: YouTube Music client
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

    query = f"{track_name} {artist_name}"
    if file_name:
        logger.info(f'\nLocal file: "{file_name}"')
    logger.info(f'Searching YouTube Music for "{track_name} - {artist_name}"')

    max_retries = 3
    retry_delay = 5  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            results = ytm.search(query, filter="songs", limit=5)
            if not results:
                logger.error("No matches found on YouTube Music")
                return None

            # Format matches
            matches: list[dict] = []
            for track in results:
                if not track.get("name") or not track.get("artists"):
                    continue

                matches.append(
                    {
                        "id": track["videoId"],
                        "name": track["name"],
                        "artist": track["artists"][0]["name"],
                    }
                )

            if not matches:
                logger.error("No valid matches found on YouTube Music")
                return None

            return matches

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
                    logger.error("Max retries reached for rate limit.")
                    return None
            else:
                logger.error(f"Error searching YouTube Music: {e}")
                logger.error(f"Query was: {query}")
                return None

    return None


def select_match(
    ytm: YTMusic, matches: list[dict], auto_first: bool = False
) -> str | None:
    """Let user select a match from the list of potential matches

    Args:
        ytm: YouTube Music client
        matches: List of potential matches with id, name, and artist
        auto_first: If True, automatically select the first match

    Returns:
        str | None: Selected track ID or None if skipped/invalid
    """
    # Show all potential matches
    logger.info("\nPotential matches from YouTube Music:")
    for i, track in enumerate(matches, 1):
        logger.info(f"{i}. Track: {track['name']}")
        logger.info(f"   Artist: {track['artist']}")

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
            return select_match(ytm, matches, auto_first=True)

    if choice == "s":
        logger.warning("Track skipped")
        return None

    if choice == "" or choice == "1":
        choice = "1"

    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        track_id = matches[int(choice) - 1]["id"]
        track_info = ytm.get_song(track_id)
        if (
            not track_info
            or not track_info.get("name")
            or not track_info.get("artists")
        ):
            logger.error("Could not get track details from YouTube Music")
            return None
        logger.success(
            f'Selected from YouTube Music: "{track_info["name"]} - {track_info["artists"][0]["name"]}"'
        )
        return track_id

    logger.warning("Invalid choice - track skipped")
    return None
