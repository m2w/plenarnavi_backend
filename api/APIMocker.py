import json
import copy
import os
from DatabaseManager import DatabaseManager

class APIMocker(object):
    def __init__(self, db, out_folder):
        self.db = db
        self.out_folder = out_folder

    @staticmethod
    def persist_json(dictionary, filename):
        with open(filename, 'w', encoding='utf8') as json_file:
            json.dump(dictionary, json_file, ensure_ascii=False, indent=4)

    @staticmethod
    def session_json(s, short=False):
        p = {
            'uuid': str(s.uuid),
            'start_time': s.start_time.isoformat(),
            'end_time': s.end_time.isoformat(),
            'session_number': s.session_number,
            'electoral_period': s.electoral_period,
            'agendaItems': [APIMocker.agenda_json(i) for i in s.agenda_items],
        }
        if not short:
            p['absentees'] = [APIMocker.person_json(a) for a in s.absentees]
            p['speeches'] = [APIMocker.speech_json(s) for s in s.speeches]
        return p

    @staticmethod
    def persist_session_json(s, filename):
        json = APIMocker.session_json(s)
        APIMocker.persist_json(json, filename)

    @staticmethod
    def person_json(a):
        return {
            'uuid': str(a.uuid),
            'first_name': a.first_name,
            'last_name': a.last_name,
            'party': a.party,
            'degree': a.degree,
            'image_url': a.image_url,
        }

    @staticmethod
    def agenda_json(i):
        return {
            'uuid': str(i.uuid),
            'name': i.name,
            'summary': i.summary,
            'agenda_id': i.agenda_id
        }

    @staticmethod
    def speech_json(s):
        return {
            'uuid': str(s.uuid),
            'text': s.text,
            'speaker': APIMocker.person_json(s.person),
            'speech_id': s.speech_id
        }

    def get_session_list(self, electoral_period):
        ss = db.get_session_list(electoral_period)
        json = [APIMocker.session_json(s, short=True) for s in ss]
        filename = os.path.join(self.out_folder, 'sessions.json')
        APIMocker.persist_json(json, filename)
        print("Wrote session list for ep=", electoral_period, "to", filename)
        return json

    def get_session_by_uuid(self, uuid):
        s = self.db.get_session_by_uuid(uuid)
        json = APIMocker.session_json(s)
        filename = os.path.join(self.out_folder, 
            "{:0>2}{:0>3}.json".format(s.electoral_period, s.session_number))
        APIMocker.persist_json(json, filename)
        print("Wrote session for uuid=", uuid, "to", filename)
        return json


if __name__ == '__main__':
    OUT_PATH = '../../plenarnavi_frontend/public/data'
    if not os.path.isdir(OUT_PATH): os.makedirs(OUT_PATH)

    db = DatabaseManager('data.db')
    api = APIMocker(db, OUT_PATH)

    session_list = api.get_session_list(18)

    for s in session_list:
        uuid = s['uuid']
        api.get_session_by_uuid(uuid)


# TODO: Divide speeches into multiple segments for each agendaitem
# 1. speech_id, cursor_position -> split speech_id at cursor_position, increment speech_ids
# 2. agenda_item_id [speech_id]
# client holds ground truth -> put not post


# def excused_stats(excused):
#     stats = Counter()
#     for e in excused:
#         stats[e['party']] += 1
#     return stats