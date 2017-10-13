# Plenarnavi Backend

Parses the text based transcripts of the plenary debates in the German Bundestag.

## Usage

First, install all required python modules

`pip install -r requirements.txt`

Scrape the plenary debate transcripts and information about delegates

`python -m parsers.scraper`

Run the flask server

`python flask_app.py`

It's also possible to dump .json files of the API requests

`python -m api.dump`