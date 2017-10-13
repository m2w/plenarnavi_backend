from data.models import Person, Speech, AgendaItem, PlenumSession
from flask_restful import Resource, abort, reqparse, marshal_with, fields
from data.DatabaseManager import DatabaseManager
from flask import g, current_app
import uuid
from data.DatabaseManager import get_session_uuid, get_speech_uuid, get_agenda_item_uuid



person_parser = reqparse.RequestParser()
person_parser.add_argument('first_name', required=True)
person_parser.add_argument('last_name', required=True)
person_parser.add_argument('degree')
person_parser.add_argument('image_url')
person_parser.add_argument('party')
person_parser.add_argument('electoral_period')
person_parser.add_argument('speeches')
person_parser.add_argument('absent_sessions')

person_fields = {
    'uuid': fields.String,
    'first_name': fields.String,
    'last_name': fields.String,
    'degree': fields.String,
    'image_url': fields.String,
    'party': fields.String,
    'electoral_period': fields.Integer,
}

speech_parser = reqparse.RequestParser()
speech_parser.add_argument('person_uuid')
speech_parser.add_argument('speech_id', required=True, type=int)
speech_parser.add_argument('agenda_item_uuid')
speech_parser.add_argument('session_uuid', required=True)
speech_parser.add_argument('text', required=True)

speech_fields = {
    'uuid': fields.String,
    'person': fields.Nested(person_fields),
    'speech_id': fields.Integer,
    'agenda_item_uuid': fields.String,
    'session_uuid': fields.String,
    'text': fields.String
}

agenda_item_fields = {
    'uuid': fields.String,
    'session_uuid': fields.String,
    'summary': fields.String,
    'name': fields.String,
    'agenda_id': fields.String,
    'speeches': fields.List(fields.Nested({'uuid': fields.String}))
}

agenda_item_summary_fields = agenda_item_fields.copy()
agenda_item_summary_fields.pop('speeches')
agenda_item_summary_fields.pop('session_uuid')

session_fields_short = {
    'uuid': fields.String,
    'electoral_period': fields.Integer,
    'session_number': fields.Integer,
    'start_time': fields.DateTime,
    'end_time': fields.DateTime,
    'agenda_items': fields.List(fields.Nested(agenda_item_summary_fields)),
}

session_fields_full = session_fields_short.copy()
session_fields_full.update({
    'agenda_items': fields.List(fields.Nested(agenda_item_fields)),
    'speeches': fields.List(fields.Nested(speech_fields)),
    'absentees': fields.List(fields.Nested(person_fields))
})


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


class SessionResource(Resource):
    @marshal_with(session_fields_full)
    def get(self, uuid):
        return find_or_abort(PlenumSession, uuid)

class SessionListResource(Resource):
    @marshal_with(session_fields_short)
    def get(self):
        db = get_db()
        return db.session.query(PlenumSession).all()


class AgendaItemResource(Resource):
    @marshal_with(agenda_item_fields)
    def get(self, uuid):
        return find_or_abort(AgendaItem, uuid)


class PersonResource(Resource):

    @marshal_with(person_fields)
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

class PersonListResource(Resource):
    @marshal_with(person_fields)
    def get(self):
        db = get_db()
        return db.session.query(Person).all()


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
        uuid = get_speech_uuid(args['text'], args['speech_id'])

        speech = Speech(uuid=uuid, **args)

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