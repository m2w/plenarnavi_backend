# -*- coding: utf-8 -*-
import unittest

from parsers.plenar_parser import Regex, sanitise_transcript

# Plenary speaker examples:
PLENARY_SPEAKER_TEST_SET = (
    ('\n  Präsident Dr. Norbert Lammert: \n',
     {'position': None, 'role': 'Präsident', 'first_name': 'Norbert', 'last_name': 'Lammert', 'titles': 'Dr.',
      'party': None}),
    ('\n  Herbert Behrens (DIE LINKE): \n',
     {'position': None, 'role': None, 'first_name': 'Herbert', 'last_name': 'Behrens', 'titles': None,
      'party': 'DIE LINKE'}),
    ('\n  Dr. Anton Hofreiter (BÜNDNIS 90/DIE GRÜNEN): \n',
     {'position': None, 'role': None, 'first_name': 'Anton', 'last_name': 'Hofreiter', 'titles': 'Dr.',
      'party': 'BÜNDNIS 90/DIE GRÜNEN'}),
    ('\n  Uwe Beckmeyer, Parl. Staatssekretär bei der Bundesministerin für Wirtschaft und Energie: \n',
     {'position': 'Parl. Staatssekretär bei der Bundesministerin für Wirtschaft und Energie', 'role': None,
      'first_name': 'Uwe', 'last_name': 'Beckmeyer', 'titles': None, 'party': None}),
    ('\n  Enak Ferlemann, Parl. Staatssekretär beim Bundesminister für Verkehr und digitale Infrastruktur: \n',
     {'position': 'Parl. Staatssekretär beim Bundesminister für Verkehr und digitale Infrastruktur', 'role': None,
      'first_name': 'Enak', 'last_name': 'Ferlemann', 'titles': None, 'party': None}),
    ('\n  Annette Sawade (SPD): \n',
     {'position': None, 'role': None, 'first_name': 'Annette', 'last_name': 'Sawade', 'titles': None, 'party': 'SPD'}),
    ('\n  Michael Donth (CDU/CSU): \n',
     {'position': None, 'role': None, 'first_name': 'Michael', 'last_name': 'Donth', 'titles': None,
      'party': 'CDU/CSU'}),
    ('\n  Vizepräsidentin Dr. h. c. Edelgard Bulmahn: \n',
     {'position': None, 'role': 'Vizepräsidentin', 'first_name': 'Edelgard', 'last_name': 'Bulmahn',
      'titles': 'Dr. h. c.', 'party': None}),
    ('\n  Heiko Maas, Bundesminister der Justiz und für Verbraucherschutz: \n',
     {'position': 'Bundesminister der Justiz und für Verbraucherschutz', 'role': None, 'first_name': 'Heiko',
      'last_name': 'Maas', 'titles': None, 'party': None}),
    ('\n  Hans-Christian Ströbele (BÜNDNIS 90/DIE GRÜNEN): \n',
     {'position': None, 'role': None, 'first_name': 'Hans-Christian', 'last_name': 'Ströbele', 'titles': None,
      'party': 'BÜNDNIS 90/DIE GRÜNEN'}),
    (
        '\n  Rita Schwarzelühr-Sutter, Parl. Staatssekretärin bei der Bundesministerin für Umwelt, Naturschutz, Bau und Reaktorsicherheit: \n',
        {
            'position': 'Parl. Staatssekretärin bei der Bundesministerin für Umwelt, Naturschutz, Bau und Reaktorsicherheit',
            'role': None, 'first_name': 'Rita', 'last_name': 'Schwarzelühr-Sutter', 'titles': None, 'party': None})
    ('\n. Harald Petzold (Havelland) (DIE LINKE): \n',
     {'position': None, 'role': None, 'first_name': 'Harald', 'last_name': 'Petzold', 'titles': None,
      'party': 'DIE LINKE'})
)


class SpeakerRegex(unittest.TestCase):
    def test(self):
        for t, e in PLENARY_SPEAKER_TEST_SET:
            t = sanitise_transcript(t)
            match = Regex.speaker_reg_.search(t)
            self.assertIsNotNone(match, (t, e))
            groups = Regex.strip_dict(match.groupdict())
            self.assertDictEqual(groups, e)


# Agenda items examples:
AGENDA_ITEMS_TEST_SET = [
    # ('  Guten Morgen, liebe Kolleginnen und Kollegen! Ich begrüße Sie alle herzlich zu unserer Plenarsitzung und rufe gleich die Zusatzpunkte 6 und 7 unserer Tagesordnung auf:',
    #    ('Zusatzpunkte', '6', 'und', '7')),
    ('  Ich rufe die Tagesordnungspunkte 28 a bis 28 c auf:',
     ('Tagesordnungspunkte', '28 a', 'bis', '28 c')),
    ('  Ich rufe die Tagesordnungspunkte 31 a und 31 b auf:',
     ('Tagesordnungspunkte', '31 a', 'und', '31 b')),
    ('  Wir kommen zum Tagesordnungspunkt 29:',
     ('Tagesordnungspunkt', '29')),
    ('  Wir kommen nun zum Tagesordnungspunkt 1',
     ('Tagesordnungspunkt', '1')),
    ('  Ich komme jetzt zum Tagesordnungspunkt 2',
     ('Tagesordnungspunkt', '2')),
    ('  Ich rufe Tagesordnungspunkt 7 auf',
     ('Tagesordnungspunkt', '7')),
    ('  Ich rufe die Tagesordnungspunkte 8 a und 8 b auf',
     ('Tagesordnungspunkte', '8 a', 'und', '8 b')),
    # ('  Ich rufe jetzt die Tagesordnungspunkte 9 a bis 9 e sowie die Zusatzpunkte 1 bis 3 auf:',
    #    ('Tagesordnungspunkte', '9 a', 'bis', '9 e', 'Zusatzpunkte', '1', '3')),
    ('  Wir kommen jetzt zum Tagesordnungspunkt 9 d',
     ('Tagesordnungspunkt', '9 d')),
    ('  Deshalb kann ich jetzt den Tagesordnungspunkt 10 aufrufen:',
     ('Tagesordnungspunkt', '10')),
    ('  Ich rufe jetzt den Tagesordnungspunkt 11 auf:',
     ('Tagesordnungspunkt', '11')),
    ('  Wir kommen zu Tagesordnungspunkt 12:',
     ('Tagesordnungspunkt', '12')),
    ('  Ich rufe die Tagesordnungspunkte 13 a und 13 b auf:',
     ('Tagesordnungspunkte', '13 a', 'und', '13 b')),
    ('  Ich rufe den Tagesordnungspunkt 14 auf:',
     ('Tagesordnungspunkt', '14')),
    ('  Tagesordnungspunkt 15 a.',
     ('Tagesordnungspunkt', '15 a')),
    ('  Ich rufe Tagesordnungspunkt 16 auf:',
     ('Tagesordnungspunkt', '16')),
    ('  Ich rufe die Tagesordnungspunkte 17 a bis 17 c auf:',
     ('Tagesordnungspunkte', '17 a', 'bis', '17 c')),
    ('  Damit kommen wir zu Tagesordnungspunkt 20:',
     ('Tagesordnungspunkt', '20')),
    ('  Wir beginnen mit den Tagesordnungspunkten 35 a, 35 b, 35 d sowie 21 b.',
     ('Tagesordnungspunkten', '35 a, 35 b, 35 d sowie 21 b')),
    ('  Tagesordnungspunkt 35 a:',
     ('Tagesordnungspunkt', '35 a')),
    # ('  Ich rufe die Tagesordnungspunkte 36 a bis dd, ff bis pp, rr bis yy, aaa und bbb, eee bis jjj, lll, ooo bis uuu und 35 c sowie Zusatzpunkte 5 a bis 5 q auf. ',
    #    ('Tagesordnungspunkte', '36 a', 'bis', 'dd', 'ff', 'bis', 'pp', 'rr', 'bis', 'yy', 'aaa', 'und', 'bbb', 'eee', 'bis', 'jjj', 'lll', 'ooo', 'bis', 'uuu', 'und', '35 c', 'Zusatzpunkte', '5 a', 'bis', '5 q')),
    # ('  Zusatzpunkt 5 a:',
    #    ('Zusatzpunkt', '5 a')),
    ('  Deshalb kann ich unmittelbar darauf den Tagesordnungspunkt 24 aufrufen:',
     ('Tagesordnungspunkt', '24')),
    # ('  Ich rufe jetzt Tagesordnungspunkt 26 sowie den Zusatzpunkt 8 auf:',
    #    ('Tagesordnungspunkt', '26', 'Zusatzpunkt', '8')),
]

AGENDA_ITEMS_NEG_TEST_SET = [
    (
        '  Frau Präsidentin! Liebe Kolleginnen und Kollegen! Liebe Zuhörerinnen und Zuhörer! Was gibt es Schöneres, als beim letzten Tagesordnungspunkt am Freitagnachmittag über Sport zu reden? ',
        ()),
    (
        'der Abgeordneten Christel Voßbeck-Kayser und Sabine Weiss (Wesel I) (beide CDU/CSU) zu der namentlichen Abstimmung über den von der Bundesregierung eingebrachten Entwurf eines Ersten Gesetzes zur Änderung des Infrastrukturabgabengesetzes (Zusatztagesordnungspunkt 6) ',
        ()),
    ('  Letzter Redner zu diesem Tagesordnungspunkt ist der Kollege Ulrich Lange.',
     ()),
    (
        '  Interfraktionell wird Überweisung der Vorlagen auf den Drucksachen 18/11145 und 18/11606 an die in der Tagesordnung aufgeführten Ausschüsse vorgeschlagen, wobei die Vorlage auf Drucksache 18/11606 zu Tagesordnungspunkt 28 b federführend im Innenausschuss beraten werden soll. Sind Sie damit einverstanden? – Das ist der Fall. Dann ist die Überweisung so beschlossen.',
        ()),
    (
        '  Tagesordnungspunkt 28 c. Da kommen wir jetzt zur Abstimmung über die Beschlussempfehlung des Ausschusses für Familie, Senioren, Frauen und Jugend zu dem Antrag der Fraktion Bündnis 90/Die Grünen mit dem Titel „Partizipation und Selbstbestimmung älterer Menschen stärken“. Der Ausschuss empfiehlt in seiner Beschlussempfehlung auf Drucksache 18/11645, den Antrag der Fraktion Bündnis 90/Die Grünen auf Drucksache 18/9797 abzulehnen. Wer stimmt für diese Beschlussempfehlung? – Wer stimmt dagegen? – Wer enthält sich? – Damit ist die Beschlussempfehlung mit den Stimmen der Koalition gegen die Stimmen der Fraktion Bündnis 90/Die Grünen bei Enthaltung der Fraktion Die Linke angenommen worden. ',
        ()),
    (
        '  Ich finde es daher schön, liebe Kolleginnen und Kollegen von den Grünen, dass Sie sich darüber Gedanken machen, wie der ÖPNV weiter verbessert werden kann. Allerdings frage ich mich, warum Sie dann Anträge ohne jegliche Verbesserungsvorschläge vorlegen. Ihr Antrag soll dem Titel nach – ich beziehe mich auf Tagesordnungspunkt 6 b – einen fairen Wettbewerb sicherstellen. Das ist aber eine Mogelpackung; denn Sie fordern genau die Maßnahmen, die einen fairen Wettbewerb abschaffen würden.',
        ()),
    (
        '  Wir kommen zur Beschlussempfehlung des Ausschusses für Gesundheit zu dem Antrag der Fraktionen Die Linke und Bündnis 90/Die Grünen mit dem Titel „Beabsichtigte und unbeabsichtigte Auswirkungen des Betäubungsmittelrechts überprüfen“. Das ist jetzt der Tagesordnungspunkt 19 b. Der Ausschuss empfiehlt in seiner Beschlussempfehlung auf Drucksache 18/10445, den Antrag der Fraktionen Die Linke und Bündnis 90/Die Grünen auf Drucksache 18/1613 abzulehnen. Wer stimmt für diese Beschlussempfehlung? – Wer stimmt dagegen? – Enthaltungen? – Die Beschlussempfehlung ist mit den Stimmen der Koalition gegen die Stimmen der Opposition angenommen.',
        ())
]


class AgendaItemsRegex(unittest.TestCase):
    def test_pos(self):
        for t, e in AGENDA_ITEMS_TEST_SET:
            t = sanitise_transcript(t)

            match = None
            for r in Regex.agenda_regs_:
                match = r.search(t)
                if match is not None:
                    break
            self.assertIsNotNone(match, t)
            sanitised_groups = Regex.strip_groups(Regex.remove_nones(match.groups()))
            self.assertTupleEqual(sanitised_groups, e, "{} {} {}".format(match.groups(), r, t))

    def test_neg(self):
        for t, _ in AGENDA_ITEMS_NEG_TEST_SET:
            t = sanitise_transcript(t)

            match = None
            for r in Regex.agenda_regs_:
                match = r.search(t)
                if match is not None:
                    break
            self.assertIsNone(match)


# parse absentee deputies
ABSENTEE_TEST_SET = [
    ("""Schmidt (Ühlingen), Gabriele
CDU/CSU
30.03.2017""",
     {'first_name': 'Gabriele', 'last_name': 'Schmidt', 'electorate': 'Ühlingen', 'party': 'CDU/CSU', 'titles': None,
      'reason': None}),
    ("""Schmidt, Dr. Frithjof
BÜNDNIS 90/DIE GRÜNEN
30.03.2017""",
     {'first_name': 'Frithjof', 'last_name': 'Schmidt', 'electorate': None, 'party': 'BÜNDNIS 90/DIE GRÜNEN',
      'titles': 'Dr.', 'reason': None}),
    ("""Rüthrich, Susann *
SPD
30.03.2017""",
     {'first_name': 'Susann', 'last_name': 'Rüthrich', 'electorate': None, 'party': 'SPD', 'titles': None,
      'reason': '*'}),
    ("""Krüger, Dr. Hans-Ulrich
SPD
30.03.2017""",
     {'first_name': 'Hans-Ulrich', 'last_name': 'Krüger', 'electorate': None, 'party': 'SPD', 'titles': 'Dr.',
      'reason': None})
]


class AbsenteeRegex(unittest.TestCase):
    def test(self):
        for t, e in ABSENTEE_TEST_SET:
            match = Regex.absentee_reg_.search(sanitise_transcript(t))
            self.assertIsNotNone(match, "\nt: {} \ne: {}".format(t, e))
            groups = Regex.strip_dict(match.groupdict())
            self.assertDictEqual(groups, e)


# parse absentee reason
ABSENTEE_REASON_TEST_SET = [
    ('*aufgrund gesetzlichen Mutterschutzes', ('*', 'aufgrund gesetzlichen Mutterschutzes'))
]


class AbsenteeReasonRegex(unittest.TestCase):
    def test(self):
        for t, e in ABSENTEE_REASON_TEST_SET:
            match = Regex.absentee_reason_reg_.search(sanitise_transcript(t))
            self.assertIsNotNone(match, "t: {} e: {}".format(t, e))
            groups = Regex.strip_groups(match.groups())
            self.assertTupleEqual(groups, e)


if __name__ == '__main__':
    unittest.main()
