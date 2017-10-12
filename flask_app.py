from flask import Flask, g
from flask_restful import Resource, Api

from api.resources import SpeechResource
from api.resources import SpeechListResource

app = Flask(__name__)
api = Api(app)

api.add_resource(SpeechResource, '/speeches/<string:uuid>', endpoint='speech')
api.add_resource(SpeechListResource, '/speeches', endpoint='speeches')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

if __name__ == '__main__':
    app.run(debug=True)