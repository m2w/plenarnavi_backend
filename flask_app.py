from flask import Flask, g
from flask_restful import Resource, Api
import uuid

from api.resources import SpeechResource, SpeechListResource
from api.resources import SessionResource, SessionListResource

app = Flask(__name__)
api = Api(app)

api.add_resource(SpeechResource, '/speeches/<uuid:uuid>', endpoint='speech')
api.add_resource(SpeechListResource, '/speeches', endpoint='speeches')
api.add_resource(SessionResource, '/sessions/<uuid:uuid>', endpoint='session')
api.add_resource(SessionListResource, '/sessions', endpoint='sessions')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

if __name__ == '__main__':
    app.run(debug=True)