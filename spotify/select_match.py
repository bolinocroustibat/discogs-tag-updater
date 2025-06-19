import spotipy
from spotify.logger import logger


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
