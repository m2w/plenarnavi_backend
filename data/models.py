from data.UUID import GUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import ForeignKey, Column, Integer, String, Table, DateTime

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
        return "<User>(first_name='{}', last_name='{}', uuid='{}')".format(
            self.first_name, self.last_name, self.uuid)


class Speech(Base):
    # TODO: add uuid generation to __init__()
    __tablename__ = 'speeches'
    uuid = Column(GUID, primary_key=True)

    person_uuid = Column(GUID, ForeignKey('persons.uuid'), nullable=True)
    person = relationship("Person", back_populates="speeches")

    speech_id = Column(Integer)  # TODO: constrain

    agenda_item_uuid = Column(GUID, ForeignKey(
        'agendaitems.uuid'), nullable=True)
    agenda_item = relationship("AgendaItem", back_populates='speeches')

    session_uuid = Column(GUID, ForeignKey('sessions.uuid'))

    text = Column(String)


class AgendaItem(Base):
    __tablename__ = 'agendaitems'
    uuid = Column(GUID, primary_key=True)

    summary = Column(String)
    name = Column(String)
    agenda_id = Column(Integer)  # TODO: constrain

    speeches = relationship("Speech", lazy="dynamic", order_by="Speech.speech_id")

    session_uuid = Column(GUID, ForeignKey('sessions.uuid'))


class PlenumSession(Base):
    __tablename__ = 'sessions'
    uuid = Column(GUID, primary_key=True)

    electoral_period = Column(Integer)
    session_number = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    agenda_items = relationship("AgendaItem", order_by='AgendaItem.agenda_id')

    speeches = relationship("Speech", order_by='Speech.speech_id',
        collection_class=ordering_list('speech_id'))

    absentees = relationship(
        "Person",
        secondary=session_absentee_association_table,
        back_populates="absent_sessions")
