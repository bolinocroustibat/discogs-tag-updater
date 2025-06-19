from ytmusicapi import YTMusic
from ytmusic.logger import logger


def select_match(
    ytm: YTMusic, matches: list[dict], auto_first: bool = False
) -> str | None:
    """
    Let the user select a match from a list of potential YouTube Music matches.

    Args:
        ytm: Authenticated YTMusic client instance.
        matches: List of potential matches, each with id, name, and artist.
        auto_first: If True, automatically select the first match without prompting.

    Returns:
        str | None: Selected video ID, or None if skipped or invalid.

    Notes:
        - Prompts the user to select a match by number or skip.
        - Returns None if the user skips or makes an invalid selection.
        - When auto_first is True, automatically selects the first match.
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
            input("\nSelect match number (1 is default, 's' to skip): ").strip().lower()
        )
        if choice == "s":
            logger.warning("Track skipped")
            return None

    if choice == "" or choice == "1":
        choice = "1"

    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        video_id = matches[int(choice) - 1]["id"]
        logger.success(
            f'Selected from YouTube Music: "{matches[int(choice) - 1]["name"]} - {matches[int(choice) - 1]["artist"]}"'
        )
        return video_id

    logger.warning("Invalid choice - track skipped")
    return None
