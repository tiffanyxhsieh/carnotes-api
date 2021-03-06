import os
import jwt
import bcrypt
import datetime
from bson import  ObjectId
from functools import wraps
from pymongo import MongoClient, uri_parser
from pymongo.collection import ReturnDocument
from flask import Flask, jsonify, request, render_template


def create_app() -> Flask:
    application = Flask(__name__)
    application.config['DEBUG'] = os.environ.get('DEBUG')
    application.config['TESTING'] = os.environ.get('TESTING')
    application.config['FLASK_ENV'] = os.environ.get('FLASK_ENV')
    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    application.config['MONGO_URI'] = os.environ.get('MONGO_URI')
    return application

app = create_app()
client = MongoClient(app.config['MONGO_URI'])
db=client['carnotes']


def token_required(f):
    '''
    # Token verification decorator. This checks to see if the token passed to the endpoint is valid
    # and is applied to the endpoints that require authentication for access.
    :param f:
    :return:
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # Authorization in headers and is not blank.
        if "Authorization" in request.headers and request.headers["Authorization"]:
            token = request.headers["Authorization"]
            # Try extracting data from the token. If it fails, return an error message.
            try:
                data = jwt.decode(token, app.config["SECRET_KEY"])
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "Token is expired!"}), 401
            except:
                return jsonify({"message": "Token is invalid!"}), 401
        else:
            return jsonify({"message": "Token is missing!"}), 401

        return f(*args, **kwargs)

    return decorated


@app.route('/')
def index():
    return render_template('index.html')
    

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')
    

@app.route('/terms')
def terms():
    return render_template('terms.html')


# Endpoint for logging into the API.
@app.route('/rest/login', methods=['POST'])
def login():
    data = request.get_json()
    # Check if the username and password are in the data.
    if 'username' in data and 'password' in data:
        # Check if the username and password are not blank.
        if data['username'] and data['password']:
            # Grab the users collection from the Mongo database.
            users = db.users
            # Query the user with the username provided in the data.
            login_user = users.find_one({'username': data['username']})

            # If the user exists.
            if login_user:
                # Check the password provided with the hashed password in the database.
                if bcrypt.checkpw(data['password'].encode('utf-8'), login_user['password']):
                    # Generate a new JWT token that lasts for 24 hours.
                    token = jwt.encode({"user": data["username"], "exp": datetime.datetime.utcnow() +
                                                                         datetime.timedelta(days=30 * 12)},
                                       app.config["SECRET_KEY"])

                    return jsonify({"message": "Login succesful!", "token": token.decode('utf-8')})
                else:
                    return jsonify({"message": "Incorrect password! Please try again."}), 401
            return jsonify({"message": "User '" + data["username"] + "' does not exist!"}), 401

        else:
            return jsonify({"message": "Username or password is blank!"}), 401
    else:
        return jsonify({"message": "Username or password field is missing from request!"}), 401


#Endpoint for refreshing an existing token
@app.route('/rest/refresh', methods=['POST'])
def refresh():
    if 'Authorization' in request.headers and request.headers["Authorization"]:
        old_token = request.headers['Authorization']
        try:
            jwt.decode(old_token, app.config['SECRET_KEY'])
        except jwt.ExpiredSignatureError:
            data = request.get_json()
            token = jwt.encode({"user": data["username"], "exp": datetime.datetime.utcnow() +
                                                                 datetime.timedelta(days=30*12)},
                               app.config["SECRET_KEY"])
            return jsonify({"message": "Refresh succesful!", "token": token.decode('utf-8')})
        except jwt.InvalidSignatureError:
            return jsonify({"message": "Invalid token!"})
    else:
        return jsonify({"message": "Token is missing!"}), 401


# Endpoint for registering with the API.
@app.route('/rest/register', methods=['POST'])
def register():
    data = request.get_json()
    # Check if the username and password are in the data.
    if 'username' in data and 'password' in data:
        # Check if the username and password are not blank.
        if data['username'] and data['password']:
            # Grab the users collection from the Mongo database.
            users = db.users
            # Query the user with the username provided in the data.
            existing_user = users.find_one({'username': data['username']})

            # Check if the user with the username provided does not exist in the database.
            if existing_user is None:
                # Create a new hashed password.
                hashpass = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
                # Insert the new user into the database.
                users.insert({'username': data['username'], 'password': hashpass, 'wishlist': []})
                # Generate a JWT token to return to the user.
                token = jwt.encode({"user": data["username"], "exp": datetime.datetime.utcnow() +
                                            datetime.timedelta(days=30*6)}, app.config["SECRET_KEY"])
                return jsonify({"message": "New user '" + data["username"] + "' created!", "token": token.decode('utf-8')})

            return jsonify({"message": "User '" + data["username"] + "' already exists!"}), 401
        else:
            return jsonify({"message": "Username or password is blank!"}), 401
    else:
        return jsonify({"message": "Username or password field is missing from request!"}), 401


# Endpoint for retrieving all notes or creating a new one.
@app.route('/rest/notes', methods=['GET', 'POST'])
@token_required
def notes():
    user = str(jwt.decode(request.headers["Authorization"], app.config["SECRET_KEY"])['user'])
    if request.method == 'GET':
        notes = db.notes.find({"user": user})
        result=[]
        for note in notes:
            note['_id'] = str(note['_id'])
            result.append(note)
        return jsonify({"notes": result})
    if request.method == 'POST':
        data = request.get_json();
        #timestamp formatting
        now=datetime.datetime.now()
        dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
        #parse individual items

        #create json object to insert
        post = {
        "title": data['title'],
        "items": data['items'],
        "lastEdited": dt_string,
        "user":user}

        db.notes.insert(post)
        post['_id']=str(post['_id'])
        return post
    
    
# Endpoint for getting or deleting one note.
@app.route('/rest/notes/<note_id>', methods=['DELETE', 'GET', 'PUT'])
@token_required
def note(note_id):
    if request.method == "DELETE":
        try:
            deletedNote = db.notes.find_one_and_delete({'_id': ObjectId(note_id)})
            deletedNote['_id'] = str(deletedNote['_id'])
            return jsonify(deletedNote)
        except:
            return jsonify({"message":"id does not exist"})
        
    if request.method == "GET":
        foundNote = db.notes.find_one({'_id': ObjectId(note_id)})
        foundNote['_id'] = str(foundNote['_id'])
        return jsonify(foundNote)

    if request.method == "PUT":
        data = request.get_json();

        user = str(jwt.decode(request.headers["Authorization"], app.config["SECRET_KEY"])['user'])
        now=datetime.datetime.now()
        dt_string = now.strftime("%m/%d/%Y %H:%M:%S")

        newNote={
        "title": data['title'],
        "items":data['items'],
        "lastUpdated": dt_string,
        "user": user}
        foundNote = db.notes.find_one_and_replace({'_id': ObjectId(note_id)}, newNote,return_document=ReturnDocument.AFTER)
        if foundNote is None:
            return jsonify({"message":"id does not exist"})
        else:
            foundNote['_id'] = str(foundNote['_id'])
            return jsonify(foundNote)



