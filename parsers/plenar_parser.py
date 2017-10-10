# -*- coding: utf-8 -*-
import copy
import itertools
import json
import logging
import re

from parsers.utils import pairwise

log = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)
log.setLevel(logging.DEBUG)


class Regex:
    absentee_reg_ = re.compile(r'^(?P<last_name>[\w-]+)(?: \((?P<electorate>\w+)\))?, ' +
                               r'(?P<titles>(?:\w{1,2}\. )+)?(?P<first_name>[\w-]+)\s*(?P<reason>\*+)*\s*\n' +
                               r'(?P<party>[\w/ ]+)\s*\n', re.MULTILINE)

    absentee_reason_reg_ = re.compile(r'^(\*+)\s*([\w ]+)')

    speaker_reg_ = re.compile(
        r'\n\s*(?P<role>[\w]+ )?(?P<titles>(?:\w{1,2}\. )*)?(?P<first_name>[\w-]+) (?P<last_name>[\w-]+) ?(?:\((?P<party>.*)\))?(?:,(?P<position>[\w ]+))?\:\s*\n')

    agenda_regs_ = [
        # re.compile(r'kommen? .* zum? ((?:Zusatz|Tagesordnungs)punkte?) (\d+(?:\w|(\w)\3+))'),
        # re.compile(r'((?:Zusatz|Tagesordnungs)punkte?) (\d+(?: (?:\w|(\w)\3+)?(?=[ .:]))?).*(?:\.|:)'),
        # re.compile(r'(?:rufe|jetzt).*((?:Zusatz|Tagesordnungs)punkte?) (\d+(?: (?:\w)\2*)?)(?: (und|bis) (\d+(?: (?:\w)\6*)?))? auf'),
        # re.compile(r'((?:Zusatz|Tagesordnungs)punkte?) (\d+(?: (?:\w)\3*)?).*((?:Zusatz|Tagesordnungs)punkte?) (\d+(?: (?:\w)\6*)?)'),

        re.compile(r'kommen? \w{0,10} (?:zum|zu den)? ((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w)?):'),
        re.compile(
            r'(?:rufe|jetzt) \w{0,10} ((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w+)?)(?: (und|bis) (\d+(?: \w+)?))? auf'),
        # re.compile(r'((?:Zusatz|Tagesordnungs)punkt[ens]*) ((?:(?:\d+(?: \w+)?)(?:, | sowie )(?:\d+(?: \w+)?))+)\.'),
        # re.compile(r'((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: (?:\w|(\w)\3+)?(?=[ .:]))?).*(?:\.|:)'),
        # re.compile(r'((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w+)?) sowie (?:zum|zu den)? ((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w+)?)'),
    ]

    session_reg_ = re.compile(r'\n\s*(\d+)\.\s*Sitzung\s*\n')

    date_reg_ = re.compile(r'\nBerlin,\s\w+,\sden\s(\d+)\.\s*([^\s]+)\s*(\d+)\s*\n')

    start_time_reg_ = re.compile(r'\nBeginn:\s*(\d+)[.:](\d+).*Uhr\s*\n')
    start_split_reg_ = re.compile(r'\nBeginn:\s*\d+[.:]\d+.*Uhr\s*\n')

    end_time_reg_ = re.compile(r'\n\(Schluss:\s*(\d+)[.:](\d+).*Uhr\)\.?\s*\n')
    end_split_reg_ = re.compile(r'\n\(Schluss:\s*\d+[.:]\d+.*Uhr\)\.?\s*\n')

    @staticmethod
    def strip_dict(groups):
        for k, v in groups.items():
            if type(v) is str:
                groups[k] = v.strip()
                if groups[k] == '': groups[k] = None
            else:
                groups[k] = v
        return groups

    @staticmethod
    def remove_nones(groups):
        return tuple([v for v in groups if v is not None])

    @staticmethod
    def strip_groups(groups):
        g = []
        for v in groups:
            g.append(v.strip())
        return tuple(g)


def parse_metadata(text):
    session = Regex.session_reg_.findall(text)[0]
    date = Regex.date_reg_.findall(text)[0]
    start = Regex.start_time_reg_.findall(text)[0]
    end = Regex.end_time_reg_.findall(text)[0]

    month_map = {
        'Januar': 1,
        'Februar': 2,
        'März': 3,
        'April': 4,
        'Mai': 5,
        'Juni': 6,
        'Juli': 7,
        'August': 8,
        'September': 9,
        'Oktober': 10,
        'November': 11,
        'Dezember': 12
    }

    return {
        'session': session,
        'date': "{}.{}.{}".format(date[0], month_map[date[1]], date[2]),
        'start_time': "{}:{}".format(start[0], start[1]),
        'end_time': "{}:{}".format(end[0], end[1])
    }


def parse_contributions(text):
    def is_invalid(s):
        tests = [
            s['first_name'][0].isupper(),
            s['last_name'][0].isupper(),
            len(s['first_name']) >= 2,
            len(s['last_name']) >= 2
        ]
        if not all(tests):
            log.debug("Discarting invalid contribution {}".format(s))

        # itertools.filterfalse() returns list of items where the predicate returns
        # false, hence the inverse logic
        return not all(tests)

    end = re.search(r'$', text)

    speakers = itertools.filterfalse(lambda x: is_invalid(x.groupdict()), Regex.speaker_reg_.finditer(text))

    # TODO: remove/fix
    aw_data = ''
    with open('../data/deputies.json') as f:
        aw_data = f.read()
    aw_data = json.loads(aw_data)

    contributions = []
    for m, m1 in pairwise(itertools.chain(speakers, [end])):
        contrib = {
            'speaker': match_abgeordnetenwatch(m.groupdict(), aw_data),
            'start_idx': m.start(),
            'end_idx': m1.start(),
            'speech': text[m.end():m1.start()]
        }
        contributions.append(contrib)
    return contributions


def inject_agenda_items(contributions, agenda_items):
    def is_speaker_in_range(t, c):
        return 'speaker' in c and (c['start_idx'] <= t['start_idx'] and c['end_idx'] >= t['start_idx'])

    contrib_agenda = copy.deepcopy(contributions)

    # add dummy elements in list of speakers for new topics
    for t in agenda_items:
        i, c = next(((i, c) for i, c in enumerate(contrib_agenda) if is_speaker_in_range(t, c)), (None, None))
        if i is not None:
            c0 = copy.deepcopy(c)
            c0['speech'] = c0['speech'][:t['start_idx'] - c0['start_idx']]
            c0['end_idx'] = t['start_idx']
            c1 = copy.deepcopy(c)
            c1['speech'] = c1['speech'][t['start_idx'] - c0['start_idx']:]
            c1['start_idx'] += t['start_idx'] - c0['start_idx']
            del contrib_agenda[i]
            contrib_agenda[i:i] = [c0, t, c1]
        else:
            log.warn("couldn't find contribution for topic ({}, {})".format(t['type'], t['id']))
    return contrib_agenda


def parse_excused(text):
    # FIX: look for regex call that can return the last `match` object.
    #      .search returns the first match
    #      .findall returns just the matched strings
    for start in re.finditer(r'\nAnlage\s\d+\s*\n\s*Liste der entschuldigten Abgeordneten', text): pass
    end = re.search(r'\nAnlage\s\d+|\s*\d+\s+Deutscher Bundestag –', text[start.end():])

    text_slice = text[start.end(): end.start() + start.end()]

    excused = [m.groupdict() for m in re.finditer(Regex.absentee_reg_, text_slice)]

    excused_reasons = [m.groups() for m in re.finditer(Regex.absentee_reason_reg_, text_slice)]

    return excused, excused_reasons


# TODO: refactor
def parse_agenda_summaries(text):
    start_delimiter = r'\n(Zusatztagesordnungspunkt|Tagesordnungspunkt)\s*(\d+)*:?\n'
    end_delimiters = [
        start_delimiter,
        r'\nAnlage\s*\d*\s*\n',
        r'\n\d+\.\sSitzung\s*\n',
        r'\nAmtliche Mitteilungen\s*\n'
    ]

    agenda_summary_reg = re.compile(start_delimiter + '(.*?(?=(?:'
                                    + '|'.join(end_delimiters) + ')|$))', re.DOTALL)

    steno_reference_reg_ = re.compile(r'\n\s*\d{5}\s[ABCD]{1}\s*(?:\n|$)')

    summaries = []
    for s in re.finditer(agenda_summary_reg, text):
        agenda_summary = steno_reference_reg_.sub('\n', s.groups()[2])

        summaries.append({
            'type': s.groups()[0],
            'id': s.groups()[1],
            'summary': agenda_summary
        })
    return summaries


def parse_agenda_debate(text, summaries):
    def is_tagesordnung(s):
        return s.lower() in ['tagesordnungspunkt', 'tagesordnung']

    def is_zusatz(s):
        return s.lower() in ['zusatzpunkt', 'zusatztagesordnungspunkt', 'zp', 'zusatzpunkte']

    def is_same_type(s, t):
        return (is_tagesordnung(s) and is_tagesordnung(t)) or (is_zusatz(s) and is_zusatz(t))

    topics = copy.deepcopy(summaries)

    for r in Regex.agenda_regs_:
        agenda_discussions = r.finditer(text)
        for t, t1 in pairwise(itertools.chain(agenda_discussions, [re.search('$', text)])):
            # now we need to match the topic summaries with the debate
            # Hopefully, the summaries will contain the type of topic
            # in group 0 and the topic id in group 1.
            log.debug("processing debate item {}".format((t.groups(), t, r)))
            s = next((s for s in topics if is_same_type(s['type'], t.groups()[0]) and (s['id'] == t.groups()[1])), None)
            if not s:
                log.warn('Could not match debate item to any agenda items {}'.format(t.groups()))
            else:
                s['start_idx'] = t.end()
                s['end_idx'] = t1.start()
    for s in topics:
        if not 'start_idx' in s:
            s['start_idx'] = -1
            s['end_idx'] = -1
            log.warn(
                "No debate found for agenda item: ({}, {}). Setting 'start_idx' and 'end_idx' to default values".format(
                    s['type'], s['id']))

    return topics


def match_abgeordnetenwatch(person, aw_data):
    for p in aw_data["profiles"]:
        if p['personal']['first_name'] == person['first_name'] and p['personal']['last_name'] == person['last_name']:
            person['aw'] = {
                'image_url': p['personal']['picture']['url'],
                'uuid': p['meta']['uuid'],
            }
            break
    return person


def split_plenum(text):
    preamble, rest = re.split(Regex.start_split_reg_, text)
    debate, postamble = re.split(Regex.end_split_reg_, rest)

    return preamble, debate, postamble


def sanitise_transcript(text):
    return text.replace(u"\xa0", " ")


def parse_plenar_transcript(file):
    log.info("Parsing transcript {}".format(file))
    text = ''
    with open(file, 'r') as f:
        text = sanitise_transcript(f.read())

    metadata = parse_metadata(text)

    preamble, debate, postamble = split_plenum(text)

    agenda_summary = parse_agenda_summaries(preamble)
    agenda_items = parse_agenda_debate(debate, agenda_summary)
    contributions = parse_contributions(debate)
    contrib_agenda = inject_agenda_items(contributions, agenda_items)

    excused, excused_reasons = parse_excused(postamble)

    return metadata, agenda_summary, contrib_agenda, excused
