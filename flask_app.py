from flask import Flask
from flask_restful import Resource, Api

from api.resources import SpeechResource
from api.resources import SpeechListResource

app = Flask(__name__)
api = Api(app)

api.add_resource(SpeechResource, '/speeches/<string:uuid>', endpoint='speech')
api.add_resource(SpeechListResource, '/speeches', endpoint='speeches')

if __name__ == '__main__':
    app.run(debug=True)