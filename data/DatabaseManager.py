from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, joinedload, exc
import uuid
import logging

from data.models import Person, Speech, AgendaItem, PlenumSession, Base

UUID_NAMESPACE = uuid.NAMESPACE_DNS


def get_session_uuid(session_start_time):
    return uuid.uuid3(UUID_NAMESPACE, session_start_time.isoformat())

def get_speech_uuid(text, i):
    return uuid.uuid3(UUID_NAMESPACE, text + str(i))

def get_agenda_item_uuid(summary, session_start_time):
    return uuid.uuid3(UUID_NAMESPACE, summary + session_start_time.isoformat())



class DatabaseManager:

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.WARN)
        fh = logging.FileHandler('DatabaseManager.log')
        self.log.addHandler(fh)
        engine = create_engine('sqlite:///{}'.format(name))
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def close(self):
        self.session.close()

    def find_person(self, json):
        q = self.session.query(Person).\
            filter(Person.first_name == json['first_name'],
                   Person.last_name == json['last_name'],
                   # Person.degree == json['titles'],
                   # Person.party==json['party']) TODO: transcript parties
                   # do not match AW parties (CDU vs CDU/CSU, etc.)
                   )
        try:
            return q.one_or_none()
        except exc.MultipleResultsFound:
            self.log.error("json: {}, query: {}".format(q, [r for r in q]))
            raise

    def add_json_person(self, json):
        p = Person(
            uuid=uuid.uuid1(),
            first_name=json['first_name'],
            last_name=json['last_name'],
            party=json['party'],
            degree=json['titles'])
        try:
            self.session.add(p)
        except:
            self.log.error("Failed to add person from JSON {}".format(json))
            raise
        return p

    def find_or_add_person(self, json):
        p = self.find_person(json)
        if not p:
            self.log.warn(
                "Failed to find candidate in Person table: {}".format(json))
            p = self.add_json_person(json)
        return p

    def add_metadata_(self, metadata, absent_mdbs):
        session = PlenumSession(
            electoral_period=metadata['electoral_period'],
            session_number=metadata['session'],
            start_time=metadata['start_time'],
            end_time=metadata['end_time'],
            absentees=[],
            uuid=get_session_uuid(metadata['start_time']))

        for m in absent_mdbs:
            person = self.find_or_add_person(m)
            session.absentees.append(person)

        try:
            self.session.add(session)
        except:
            self.session.rollback()
            raise
        return session

    def add_speeches_(self, debate, agenda_mapping, session):
        def is_agenda_item_for_speech(s, a):
            return s['end_idx'] >= a['start_idx'] and s['start_idx'] <= a['end_idx']

        speeches = []
        for i, d in enumerate(debate):
            person = self.find_or_add_person(d['speaker'])

            agenda_item_uuid = next(
                (a['uuid'] for a in agenda_mapping if is_agenda_item_for_speech(d, a)), None)

            speeches.append(
                Speech(
                    uuid=get_speech_uuid(str(session.uuid) + d['speech'], i),
                    text=d['speech'],
                    person_uuid=person.uuid,
                    session_uuid=session.uuid,
                    speech_id=i,
                    agenda_item_uuid=agenda_item_uuid
                ))
        try:
            self.session.add_all(speeches)
        except:
            self.session.rollback()
            raise
        return speeches

    def add_agenda_(self, agenda_summary, session):
        agenda_items = []
        agenda_mapping = []
        for i, a in enumerate(agenda_summary):
            if a['id']:
                a_name = a['type'] + '-' + a['id']
            else:
                a_name = a['type']
            agenda_item = AgendaItem(
                session_uuid=session.uuid,
                summary=a['summary'],
                name=a_name,
                agenda_id=i,
                uuid=get_agenda_item_uuid(a['summary'], session.start_time)
            )
            agenda_items.append(agenda_item)

            agenda_mapping.append({
                'uuid': agenda_item.uuid,
                'start_idx': a['start_idx'],
                'end_idx': a['end_idx']
            })
        try:
            self.session.add_all(agenda_items)
        except:
            self.session.rollback()
            raise
        return agenda_items, agenda_mapping

    def persist_session(self, metadata, absent_mdbs, agenda_summary, debate):
        session = self.add_metadata_(metadata, absent_mdbs)
        agenda_items, agenda_mapping = self.add_agenda_(
            agenda_summary, session)
        speeches = self.add_speeches_(debate, agenda_mapping, session)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return session.uuid

    def persist_aw_mdbs(self, aw_data, electoral_period=18):
        persons = []
        for p in aw_data['profiles']:
            personal = p['personal']
            persons.append(
                Person(
                    uuid=p['meta']['uuid'],
                    first_name=personal['first_name'],
                    last_name=personal['last_name'],
                    party=p['party'],
                    degree=personal['degree'],
                    image_url=personal['picture']['url'],
                    electoral_period=electoral_period
                )
            )
        try:
            self.session.add_all(persons)
            self.session.commit()
        except:
            self.session.rollback()
            raise