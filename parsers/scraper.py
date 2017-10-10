from urllib.request import urlopen
import os
import glob
import logging
import json

from bs4 import BeautifulSoup

from APIMocker import APIMocker
from PlenarParser import PlenarParser
from DatabaseManager import DatabaseManager


BASE_URL = 'https://www.bundestag.de'
PLENAR_URL_SCHEME = BASE_URL + \
    '/ajax/filterlist/de/dokumente/protokolle/plenarprotokolle/plenarprotokolle/-/455046/h_121016ea2f478ddcf3be50587d9fa1f8?limit={limit}&noFilterSet=true&offset={offset}'
DATA_DIR = '/tmp/scraper'
AW_URL = 'https://www.abgeordnetenwatch.de/api/parliament/hamburg/deputies.json'


def fetch_resource(url, filename):
    dir_name = os.path.dirname(filename)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)

    f = urlopen(url)
    data = f.read()
    with open(filename, "wb") as local_file:
        local_file.write(data)


def scrape_protocols(params):
    plenar_url = PLENAR_URL_SCHEME.format(**params)

    data = urlopen(plenar_url).read()
    soup = BeautifulSoup(data, "html5lib")
    links = soup.find_all("a")

    files = []
    for link in links:
        href = link['href']
        filename = os.path.basename(href)
        abs_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(abs_path):
            print("Downloading {} to {}".format(BASE_URL + href, filename))
            fetch_resource(BASE_URL + href, abs_path)
        else:
            print("File", filename, "exists, skipping")
        files.append(abs_path)
    return files


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=FORMAT)

    # Scrape the plenary transcripts from bundestag.de. We work with the .txt files since
    # they are easier to parse than the alternative PDFs. The
    # Note: the limit parameter does not seem to work, there are always 20 results in the
    #       HTML response.
    plenar_params = {'limit': 20, 'offset': 0}
    plenar_files = scrape_protocols(plenar_params)

    # Get the deputies information from Abgeordnetenwatch (http://abgeordnetenwatch.de/api)
    # TODO: query past parliaments
    aw_data = json.loads(urlopen(AW_URL).read().decode())

    # The DatabaseManager handles all interaction with the database
    db = DatabaseManager('data.db')

    # Save the data from Abgeordnetenwatch to the database
    db.persist_aw_mdbs(aw_data)

    # Parse the plenary protocols and save them to the database
    for f in plenar_files:
        p = PlenarParser(f)
        metadata, absentees, absent_reasons, agenda_summary, debate = p.parse()
        _ = db.persist_session(metadata, absentees, agenda_summary, debate)

    db.close()
