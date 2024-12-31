# Audio files tag & Spotify utilities

## Prerequisites

- Requires Python >=3.7 and a modern Python environement manager like [Poetry](https://python-poetry.org/) or [PDM](https://pdm.fming.dev/).
- For the Discogs tag updater, it requires a Discogs developper account and free API key: [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)
- For Spotify integration: requires a Spotify Developer account: [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)

## Install
```sh
uv sync
```

## Config
On the first run, it will ask for some inputs. You can change these variables after in the `config.ini` file, following the `config.ini.example` file.

### Common Setup
`path`  
The path to your music files directory.

### Discogs Setup
For the discogs access token, you can create one [here](https://www.discogs.com/settings/developers).

### Spotify Setup
1. Create an application in your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Get your `client_id` and `client_secret` from the application settings
3. Add `http://localhost:8888/callback` to the Redirect URIs in your application settings
4. Get your target playlist ID (the last part of the playlist URL: spotify:playlist:**YOUR_PLAYLIST_ID**)

## Options

### Discogs Options
`overwrite_year = False`  
If year tag is set on the file, it will not overwrite it.  
If year tag is empty, it will add it.

`overwrite_genre = False`  
If genre tag is set on the file, it will not overwrite it.  
If genre tag is empty, it will add it.  

`embed_cover = True`  
Enable or disable cover embedding feature. Will overwrite existing covers.

`overwrite_cover = False`   
If cover is set on the file, it will not overwrite it.  
If cover is empty, it will add it.

`rename_file = True`   
If file is already named correctly, it will not rename it.
If artist and/or title is empty, it will not rename it.
Otherwise, it will rename it to `artist - title.ext`.

### Spotify Options
`client_id`  
Your Spotify application client ID.

`client_secret`  
Your Spotify application client secret.

`playlist_id`  
The ID of the playlist where you want to add tracks.

`redirect_uri`  
The redirect URI for OAuth authentication (default: http://localhost:8888/callback).

## Scripts

### Discogs Tag Updater

Forked from https://notabug.org/Aesir.

Updates genre, year and image of .mp3 and .flac files based on title and artist using the Discogs database, and rename the file based on the title and artist.

#### How to run

Updates your music files with metadata from Discogs:
```sh
uv run discogs.py
```

#### See it in action
[https://youtu.be/mWQZJS94p40](https://youtu.be/mWQZJS94p40)  
Thanks to Bas Curtiz for creating the video.

### Spotify utilities

The first time you run the Spotify script, it will:
1. Open your browser
2. Ask you to log in to Spotify
3. Request permission to modify your playlists
4. Save the authentication token locally for future use

For each track found, you'll be prompted to confirm whether you want to add it to your playlist.

#### Add tracks to Spotify

Searches for your music files on Spotify and adds them to a playlist:
```sh
uv run spotify/add_tracks.py
```

### Spotify Duplicate Manager

Manages duplicates in your Spotify playlist.
```sh
uv run spotify/manage_duplicates.py
```
