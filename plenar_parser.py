import re
import glob
import itertools
from datetime import datetime
import copy


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

parties = [
        'CDU/CSU',
        'SPD',
        'DIE LINKE',
        'BÜNDNIS\s90/DIE\sGRÜNEN',
        'fraktionslos'
    ] 

positions = [
    'Präsident',
    'Vizepräsident',
    'Präsidentin',
    'Vizepräsidentin'
]
regex_speaker = re.compile(r'\n\s+(?:(?P<position>' + '|'.join(positions) + ')\s)?' +
                           '(?:[Dd]r\.\s+)*' +
                           '(?P<first_name>[^ ]+) (?P<last_name>[^ ]+)' +
                           '(?:\s\((?P<electorate>[^ ]+)\))?' +
                           '(?:\s\((?P<party>' + '|'.join(parties) + ')\))?' + 
                           '(\s*Bundesminister.*)?:\s*\n')

def parse_header(text):
    session_regex = re.compile(r'\n\s*(\d+)\.\s*Sitzung\s*\n')
    date_regex = re.compile(r'(\d+)\.\s*([^\s]+)\s*(\d+)')

    session = session_regex.findall(text)[0]
    date = date_regex.findall(text)[0]

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

def parse_speakers(text, topics):
    def is_not_in_topic(t, c):
        return c['start_idx'] <= t['start_idx'] and c['end_idx'] >= t['start_idx']
    
    regex_delimiter = re.compile(r'$')
    
    end = regex_delimiter.search(text)
    
    contributions = []
    #topics_with_contrib = topics.copy()
    for m, m1 in pairwise(itertools.chain(regex_speaker.finditer(text), [end])):
        contrib = {
            'speaker': m.groupdict(),
            'start_idx': m.start(),
            'end_idx': m1.start(),
            'speech': text[m.end():m1.start()]
        }
        contributions.append(contrib)
        
    # add dummy elements in list of speakers for new topics
    for t in topics:
        i = next((i for i, c in enumerate(contributions) if is_not_in_topic(t, c)), None)
        if i is not None:
            contributions.insert(i+1, t)
        else:
            print("couldn't find contribution for topic", t['type'], t['id'], t['start_idx'], t['end_idx'])
    return contributions

def parse_excused(text):
    # FIX: look for regex call that can return the last `match` object.
    #      .search returns the first match
    #      .findall returns just the matched strings
    for start in re.finditer(r'\nAnlage\s\d+\s*\n\s*Liste der entschuldigten Abgeordneten', text): pass
    end = re.search(r'\nAnlage\s\d+|\s*\d+\s+Deutscher Bundestag –', text[start.end():])
    
    # TODO: title: Phillip, first_name: Graf
    regex_excused = re.compile('^(?P<last_name>[^,\s]+) ?'+
                               '(?:\((?P<electorate>[^,\s]+)\))?,' +
                               '(?P<title> ?[\w. ]+)* ' +
                               '(?P<first_name>[^\s]+(?: [^\s]+\.)*)\s*\n' +
                               '(?P<party>' + '|'.join(parties) + ')\s*\n', re.MULTILINE)
    
    text_slice = text[start.end(): end.start()+start.end()]

    excused = []
    for m in re.finditer(regex_excused, text_slice):
        excused.append(m.groupdict())

    return excused


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

def parse_plenar_transcript(file):
    text = ''
    with open(file, 'r') as f: 
        text = f.read().replace(u"\xa0", " ")
    
    preamble, debate, postamble = split_plenum(text)
    
    header = parse_header(preamble)
    topic_summaries = parse_topic_summaries(preamble)
    topics = parse_topics(debate, topic_summaries)
    print([(t['type'], t['id'], t['start_idx'], t['end_idx']) for t in topics])     
    contributions = parse_speakers(debate, topics)
    
    excused = parse_excused(postamble)

    return header, topic_summaries, contributions, excused
