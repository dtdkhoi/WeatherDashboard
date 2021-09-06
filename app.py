from os import name
import requests
import string
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm, form
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))
    cities = db.relationship('City', backref='user')


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')


class RegisterForm(FlaskForm):
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])


def get_weather_data(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}" \
          f"&units=metric&appid=2e73ddcb4995cfe07cba7b05518f4738"
    r = requests.get(url).json()
    return r


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('dashboard_get'))
        return redirect(url_for('index'))
    return render_template('index.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('signup.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard_get():
    cities = City.query.filter_by(user_id=current_user.id).all()
    weather_data = []
    for city in cities:
        r = get_weather_data(city.name)
        weather = {
            'city': city.name,
            'temperature': r['main']['temp'],
            'description': r['weather'][0]['description'],
            'icon': r['weather'][0]['icon'],
        }
        weather_data.append(weather)
        print(weather_data)

    return render_template('dashboard.html', name=current_user.username,
                           weather_data=weather_data)


@app.route('/dashboard', methods=["POST"])
def dashboard_post():
    err_msg = ''
    new_city = request.form.get('city')
    new_city = new_city.lower()
    new_city = string.capwords(new_city)
    if new_city:
        existing_city = City.query.filter_by(name=new_city, user=current_user).first()
        if not existing_city:
            new_city_data = get_weather_data(new_city)
            if new_city_data['cod'] == 200:
                new_city_obj = City(name=new_city, user=current_user)
                db.session.add(new_city_obj)
                db.session.commit()
            else:
                err_msg = 'That is not a valid city!'
        else:
            err_msg = 'City already exists in the database!'
    if err_msg:
        flash(err_msg, 'error')
    else:
        flash('City added successfully!', 'success')
    
    return redirect(url_for('dashboard_get'))


@app.route('/delete/<name>')
def delete_city(name):
    city = City.query.filter_by(name=name, user=current_user).first()
    db.session.delete(city)
    db.session.commit()
    flash(f'Successfully deleted {city.name}!', 'success')
    return redirect(url_for('dashboard_get'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)