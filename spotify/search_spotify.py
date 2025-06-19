import spotipy
from logger import FileLogger

MAX_MATCHES_TO_DISPLAY = 4  # Maximum number of matches to show for each track
logger = FileLogger("spotify/spotify.log")


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

        # Only return first N matches
        return matches[:MAX_MATCHES_TO_DISPLAY]

    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        logger.error(f"Query was: {query}")
        return None
