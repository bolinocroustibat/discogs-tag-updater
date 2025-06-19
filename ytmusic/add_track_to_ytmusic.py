from ytmusicapi import YTMusic
import time
from logger import FileLogger
from pathlib import Path

logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def add_track_to_ytmusic(
    ytm: YTMusic,
    video_id: str,
    ytmusic_playlist_id: str,
    retry_delay: int,
) -> tuple[bool, int]:
    """Add track to YouTube Music playlist with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if ytmusic_playlist_id == "LM":
                # Special case for Liked Music - use rate_song instead of add_playlist_items
                ytm.rate_song(video_id, "LIKE")
            else:
                # Regular playlist
                ytm.add_playlist_items(ytmusic_playlist_id, [video_id])
            logger.success("Track added to YouTube Music playlist.")
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
                logger.error(f"Error adding to YouTube Music playlist: {e}")
                logger.error(f"Video ID: {video_id}")
                logger.error(f"Playlist ID: {ytmusic_playlist_id}")
                return False, retry_delay
    return False, retry_delay
