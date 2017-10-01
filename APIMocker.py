import json

class APIMocker(object):
    def persist_json(dictionary, filename):
        with open(filename, 'w', encoding='utf8') as json_file:
            json.dump(dictionary, json_file, ensure_ascii=False, indent=4)

    def plenum_short(header, topic_summaries, excused_stats):
        desc = header.copy()
        desc['agendaItems'] = topic_summaries
        desc['stats'] = {
            'absences': excused_stats
        }
        return desc

    def plenum(header, topic_summaries, contributions, excused):
        p = {
            'absentRepresentatives': excused,
            'date': header['date'],
            'session': header['session'],
            'agendaItems': topic_summaries,
            'contributions': contributions
        }
        return p

    def 