from ytmusicapi import YTMusic
import inquirer
from .list_user_playlists import list_user_playlists
from logger import FileLogger
from pathlib import Path

logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def select_playlist(ytm: YTMusic, playlist_id: str | None = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            if playlist_id == "LM":
                # Special case for Liked Music
                try:
                    ytm.get_liked_songs(
                        limit=1
                    )  # Just check if we can access liked songs
                    logger.success('Using YouTube Music playlist "Liked Music"')
                    return playlist_id
                except Exception as e:
                    logger.error(f"Error accessing liked music: {e}")
                    # Fall through to manual selection
            else:
                playlist = ytm.get_playlist(playlist_id)
                logger.success(f'Using YouTube Music playlist "{playlist["title"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(ytm)

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
            message="Select a YouTube Music playlist",
            choices=choices,
            carousel=True,  # Show all options without scrolling
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using YouTube Music playlist "{selected_name}"')
    return selected_id
