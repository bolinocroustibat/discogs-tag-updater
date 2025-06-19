# Import all main functions from script modules
from .local_to_spotify import main as add_local_tracks_to_spotify
from .local_to_ytmusic import main as add_local_tracks_to_ytmusic
from .ytmusic_to_spotify import main as import_ytmusic_to_spotify
from .spotify_to_ytmusic import main as import_spotify_to_ytmusic
from .manage_spotify_duplicates import main as manage_spotify_duplicates

__all__ = [
    "add_local_tracks_to_spotify",
    "add_local_tracks_to_ytmusic",
    "import_ytmusic_to_spotify",
    "import_spotify_to_ytmusic",
    "manage_spotify_duplicates",
]
