import os
import jwt
import bcrypt
import datetime
import json
from urllib.parse import quote_plus
from bson import json_util, ObjectId
from functools import wraps
from flask_pymongo import PyMongo
from pymongo import MongoClient, uri_parser
from flask import Flask, jsonify, request, render_template

def create_app() -> Flask:
    '''
    # Configures application and returns it.
    :return:
    '''
    app = Flask(__name__)
    app.config.from_pyfile('config.py')

    # application.config['DEBUG'] = "DEBUG"
    # application.config['TESTING'] = "TESTING"
    # application.config['FLASK_ENV'] = "FLASK_ENV"
    # application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

    return app

app = create_app()

# mongo_username = quote_plus(app.config.get('MONGO_USERNAME'))
# mongo_password = quote_plus((app.config.get('MONGO_PASSWORD')))
# mongo_cluster = app.config.get('MONGO_CLUSTER')

# mongo_uri = "PUT ATLAS URL HERE"
client = MongoClient(os.environ.get('MONGO_URI'))

# mongo = PyMongo(app)
db=client['carnotes']

@app.route('/')
def hello_world():
    return 'test'

# Endpoint for retrieving all notes
@app.route('/notes', methods=['GET'])
def getNotes():
    notes = db.notes.find()
    result=[]

    for note in notes:
        note['_id'] = str(note['_id'])
        result.append(note)
    return jsonify({"notes": result})

# #Endpoint for creating a new note
@app.route('/notes', methods=['POST'])
def createNote():
    post={"title": request.headers['noteTitle'],
    "note":request.headers['noteBody']}
    db.notes.insert(post)
    print(post)
    return json.dumps(post, indent=4, default=json_util.default)
    
#Endpoint for deleting one note
@app.route('/notes/<note_id>', methods=['DELETE'])
def deleteNote(note_id):
    return jsonify(db.notes.delete_one(note_id))
#Endpoint for getting one note
@app.route('/notes/<note_id>', methods=['GET'])
def getNote(note_id):
    return jsonify(db.notes.find_one({"_id": ObjectId(str(note_id))}))


