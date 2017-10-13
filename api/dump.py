from urllib.request import urlopen
import json
import os

BACKEND_URL="http://localhost:5000"
OUT_DIR='/tmp/plenarnavi_api_dump'

def persist_json(dictionary, filename):
    with open(filename, 'w', encoding='utf8') as json_file:
        json.dump(dictionary, json_file, ensure_ascii=False, indent=4)

def fetch_resource(url, filename):
    dir_name = os.path.dirname(filename)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)

    f = urlopen(url)
    data = f.read()
    with open(filename, "wb") as local_file:
        local_file.write(data)
    return data

if __name__ == "__main__":
    print("Dumping JSON responses from plenarnavi backend at '{}' to '{}'".format(BACKEND_URL, OUT_DIR))

    sessions_url = BACKEND_URL + '/sessions'

    sessions_filename = os.path.join(OUT_DIR, 'sessions.json')
    sessions = fetch_resource(sessions_url, sessions_filename)

    print("Sessions JSON: '{}'".format(sessions_filename))

    sessions_json = json.loads(sessions)

    for s in sessions_json:
        session_url = BACKEND_URL + '/sessions/' + s['uuid']
        session_filename = os.path.join(OUT_DIR, 
            '{:0>2}{:0>3}.json'.format(s['electoral_period'], s['session_number']))
        fetch_resource(session_url, session_filename)
        print("Session '{}': {}".format(s['uuid'], session_filename))
