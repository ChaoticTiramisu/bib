from flask import Flask, render_template, redirect,url_for,request,flash,session 
from flask_sqlalchemy import SQLAlchemy
import os
from database import Bibliothecaris,Ontlener,Boeken

dirname = os.path.dirname(__file__)
app = Flask(__name__, instance_path=dirname)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/sportweb.db"
app.secret_key = "Arno_augu"
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()



app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/boeken")
def boeken():
    return render_template("boeken.html")

@app.route("/button")
def button():
    return render_template("button_test.html")

@app.route("/button/post", methods = ['POST'])
def post():
    bibliothecaris(request.form['bib_id'],request.form['voornaam'],request.form['achternaam'],request.form['email'],request.form['bib_recht'],request.form['tel_nr_bib'])
    flash("Je bent geregistreerd!")
    return(url_for(index))






if __name__ == "__main__":
    app.run(debug=True)

