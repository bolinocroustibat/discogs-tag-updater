# Music Sync Toolbox

A CLI toolbox for syncing your music across Spotify, YouTube Music and you local music files. Features include:
- Bidirectional playlist synchronization between Spotify and YouTube Music
- Automatic duplicate detection and removal in Spotify and YouTube Music playlists
- Seamless import of local music files into Spotify playlists
- Metadata enrichment and music files management using Discogs database

## Prerequisites

- Requires Python >=3.11 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- For the Discogs tag updater, it requires a Discogs developper account and free API key: [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)
- For Spotify integration: requires a Spotify Developer account: [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
- For YouTube Music integration: it requires either:
  - A YouTube Music Developer account: [https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials](https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials)
  - Or a YouTube Music session cookie file (see [https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)), but this might not be working as expected.

## Install
```sh
uv sync
```

## Usage
```sh
uv run music-sync
```

This will show a menu with the different features available.

## Config
On the first run, it will ask for some inputs. You can change these variables after in the `config.toml` file, following the `config.toml.example` file.

### Common Setup
`path`  
The path to your music files directory. This is only required for:
- Local file tag updates from Discogs
- File renaming based on tags
- Adding local files to Spotify playlist

### Local Files Setup
For the discogs access token, you can create one [here](https://www.discogs.com/settings/developers).

### Spotify Setup
1. Create an application in your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Get your `client_id` and `client_secret` from the application settings
3. Add `http://localhost:8888/callback` to the Redirect URIs in your application settings
4. Get your target playlist ID (the last part of the playlist URL: spotify:playlist:**YOUR_PLAYLIST_ID**)

### YouTube Music Setup
You can choose between two authentication methods:

1. OAuth (Recommended):
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials (TVs and Limited Input devices type)
   - Add your credentials to `config.toml`
   - Run `uv run ytmusicapi oauth` to create `oauth.json`

2. Browser Cookies:
   - Follow the instructions at [ytmusicapi browser setup](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)
   - Create a `browser.json` file with your browser credentials

## Options

### Common Options
`path`  
The path to your music files directory. Only required for features that work with local files.

### Local Files (💿) Options
`token`  
Your Discogs API token.

`overwrite_year = false`
If year tag is set on the file, it will not overwrite it.  
If year tag is empty, it will add it.

`overwrite_genre = false`
If genre tag is set on the file, it will not overwrite it.  
If genre tag is empty, it will add it.  

`embed_cover = true`
Enable or disable cover embedding feature. Will overwrite existing covers.

`overwrite_cover = false`
If cover is set on the file, it will not overwrite it.  
If cover is empty, it will add it.

`rename_file = false`
If file is already named correctly, it will not rename it.
If artist and/or title is empty, it will not rename it.
Otherwise, it will rename it to `artist - title.ext`.

### Spotify (🟢) Options
`client_id`  
Your Spotify application client ID.

`client_secret`  
Your Spotify application client secret.

`redirect_uri`  
The redirect URI for OAuth authentication (default: http://localhost:8888/callback).

`playlist_id`  
The ID of the playlist where you want to add tracks. If not set, you'll be prompted to select a playlist when running the script.

### YouTube Music (🔴) Options
`client_id`  
Your YouTube Music OAuth client ID (only needed for OAuth method).

`client_secret`  
Your YouTube Music OAuth client secret (only needed for OAuth method).

`playlist_id`  
The ID of the playlist where you want to add tracks. If not set, you'll be prompted to select a playlist when running the script.

## TODO

### Common Improvements
- Ask user for local path if not provided in `config.toml` for:
  - Local file tag updates from Discogs
  - Spotify (🟢) utilities
  - YouTube Music (🔴) utilities

### Spotify (🟢) Improvements
- In `spotify/add_tracks.py`: Compare Spotify matches with local files BEFORE asking user for match selection
  - This will help identify the best match automatically
  - Only ask user if no exact match is found

### Code Refactoring for Django Backend
- Refactor core functionality to be framework-agnostic:
  - Move all business logic into separate service classes
  - Return structured responses with success/error messages and data
  - Remove direct CLI interactions (print, input) from core functions
  - Create separate handlers for CLI and web interfaces
- Example structure:
  ```python
  class TagUpdaterService:
      def update_tags(self, file_path: Path) -> dict:
          return {
              "success": bool,
              "message": str,
              "data": {
                  "genres_updated": bool,
                  "year_updated": bool,
                  "cover_updated": bool,
                  "file_renamed": bool,
                  "new_path": str | None
              }
          }
  ```
- Benefits:
  - Same core code can be used in CLI and web interface
  - Better error handling and reporting
  - Easier to test individual components
  - Progress updates can be sent to web interface via WebSocket
  - Configuration can be stored in database instead of files
