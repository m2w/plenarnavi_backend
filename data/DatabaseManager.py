from sqlalchemy import create_engine, ForeignKey, Column, Integer, String, Table, DateTime, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, joinedload, exc
from UUID import GUID
import uuid
import logging

ELECTORAL_PERIOD_OVERRIDE = 18
UUID_NAMESPACE = uuid.NAMESPACE_DNS

Base = declarative_base()

session_absentee_association_table = Table('session_absentee_association', Base.metadata,
                                           Column('person_uuid', GUID,
                                                  ForeignKey('persons.uuid')),
                                           Column('session_uuid', GUID,
                                                  ForeignKey('sessions.uuid'))
                                           )


class Person(Base):
    __tablename__ = 'persons'
    uuid = Column(GUID, primary_key=True)

    first_name = Column(String)
    last_name = Column(String)
    degree = Column(String)
    image_url = Column(String)
    party = Column(String)
    electoral_period = Column(Integer)

    speeches = relationship("Speech", back_populates="person")

    absent_sessions = relationship(
        "PlenumSession",
        secondary=session_absentee_association_table,
        back_populates="absentees")

    def __repr__(self):
        return "<User>(first_name='{}', last_name='{}')".format(
            self.first_name, self.last_name)


class Speech(Base):
    __tablename__ = 'speeches'
    uuid = Column(GUID, primary_key=True)

    person_uuid = Column(GUID, ForeignKey('persons.uuid'), nullable=True)
    person = relationship("Person", back_populates="speeches")

    speech_id = Column(Integer)  # TODO: constrain

    agenda_item_uuid = Column(GUID, ForeignKey(
        'agendaitems.uuid'), nullable=True)
    session_uuid = Column(GUID, ForeignKey('sessions.uuid'))

    text = Column(String)


class AgendaItem(Base):
    __tablename__ = 'agendaitems'
    uuid = Column(GUID, primary_key=True)

    summary = Column(String)
    name = Column(String)
    agenda_id = Column(Integer)  # TODO: constrain

    speeches = relationship("Speech")

    session_uuid = Column(GUID, ForeignKey('sessions.uuid'))


class PlenumSession(Base):
    __tablename__ = 'sessions'
    uuid = Column(GUID, primary_key=True)

    electoral_period = Column(Integer)
    session_number = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    agenda_items = relationship("AgendaItem")

    speeches = relationship("Speech")

    absentees = relationship(
        "Person",
        secondary=session_absentee_association_table,
        back_populates="absent_sessions")


class DatabaseManager:

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
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
                   Person.degree == json['titles'],
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
        uuid_str = metadata['session'] + metadata['start_time'].isoformat()
        session = PlenumSession(
            electoral_period=metadata['electoral_period'],
            session_number=metadata['session'],
            start_time=metadata['start_time'],
            end_time=metadata['end_time'],
            absentees=[],
            uuid=uuid.uuid3(UUID_NAMESPACE, uuid_str))

        for m in absent_mdbs:
            person = self.find_or_add_person(m)
            session.absentees.append(person)

        try:
            self.session.add(session)
        except:
            self.session.rollback()
            raise
        return session

    def add_speeches_(self, debate, session):
        speeches = []
        for i, d in enumerate(debate):
            person = self.find_or_add_person(d['speaker'])
            uuid_str = str(i) + session.start_time.isoformat()
            speeches.append(
                Speech(
                    uuid=uuid.uuid3(UUID_NAMESPACE, uuid_str),
                    text=d['speech'],
                    person_uuid=person.uuid,
                    session_uuid=session.uuid,
                    speech_id=i
                ))
        try:
            self.session.add_all(speeches)
        except:
            self.session.rollback()
            raise
        return speeches

    def add_agenda_(self, agenda_summary, session):
        agenda_items = []
        for i, a in enumerate(agenda_summary):
            if a['id']:
                a_name = a['type'] + a['id']
            else:
                a_name = a['type']
            uuid_str = a['type'] + str(i) + session.start_time.isoformat()
            agenda_items.append(
                AgendaItem(
                    session_uuid=session.uuid,
                    summary=a['summary'],
                    name=a_name,
                    agenda_id=i,
                    uuid=uuid.uuid3(UUID_NAMESPACE, uuid_str)
                ))
        try:
            self.session.add_all(agenda_items)
        except:
            self.session.rollback()
            raise
        return agenda_items

    def persist_session(self, metadata, absent_mdbs, agenda_summary, debate):
        session = self.add_metadata_(metadata, absent_mdbs)
        speeches = self.add_speeches_(debate, session)
        agenda_items = self.add_agenda_(agenda_summary, session)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return session.uuid

    def persist_aw_mdbs(self, aw_data):
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
                    electoral_period=ELECTORAL_PERIOD_OVERRIDE
                )
            )
        try:
            self.session.add_all(persons)
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def get_session_list(self, electoral_period):
        return self.session.query(PlenumSession).\
            options(joinedload('agenda_items'),
                    joinedload('absentees')).\
            filter(PlenumSession.electoral_period == electoral_period).\
            all()

    def get_session_by_uuid(self, session_uuid):
        return self.session.query(PlenumSession).\
            options(joinedload('agenda_items'),
                    joinedload('speeches'),
                    joinedload('absentees')).\
            filter(PlenumSession.uuid == session_uuid).\
            one()

    def get_session_by_number(self, electoral_period, session_number):
        return self.session.query(PlenumSession).\
            options(joinedload('agenda_items'),
                    joinedload('speeches'),
                    joinedload('absentees')).\
            filter(PlenumSession.electoral_period == electoral_period,
                   PlenumSession.session_number == session_number).\
            one()
