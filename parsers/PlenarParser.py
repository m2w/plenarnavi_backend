# -*- coding: utf-8 -*-
import re
import glob
import itertools
import datetime
import copy
import logging
from utils import pairwise
import json


class PlenarParser:
    """Parse a text transcript of a plenary debate in the German Bundestag"""

    # Protocol splitting regex
    debate_start_regex = re.compile(r'\nBeginn:\s*\d+[.:]\d+.*Uhr\s*\n')
    debate_end_regex = re.compile(r'\n\(Schluss:\s*\d+[.:]\d+.*Uhr\)\.?\s*\n')

    # Plenary Session metadata regexes
    session_regex = re.compile(r'\n\s*Plenarprotokoll\s*(\d+)/(\d+)\s*\n')
    date_regex = re.compile(
        r'\nBerlin,\s\w+,\sden\s(\d+)\.\s*([^\s]+)\s*(\d+)\s*\n')
    start_time_regex = re.compile(r'\nBeginn:\s*(\d+)[.:](\d+).*Uhr\s*\n')
    end_time_regex = re.compile(
        r'\n\(Schluss:\s*(\d+)[.:](\d+).*Uhr\)\.?\s*\n')

    # Absentee regexes
    absentee_regex = re.compile(r'^(?P<last_name>[\w-]+)(?: \((?P<electorate>\w+)\))?, ' +
                               r'(?P<titles>(?:\w{1,2}\. )+)?(?P<first_name>[\w-]+)\s*(?P<reason>\*+)*\s*\n' +
                               r'(?P<party>[\w/ ]+)\s*\n', re.MULTILINE)

    absentee_reason_regex = re.compile(r'^(\*+)\s*([\w ]+)')

    absent_mdbs_start_regex = re.compile(
        r'\nAnlage\s\d+\s*\n\s*Liste der entschuldigten Abgeordneten')
    absent_mdbs_end_regex = re.compile(
        r'\nAnlage\s\d+|\s*\d+\s+Deutscher Bundestag –')

    # Agenda item regexes
    agenda_start_regex = r'\n(Zusatztagesordnungspunkt|Tagesordnungspunkt)\s*(\d+)*:?\n'
    agenda_end_regex = [
        agenda_start_regex,
        r'\nAnlage\s*\d*\s*\n',
        r'\n\d+\.\sSitzung\s*\n',
        r'\nAmtliche Mitteilungen\s*\n'
    ]
    agenda_item_regex = re.compile(agenda_start_regex + '(.*?(?=(?:'
                                   + '|'.join(agenda_end_regex) + ')|$))', re.DOTALL)
    steno_reference_regex = re.compile(r'\n\s*\d{5}\s[ABCD]{1}\s*(?:\n|$)')
    agenda_regexs = [
        re.compile(
            r'kommen? \w{0,10} (?:zum|zu den)? ((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w)?):'),
        re.compile(
            r'(?:rufe|jetzt) \w{0,10} ((?:Zusatz|Tagesordnungs)punkt[ens]*) (\d+(?: \w+)?)(?: (und|bis) (\d+(?: \w+)?))? auf'),
    ]

    # Debate speakers
    speaker_regex = re.compile(
        r'\n\s*(?P<role>Präsident |Präsidentin |Vizepräsident |Vizepräsidentin )?(?P<titles>(?:\w{1,2}\. )*)?(?P<first_name>[\w-]+) (?P<last_name>[\w-]+) ?(?:\((?P<party>.*)\))?(?:,(?P<position>[\w ]+))?\:\s*\n')

    # Month to integer map, required for date parsing if the environment locale is not
    # set to German
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

    def __init__(self, filename):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)

        self.filename = filename
        # There are some unicode whitespaces '\xa0' peppered through the transcript
        # these cause some regexes to fail, hence they are replaced with normal
        # whitespaces.
        with open(filename, 'r') as f:
            self.protocol = f.read().replace(u"\xa0", " ")

        self.metadata = None
        self.absent_mdbs = None
        self.absent_reasons = None
        self.agenda_summaries = None
        self.debate = None

    def parse(self):
        self.parse_metadata_()
        self.parse_absent_mdbs_()
        self.parse_agenda_()
        self.parse_debate_()
        return (self.metadata, self.absent_mdbs, self.absent_reasons,
            self.agenda_summaries, self.debate)

    def parse_metadata_(self):
        def extract_time(date, time):
            date = datetime.date(int(date[2]), self.month_map[
                                 date[1]], int(date[0]))
            time = datetime.time(int(time[0]), int(time[1]))
            return datetime.datetime.combine(date, time)

        try:
            ep, session = self.session_regex.findall(self.protocol)[0]
            date = self.date_regex.findall(self.protocol)[0]
            start_time = self.start_time_regex.findall(self.protocol)[0]
            end_time = self.end_time_regex.findall(self.protocol)[0]

            self.metadata = {
                'session': session,
                'electoral_period': ep,
                'start_time': extract_time(date, start_time),
                'end_time': extract_time(date, end_time)
            }
        except:
            self.log.error(
                "Failed to parse metadata from transcript {}.".format(self.filename))
            raise

    def parse_absent_mdbs_(self):
        for start in re.finditer(self.absent_mdbs_start_regex, self.protocol):
            pass
        end = re.search(self.absent_mdbs_end_regex, self.protocol[start.end():])

        text_slice = self.protocol[start.end(): end.start() + start.end()]

        absentees = [m.groupdict()
                     for m in re.finditer(self.absentee_regex, text_slice)]
        reasons = [m.groups()
                   for m in re.finditer(self.absentee_reason_regex, text_slice)]

        self.absent_mdbs = absentees
        self.absent_reasons = reasons

    def parse_agenda_(self):
        def is_tagesordnung(s):
            return s.lower() in ['tagesordnungspunkt', 'tagesordnung']

        def is_zusatz(s):
            return s.lower() in ['zusatzpunkt', 'zusatztagesordnungspunkt', 'zp', 'zusatzpunkte']

        def is_same_type(s, t):
            return (is_tagesordnung(s) and is_tagesordnung(t)) or (is_zusatz(s) and is_zusatz(t))

        summaries = []
        for s in re.finditer(self.agenda_item_regex, self.protocol):
            agenda_summary = self.steno_reference_regex.sub('\n', s.groups()[2])

            summaries.append({
                'type': s.groups()[0],
                'id': s.groups()[1],
                'summary': agenda_summary,
                'start_idx': -1,
                'end_idx': -1
            })

        for r in self.agenda_regexs:
            agenda_discussions = r.finditer(self.protocol)
            for t, t1 in pairwise(itertools.chain(agenda_discussions, [re.search('$', self.protocol)])):
                # now we need to match the topic summaries with the debate
                # Hopefully, the summaries will contain the type of topic
                # in group 0 and the topic id in group 1.
                self.log.debug(
                    "processing debate item {}".format((t.groups(), t, r)))
                s = next((s for s in summaries if is_same_type(
                    s['type'], t.groups()[0]) and (s['id'] == t.groups()[1])), None)
                if not s:
                    self.log.warn(
                        'Could not match debate item to any agenda items {}'.format(t.groups()))
                else:
                    s['start_idx'] = t.end()
                    s['end_idx'] = t1.start()
        self.agenda_summaries = summaries

    def parse_debate_(self):
        def is_valid(s):
            tests = [
                s['first_name'][0].isupper(),
                s['last_name'][0].isupper(),
                len(s['first_name']) >= 2,
                len(s['last_name']) >= 2
            ]
            if not all(tests):
                self.log.debug("Discarting invalid contribution {}".format(s))

            return all(tests)

        contributions = self.speaker_regex.finditer(self.protocol)

        speakers = filter(lambda x: is_valid(x.groupdict()), contributions)

        debate = []
        for m, m1 in pairwise(itertools.chain(speakers, [re.search('$', self.protocol)])):
            contrib = {
                'speaker': self.strip_dict_strings(m.groupdict()),
                'start_idx': m.start(),
                'end_idx': m1.start(),
                'speech': self.protocol[m.end():m1.start()]
            }
            debate.append(contrib)
        self.debate = debate

    def strip_dict_strings(self, d):
        out = {}
        for k, v in d.items():
            if type(v) is str:
                out[k] = v.strip()
                if len(out[k]) == 0:
                    out[k] = None
            else:
                out[k] = v
        return out
