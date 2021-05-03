# Discogs Tag Updater

Fork from https://notabug.org/Aesir.
Updates genre, year and image of .mp3 and .flac files based on title and artist using the Discogs database.

## Prerequisites

- Requires Python 3.7 and [Poetry](https://python-poetry.org/).
- Requires a Discogs developper account and free API key: [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)

## Install
```sh
poetry install
```

## Launch
```sh
poetry run python discogs_api-aesir.py
```

## Config
On the first run, it will ask for some inputs. You can change these variables after in the `discogs_tag.ini` file.  
For the discogs access token, you can create one [here](https://www.discogs.com/settings/developers).

## Options
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

## Known Problems
- If you are using the compiled mac version, the `discogs_tag.ini` file will be created under your user account `/User/<username>/discogs_tag.ini`

## See it in action
[https://youtu.be/mWQZJS94p40](https://youtu.be/mWQZJS94p40)  
Thanks to Bas Curtiz for creating the video.
