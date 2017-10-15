from flask import Flask, g
from flask_restful import Resource, Api
import uuid

from api.resources import SpeechResource, SpeechListResource
from api.resources import SessionResource, SessionListResource
from api.resources import PersonResource, PersonListResource

app = Flask(__name__)
api = Api(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type,Authorization'
    )
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST')
    return response

api.add_resource(SpeechResource, '/speeches/<uuid:uuid>', endpoint='speech')
api.add_resource(SpeechListResource, '/speeches', endpoint='speeches')
api.add_resource(SessionResource, '/sessions/<uuid:uuid>', endpoint='session')
api.add_resource(SessionListResource, '/sessions', endpoint='sessions')
api.add_resource(PersonResource, '/persons/<uuid:uuid>', endpoint='person')
api.add_resource(PersonListResource, '/persons', endpoint='persons')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

if __name__ == '__main__':
    app.run(debug=True)
