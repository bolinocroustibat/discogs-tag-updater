import time
from typing import TypedDict, Protocol

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mininterface import Mininterface

from spotify.common import setup_spotify, select_playlist


class TrackInfo(TypedDict):
    name: str
    id: str
    uri: str


class MininterfaceProtocol(Protocol):
    def dialog(self, message: str, title: str | None = None) -> None: ...
    def confirm(self, message: str) -> bool: ...


def find_duplicates(m: Mininterface, sp: spotipy.Spotify, playlist_id: str) -> dict[str, list[TrackInfo]]:
    """Find duplicate tracks in a Spotify playlist"""
    m.dialog("Fetching Spotify playlist tracks...")

    # Get all tracks from playlist
    tracks: dict[str, list[TrackInfo]] = {}  # key: track_id, value: list of track_info
    try:
        # First get basic playlist info
        playlist = sp.playlist(playlist_id)
        if not playlist:
            m.dialog("Could not access playlist", title="Error")
            return {}
        m.dialog(
            f"Successfully connected to Spotify API - Playlist: {playlist.get('name')}"
        )

    except Exception as e:
        m.dialog(f"Error accessing playlist: {e}", title="Error")
        return {}

    total_tracks = 0
    try:
        if not playlist.get("tracks") or not playlist["tracks"].get("items"):
            m.dialog("No tracks found in playlist", title="Error")
            return {}

        for item in playlist["tracks"]["items"]:
            track = item["track"]
            if not track:  # Skip empty tracks
                continue

            total_tracks += 1
            track_id = track["id"]

            # Safely get artist name with fallbacks
            artist = "Unknown Artist"
            if track.get("artists") and track["artists"]:
                artist = track["artists"][0].get("name", "Unknown Artist")

            # Safely get title
            title = track.get("name", "Unknown Title")
            track_name = f"{title} - {artist}"

            track_info: TrackInfo = {
                "name": track_name,
                "id": track_id,
                "uri": track["uri"],
            }

            if track_id in tracks:
                tracks[track_id].append(track_info)
            else:
                tracks[track_id] = [track_info]

        m.dialog(f"Processed {total_tracks} tracks from Spotify playlist")
    except Exception as e:
        m.dialog(f"Error processing tracks: {e}", title="Error")
        return {}

    # Filter only duplicates
    duplicates = {k: v for k, v in tracks.items() if len(v) > 1}
    return duplicates


def remove_duplicates(
    m: Mininterface, sp: spotipy.Spotify, playlist_id: str, duplicates: dict[str, list[TrackInfo]]
) -> None:
    """Remove duplicate tracks from Spotify playlist keeping the first instance"""
    if not duplicates:
        return

    tracks_to_remove: list[dict[str, str]] = []
    for track_id, instances in duplicates.items():
        # Keep the first instance and remove the rest
        for instance in instances[1:]:  # Skip first instance
            track_info = {
                "uri": instance["uri"],
            }
            tracks_to_remove.append(track_info)

    if tracks_to_remove:
        try:
            m.dialog(f"Attempting to remove {len(tracks_to_remove)} tracks")
            for track in tracks_to_remove:
                try:
                    sp.playlist_remove_all_occurrences_of_items(playlist_id, [track["uri"]])
                except Exception as e:
                    m.dialog(f"Error removing track: {e}", title="Error")
                time.sleep(1)  # Rate limiting
            m.dialog(
                f"Successfully removed {len(tracks_to_remove)} duplicate tracks from Spotify playlist",
                title="Success"
            )
        except Exception as e:
            m.dialog(f"Error removing tracks from Spotify playlist: {e}", title="Error")
            m.dialog(
                "Please make sure you have the necessary permissions to modify this playlist.",
                title="Error"
            )


def main(m: Mininterface) -> None:
    sp = setup_spotify()

    # Get playlist ID from user selection
    playlist_id = select_playlist(sp)

    duplicates = find_duplicates(m, sp, playlist_id)

    if not duplicates:
        m.dialog("No duplicates found in Spotify playlist!", title="Success")
        return

    m.dialog(
        f"\nFound {sum(len(v) - 1 for v in duplicates.values())} duplicate tracks in Spotify playlist:"
    )
    for track_id, instances in duplicates.items():
        # Get the track name from the first instance (they're all the same track)
        track_name = instances[0]["name"]
        m.dialog(f"\n{track_name}")
        m.dialog(f"  Found {len(instances)} instances")

    if m.confirm("Do you want to remove duplicates from Spotify playlist?"):
        remove_duplicates(m, sp, playlist_id, duplicates)
