from data.models import Person, Speech, AgendaItem, PlenumSession
from flask_restful import Resource, abort, reqparse, marshal_with, fields
from data.DatabaseManager import DatabaseManager
from flask import g, current_app

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = DatabaseManager('./data.db')
    return g.db

def find_or_abort(model, uuid):
    db = get_db()
    try:
        return db.session.query(model).filter(model.uuid==uuid).one()
    except Exception as e:
        print(e)
        abort(404, message="{} '{}' doesn't exist".format(model.__name__, uuid))


#person_uuid = Column(GUID, ForeignKey('persons.uuid'), nullable=True)
#person = relationship("Person", back_populates="speeches")
# speech_id = Column(Integer)  # TODO: constrain
# agenda_item_uuid = Column(GUID, ForeignKey(
#    'agendaitems.uuid'), nullable=True)
#agenda_item = relationship("AgendaItem", back_populates='speeches')
#session_uuid = Column(GUID, ForeignKey('sessions.uuid'))
#text = Column(String)

speech_parser = reqparse.RequestParser()
speech_parser.add_argument('uuid', required=True)
speech_parser.add_argument('person_uuid')
speech_parser.add_argument('speech_id', required=True, type=int)
speech_parser.add_argument('agenda_item_uuid')
speech_parser.add_argument('session_uuid', required=True)
speech_parser.add_argument('text', required=True)

speech_fields = {
    'person_uuid': fields.String,
    'speech_id': fields.Integer,
    'agenda_item_uuid': fields.String,
    'session_uuid': fields.String,
    'text': fields.String
}

# first_name = Column(String)
# last_name = Column(String)
# degree = Column(String)
# image_url = Column(String)
# party = Column(String)
# electoral_period = Column(Integer)
# speeches = relationship("Speech", back_populates="person")
# absent_sessions

person_parser = reqparse.RequestParser()
person_parser.add_argument('first_name')
person_parser.add_argument('last_name')
person_parser.add_argument('degree')
person_parser.add_argument('image_url')
person_parser.add_argument('party')
person_parser.add_argument('electoral_period')
person_parser.add_argument('speeches')
person_parser.add_argument('absent_sessions')


class PersonResource(Resource):

    def get(self, uuid):
        return find_or_abort(Person, uuid)

    def put(self, uuid):
        args = person_parser.parse_args()
        p = Person(**args)
        try:
            db = get_db()
            db.session.merge(p)
            db.session.commit()
        except:
            abort(500, message="Could not merge Person '{}'".format(uuid))
        return p, 201

    def delete(self, uuid):
        p = find_or_abort(Person, uuid)
        db = get_db()
        db.session.delete(p)
        db.session.commit()
        return {}, 204


class SpeechResource(Resource):
    @marshal_with(speech_fields)
    def get(self, uuid):
        return find_or_abort(Speech, uuid)

    @marshal_with(speech_fields)
    def put(self, uuid):
        args = speech_parser.parse_args()
        # TODO: currently overwrites non-null fields with nulls if the post data 
        #       doesn't contain those same fields. Not sure if this is what we want.
        #       If not: query database for speech with uuid, merge fields manually
        s = Speech(uuid=uuid, **args) 
        try:
            db = get_db()
            db.session.merge(s)
            db.session.commit()
        except Exception as e:
            print(e)
            abort(500, message="Could not merge Speech '{}'".format(uuid))
        return s, 201

    def delete(self, uuid):
        s = find_or_abort(Speech, uuid)
        db = get_db()
        db.session.delete(s)
        db.session.commit()
        return {}, 204


class SpeechListResource(Resource):
    @marshal_with(speech_fields)
    def post(self):
        args = speech_parser.parse_args()
        speech = Speech(**args)

        try:
            db = get_db()
            ps = db.session.query(PlenumSession).filter(PlenumSession.uuid==speech.session_uuid).one()
            ps.speeches.insert(speech.speech_id, speech)
            db.session.merge(ps)
            db.session.add(speech) # TODO: do i need this?
            db.session.commit()
        except Exception as e:
            abort(500, message="Could not add Speech")
            print(e)
        return speech, 201