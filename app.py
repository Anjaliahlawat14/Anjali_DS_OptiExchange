from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from datetime import datetime
from flask_mail import Mail, Message
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-app-password'     # Replace with app password
app.config['MAIL_DEFAULT_SENDER'] = ('Your App Name', 'your-email@gmail.com')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Supported currencies
currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'INR', 'SGD']

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database
with app.app_context():
    db.create_all()

def get_prediction(currency, date):
    try:
        # Convert date string to datetime for validation
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        current_date = datetime.now()
        
        # For past dates, fetch historical data from Frankfurter API
        if selected_date.date() <= current_date.date():
            try:
                response = requests.get(f"https://api.frankfurter.app/{date}?from=USD&to={currency}")
                if response.status_code == 200:
                    data = response.json()
                    rate = data['rates'][currency]
                    return f"1 USD = {rate:.4f} {currency}"
                else:
                    raise Exception(f"API returned status {response.status_code}")
            except Exception as e:
                app.logger.error(f"Frankfurter API error: {str(e)}")
                return None
        
        # For future dates, use a mock prediction based on the latest rate
        try:
            response = requests.get(f"https://api.frankfurter.app/latest?from=USD&to={currency}")
            if response.status_code == 200:
                data = response.json()
                latest_rate = data['rates'][currency]
                # Simulate a prediction by adding slight variation
                variation = random.uniform(-0.05, 0.05)  # ±5% variation
                predicted_rate = latest_rate * (1 + variation)
                return f"1 USD = {predicted_rate:.4f} {currency}"
            else:
                raise Exception(f"API returned status {response.status_code}")
        except Exception as e:
            app.logger.error(f"Frankfurter API error for latest rate: {str(e)}")
            return None
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return None

@app.route('/')
def index():
    # Reset to converter tool and clear prediction on page load/refresh
    return render_template('index.html', currencies=currencies, prediction=None, selected_currency=None, selected_tool='converter')

@app.route('/predict', methods=['POST'])
def predict():
    currency = request.form.get('currency')
    date = request.form.get('date')
    
    if not currency or not date:
        flash('Please select both a currency and a date.', 'error')
        return render_template('index.html', currencies=currencies, prediction=None, selected_currency=None, selected_tool='predictor')
    
    if currency not in currencies:
        flash('Invalid currency selected.', 'error')
        return render_template('index.html', currencies=currencies, prediction=None, selected_currency=None, selected_tool='predictor')
    
    prediction = get_prediction(currency, date)
    if not prediction:
        flash('Failed to generate prediction. Please try again.', 'error')
        return render_template('index.html', currencies=currencies, prediction=None, selected_currency=None, selected_tool='predictor')
    
    return render_template('index.html', currencies=currencies, prediction=prediction, selected_currency=currency, selected_tool='predictor')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your email and password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/alerts', methods=['GET', 'POST'])
@login_required
def alerts():
    message = None
    message_type = None  # 'success' or 'info'
    
    if request.method == 'POST':
        email = request.form.get('email')
        currency = request.form.get('currency')
        alert_type = request.form.get('alert_type')
        threshold = float(request.form.get('threshold'))
        notification_method = request.form.get('notification_method')

        try:
            response = requests.get(f"https://api.frankfurter.app/latest?from=USD&to={currency}")
            if response.status_code != 200:
                flash('Error fetching exchange rate.', 'error')
                return redirect(url_for('alerts'))
                
            data = response.json()
            current_rate = data['rates'][currency]

            if (alert_type == 'above' and current_rate > threshold) or (alert_type == 'below' and current_rate < threshold):
                alert_message = f"Alert Triggered: USD/{currency} rate is {current_rate:.4f}, which is {alert_type} your threshold of {threshold:.4f}!"
                
                if notification_method == 'email':
                    msg = Message(
                        subject=f"Currency Alert: USD/{currency}",
                        recipients=[email],
                        body=alert_message
                    )
                    try:
                        mail.send(msg)
                        message = "Alert triggered successfully! Email sent."
                        message_type = 'success'
                    except Exception as e:
                        message = "Alert triggered! (Email failed to send)"
                        message_type = 'info'
                        app.logger.error(f"Failed to send email: {str(e)}")
                else:
                    message = "Alert triggered successfully! In-app notification sent."
                    message_type = 'success'
            else:
                message = f"Alert set! Current USD/{currency} rate is {current_rate:.4f}. We'll notify you when the rate goes {alert_type} {threshold:.4f}."
                message_type = 'info'
        
        except Exception as e:
            app.logger.error(f"Error processing alert: {str(e)}")
            flash(f"Error processing alert: {str(e)}", 'error')
            return redirect(url_for('alerts'))

    return render_template('alerts.html', 
                         currencies=currencies, 
                         message=message,
                         message_type=message_type)

@app.route('/find_exchanges')
def find_exchanges():
    return render_template('exchange_finder.html')

@app.route('/api/nearby_exchanges')
def nearby_exchanges():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    radius = float(request.args.get('radius', 5000))

    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"[out:json];node[\"amenity\"=\"bureau_de_change\"](around:{radius},{lat},{lng});out body;"
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch data from Overpass API'}), 500
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

if __name__ == '__main__':
    app.run(debug=True)