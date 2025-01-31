# -*- coding: iso-8859-15 -*-
# Creado por: Sergio Vaquero

import json
from flask import Flask, request, render_template, session, redirect, url_for
import os.path
from os import listdir
import json
from time import time
import sys

app = Flask(__name__)

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))

# este codigo controla los errores de campos ausentes
def process_missingFields(campos, next_page):
    """
    :param campos: Lista de Campos que faltan
    :param next_page: ruta al pulsar botón continuar
    :return: plantilla generada
    """
    return render_template("missingFields.html", inputs=campos, next=next_page)


@app.route('/', methods=['GET'])
def index():

    if 'user_name' in session:
        return render_template("index.html", logged=True, nickname=session['user_name'])
    else:
        return render_template("index.html", logged=False, nickname='')
    


@app.route('/home', methods=['GET'])
def home():
    if 'user_name' not in session:
        return process_error("you must be logged to use the app / debe registrarse antes de usar la aplicacion",
                             url_for("login"))
    if request.method == 'POST' and request.form['message'] != "":
        messages = session['messages']
        if not messages:
            messages = []
        messages.append((time(), request.form['message']))
        save_current_user()
    else:  # The http GET method was used
        messages = session['messages']
    session['messages'] = messages
    return render_template('home.html', logged=True, nickname=session['user_name'],  messages = messages, 
            friends_messages=sorted(get_friends_messages_with_authors(), key=lambda x: x[1]))
    


@app.route('/login', methods=['GET'])
def login():
    return app.send_static_file('login.html')
    


@app.route('/signup', methods=['GET'])
def signup():
    return app.send_static_file('signup.html')
   

@app.route('/processLogin', methods=['GET', 'POST'])
def processLogin():
    if request.method == 'POST':   
       missing = []
       fields = ['email', 'passwd', 'login_submit']
       for field in fields:
              value = request.form.get(field, None)
              if value is None or value == '':
                  missing.append(field)
       if missing:
              return process_missingFields(missing, inputs=missing, next=url_for("login"))

       return load_user(request.form['email'], request.form['passwd'])

    return app.send_static_file('login.html')

        
      
@app.route('/processSignup', methods=['GET', 'POST'])
def processSignup():
    if request.method == 'POST':
       missing = []
       fields = ['nickname', 'email', 'passwd','confirm', 'signup_submit']
       for field in fields:
              value = request.form.get(field, None)
              if value is None or value == '':
                     missing.append(field)
       if missing:
              return process_missingFields(missing, inputs=missing, next=url_for("signup"))
       
       return create_user_file(request.form['nickname'], request.form['email'], request.form['passwd'],
                            request.form['confirm'])

    return app.send_static_file('signup.html')
     


@app.route('/processHome', methods=['GET', 'POST'])
def processHome():
    
    if 'user_name' not in session:
        return process_error("you must be logged to use the app / debe registrarse antes de usar la aplicacion",
                             url_for("login"))
    if request.method == 'POST' and request.form['message'] != "":
        messages = session['messages']
        if not messages:
            messages = []
        messages.append((time(), request.form['message']))
        save_current_user()
    else:  # The http GET method was used
        messages = session['messages']
    session['messages'] = messages
    return render_template('home.html', logged=True, nickname=session['user_name'], messages=messages, 
            friends_messages=sorted(get_friends_messages_with_authors(), key=lambda x: x[1]))

@app.route('/logout', methods=['GET', 'POST'])
def process_logout():
    """
    '/logout' url (salir de la sesión)
    :return: pagina inicial
    """
    save_current_user()
    session.pop('user_name', None)
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """
    Procesa '/profile' url (smuestra datos del usuario)
    :return: Si el usuario está logueado edita su perfil
    """
    if 'user_name' not in session:
        return process_error("you must be logged to use the app / debe registrarse antes de usar la aplicacion",
                             url_for("login"))
    if request.method == 'POST':
        session['user_name'] = request.form['nickname']
        session['password'] = request.form['passwd']
        session['friends'] = [str.strip(str(friend)) for friend in request.form.getlist('friends')]
        return redirect(url_for("home"))
    else:  # The http GET method was used
        return render_template("edit_profile.html", nickname=session['user_name'], email=session['email'],
                               passwd=session['password'], friends=session['friends'],
                               all_users=get_all_users(session['email']))
def process_error(message, next_page):
    """

    :param message:
    :param next_page:
    :return:
    """
    return render_template("error.html", error_message=message, next=next_page)


def load_user(email, passwd):
    """
    Carga datos usuario (identified by email) del directorio data.
    Busca un archivo de nombre el email del usuario
    :param email: user id
    :param passwd: password 
    :return: pagina home si existe el usuario y es correcto el pass
    """
    file_path = os.path.join(SITE_ROOT, "data/", email)
    if not os.path.isfile(file_path):
        return process_error("User not found / No existe un usuario con ese nombre", url_for("login"))
    with open(file_path, 'r') as f:
        data = json.load(f)
    if data['password'] != passwd:
        return process_error("Incorrect password / la clave no es correcta", url_for("login"))
    session['user_name'] = data['user_name']
    session['messages'] = data['messages']
    session['password'] = passwd
    session['email'] = email
    session['friends'] = data['friends']
    return redirect(url_for("home"))
    
def save_current_user():
    datos = {
        "user_name": session["user_name"],
        "password": session['password'],
        "messages": session['messages'], # lista de tuplas (time_stamp, mensaje)
        "email": session['email'],
        "friends": session['friends']
    }
    file_path = os.path.join(SITE_ROOT, "data/", session['email'])
    with open(file_path, 'w') as f:
        json.dump(datos, f)


def create_user_file(name, email, passwd, passwd_confirmation):
    """
    Crea el fichero (en directorio /data). El nombre será el email.
    Si el fichero ya existe, error.
    Si no coincide el pass con la confirmación, error.
    :param name: Nombre o apodo del usuario
    :param email: correo
    :param passwd: password 
    :param passwd_confirmation: debe coincidir con pass
    :return: Si no hay errores, dirección al usuario a home.
    """

    directory = os.path.join(SITE_ROOT, "data")
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(SITE_ROOT, "data/", email)
    if os.path.isfile(file_path):
        return process_error("The email is already used, you must select a different email / Ya existe un usuario con ese nombre", url_for("signup"))
    if passwd != passwd_confirmation:
        return process_error("Your password and confirmation password do not match / Las claves no coinciden", url_for("signup"))
    datos = {
        "user_name": name,
        "password": passwd,
        "messages": [],
        "friends": []
    }
    with open(file_path, 'w') as f:
        json.dump(datos, f)
    session['user_name'] = name
    session['password'] = passwd
    session['messages'] = []
    session['friends'] = []
    session['email'] = email
    return redirect(url_for("home"))
    
def get_friends_messages_with_authors():
    """
    Obtiene los mensajes de los amigos  (del usuario de la sesión)
    :return: Lista de mensajes, formato (usuario, marca tiempo, mensaje)
    """
    message_and_authors = []
    for friend in session['friends']:
        texts = load_messages_from_user(friend)
        message_and_authors.extend(texts)
    return message_and_authors


def load_messages_from_user(user):
    """
    Obtiene todos los mensajes de un usuario
    :param user: el usuario
    :return: todos los mensajes publicados, formato (usuario, marca tiempo, mensaje)
    """
    file_path = os.path.join(SITE_ROOT, "data/", user)
    if not os.path.isfile(file_path):
        return []
    with open(file_path, 'r') as f:
        data = json.load(f)
    messages_with_author = [(data["user_name"], message[0], message[1]) for message in data["messages"]]
    return messages_with_author


def get_all_users(user):
    """
    Obtienes los amigos de un usuario (parameter)
    :param user: usuario actual
    :return: Lista de usuarios amigos del usuario actual
    """
    dir_path = os.path.join(SITE_ROOT, "data/")
    user_list = listdir(dir_path)
    user_list.remove(user)
    return user_list

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True, port=55555)