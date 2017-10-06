from urllib.request import urlopen
import os
from bs4 import BeautifulSoup
from APIMocker import APIMocker
from plenar_parser import parse_plenar_transcript
from collections import Counter
import glob

BASE_URL = 'https://www.bundestag.de'
PLENAR_URL_SCHEME = BASE_URL + '/ajax/filterlist/de/dokumente/protokolle/plenarprotokolle/plenarprotokolle/-/455046/h_121016ea2f478ddcf3be50587d9fa1f8?limit={limit}&noFilterSet=true&offset={offset}'


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
    data_dir = '/tmp/scraper'

    data = urlopen(plenar_url).read()
    soup = BeautifulSoup(data, "html5lib")
    links = soup.find_all("a")

    files = []
    for link in links:
        href = link['href']
        filename = os.path.basename(href)
        abs_path = os.path.join(data_dir, filename)
        if not os.path.exists(abs_path):
            print("Downloading {} to {}".format(BASE_URL + href, filename))
            fetch_resource(BASE_URL + href, abs_path)
        else:
            print("File", filename, "exists, skipping")
        files.append(abs_path)

    return files


def excused_stats(excused):
    stats = Counter()
    for e in excused:
        stats[e['party']] += 1
    return stats


if __name__ == "__main__":
    OUT_PATH = '../../plenarnavi_frontend/public/data'
    if not os.path.isdir(OUT_PATH): os.makedirs(OUT_PATH)

    plenar_params = {'limit': 5, 'offset': 0}

    files = scrape_protocols(plenar_params)  # TODO: aparently, the limit parameter doesn't work

    #files = glob.glob('/tmp/scraper/*.txt')

    mock_plenums = []
    for f in files:
        metadata, topic_summaries, contributions, excused = parse_plenar_transcript(f)
        print("Plenarprotokoll", os.path.basename(f))
        print("meta: ", metadata)
        print("number contributions:", len(contributions))
        print("number excused deputies:", len(excused))

        e_stats = excused_stats(excused)

        mock_plenums.append(APIMocker.plenum_short(metadata, topic_summaries, e_stats))
        mock_plenum = APIMocker.plenum(metadata, topic_summaries, contributions, excused)

        filebase = os.path.join(OUT_PATH, os.path.basename(f)[2:5])

        APIMocker.persist_json(mock_plenum, filebase + '.json')
    APIMocker.persist_json(mock_plenums, os.path.join(OUT_PATH, 'plenums.json'))

