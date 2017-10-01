# -*- coding: utf-8 -*-
import re
import glob
import itertools
from datetime import datetime
import copy
import logging


class Regex:
    # TODO: delete once absentee_reg_ is rewritten
    parties = [
        'CDU/CSU',
        'SPD',
        'DIE LINKE',
        'BÜNDNIS\s90/DIE\sGRÜNEN',
        'fraktionslos'
    ]

    # TODO: rewrite regex to be more succinct
    absentee_reg_ = re.compile(r'^(?P<last_name>[\w-]+)(?: \((?P<electorate>\w+)\))?, ' +
                               r'(?P<titles>(?:\w{1,2}\. )+)?(?P<first_name>[\w-]+)\s*(?P<reason>\*+)*\s*\n' +
                               r'(?P<party>[\w/ ]+)\s*\n', re.MULTILINE)

    absentee_reason_reg_ = re.compile(r'^(\*+)\s*([\w ]+)')

    #speaker_reg_ = re.compile(r'\n\s*(?P<role>\w+ )?(?P<titles>(?:\w{1,2}\. )*)?(?P<first_name>[\w-]+) (?P<last_name>[\w-]+) ?(?:\((?P<party>.*)\))?(?:,(?P<position>[\w ]+))?\:\s*\n')
    speaker_reg_ = re.compile(r'\n\s*(?P<role>[\w]+ )?(?P<titles>(?:\w{1,2}\. )*)?(?P<first_name>[\w-]+) (?P<last_name>[\w-]+) ?(?:\((?P<party>.*)\))?(?:,(?P<position>[\w ]+))?\:\s*\n')
    agenda_regs_ = [
        re.compile(r'kommen? .* zum? (Tagesordnungspunkt) (\d+(?: \w)?)'),
        re.compile(r'(?:rufe|jetzt).*(Tagesordnungspunkte?) (\d+(?: \w+)?)(?: (und|bis) (\d+(?: \w+)?))? auf'),
        re.compile(r'(Tagesordnungspunkten*) ((?:(?:\d+(?: \w+)?)(?:, | sowie )(?:\d+(?: \w+)?))+)\.'),
        re.compile(r'(Tagesordnungspunkte?) (\d+(?: (?:\w|(\w)\3+)?(?=[ .:]))?).*(?:\.|:)'),
        re.compile(r'(Tagesordnungspunkte?) (\d+(?: \w+)?) sowie zum? (.*punkte?) (\d+(?: \w+)?)'),
    ]

    session_reg_ = re.compile(r'\n\s*(\d+)\.\s*Sitzung\s*\n')
    date_reg_ = re.compile(r'(\d+)\.\s*([^\s]+)\s*(\d+)')

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



def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def parse_header(text):
    session = Regex.session_reg_.findall(text)[0]
    date = Regex.date_reg_.findall(text)[0]

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
        'date': "{}.{}.{}".format(date[0], month_map[date[1]], date[2])
    }


def parse_contributions(text):
    end = re.search(r'$', text)
    
    contributions = []
    #topics_with_contrib = topics.copy()
    for m, m1 in pairwise(itertools.chain(Regex.speaker_reg_.finditer(text), [end])):
        contrib = {
            'speaker': m.groupdict(),
            'start_idx': m.start(),
            'end_idx': m1.start(),
            'speech': text[m.end():m1.start()]
        }
        contributions.append(contrib)
    return contributions


def inject_agenda_items(contributions, agenda_items):
    def is_not_in_range(t, c):
        return c['start_idx'] <= t['start_idx'] and c['end_idx'] >= t['start_idx']
    
    contrib_agenda = copy.deepcopy(contributions)

    # add dummy elements in list of speakers for new topics
    for t in agenda_items:
        i = next((i for i, c in enumerate(contrib_agenda) if is_not_in_range(t, c)), None)
        if i is not None:
            contrib_agenda.insert(i+1, t)
        else:
            print("couldn't find contribution for topic", t['type'], t['id'], t['start_idx'], t['end_idx'])
    return contrib_agenda

def parse_excused(text):
    # FIX: look for regex call that can return the last `match` object.
    #      .search returns the first match
    #      .findall returns just the matched strings
    for start in re.finditer(r'\nAnlage\s\d+\s*\n\s*Liste der entschuldigten Abgeordneten', text): pass
    end = re.search(r'\nAnlage\s\d+|\s*\d+\s+Deutscher Bundestag –', text[start.end():])
    
    # TODO: title: Phillip, first_name: Graf
    text_slice = text[start.end(): end.start()+start.end()]

    excused = [m.groupdict() for m in re.finditer(Regex.absentee_reg_, text_slice)]

    return excused


# TODO: refactor
def parse_topic_summaries(text):
    start_delimiter = r'\n(Zusatztagesordnungspunkt|Tagesordnungspunkt)\s*(\d+)*:?\n'
    end_delimiters = [
        start_delimiter,
        r'\nAnlage\s*\d*\s*\n',
        r'\n\d+\.\sSitzung\s*\n',
        r'\nAmtliche Mitteilungen\s*\n'
    ]

    re_topic_summaries = re.compile(start_delimiter + '(.*?(?=(?:' 
                        + '|'.join(end_delimiters) + ')|$))', re.DOTALL)

    topics = []
    for s in re.finditer(re_topic_summaries, text):
        #print(s.groups())
        topics.append({
            'type': s.groups()[0],
            'id': s.groups()[1],
            'summary': s.groups()[2]
        })        
    return topics

def parse_topics(text, summaries):
    def is_same_type(s, t):
        tagesordnung = ['tagesordnungspunkt', 'tagesordnung']
        zusatz = ['zusatzpunkt', 'zusatztagesordnungspunkt', 'zp', 'zusatzpunkte']
        s_type = s['type'].lower()
        t_type = t['type'].lower()
        return all(t in tagesordnung for t in [s_type, t_type]) or all(t in zusatz for t in [s_type, t_type])
    
    def is_same_id(s, t):
        return s['id'] == t['id']
    
    start_mark = re.compile('(?:wir kommen|ich komme|rufe).*(?P<type>Tagesordnung|Tagesordnungspunkt|Zusatzpunkt|Zusatzpunkte)\s*(?P<id>\d+)', re.IGNORECASE)

    topic_matches = start_mark.finditer(text)

    topics = copy.deepcopy(summaries)
    
    for t, t1 in pairwise(itertools.chain(topic_matches, [re.search('$', text)])):
        # now we need to match the topic summaries with the debate
        # Hopefully, the summaries will contain the type of topic
        # in group 0 and the topic id in group 1.
        s = next((s for s in topics if is_same_type(s, t.groupdict()) and is_same_id(s, t.groupdict())), None)
        if not s:
            print('Failed to find a match', t.groupdict()['type'], t.groupdict()['id'])
        else:
            s['start_idx'] = t.start()
            s['end_idx'] = t1.start()
    for s in topics:
        if not 'start_idx' in s:
            print("Setting 'start_idx' and 'end_idx' to default values for", s['type'], s['id'])
            s['start_idx'] = -1
            s['end_idx'] = -1
    return topics
            
    
def split_plenum(text):
    begin_delimiter = r'\nBeginn:\s*\d*[.:]\d*.*Uhr'
    end_delimiter = r'\n\(Schluss:\s*\d+[.:]\d+.*Uhr\)\.*'

    preamble, rest = re.split(begin_delimiter, text)
    debate, postamble = re.split(end_delimiter, rest)
    
    print(len(preamble), len(debate), len(postamble))
    
    return preamble, debate, postamble

def sanitise_transcript(text):
    return text.replace(u"\xa0", " ")

def parse_plenar_transcript(file):
    text = ''
    with open(file, 'r') as f: 
        text = sanitise_transcript(f.read())
    
    preamble, debate, postamble = split_plenum(text)
    
    header = parse_header(preamble)
    agenda_summary = parse_topic_summaries(preamble)
    agenda_items = parse_topics(debate, agenda_summary)
    print([(t['type'], t['id'], t['start_idx'], t['end_idx']) for t in agenda_items])     
    contributions = parse_contributions(debate)
    contrib_agenda = inject_agenda_items(contributions, agenda_items)
    
    excused = parse_excused(postamble)

    return header, agenda_summary, contrib_agenda, excused
