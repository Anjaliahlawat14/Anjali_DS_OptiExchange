from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from datetime import datetime
from flask_mail import Mail, Message
import random
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail configuration (optional)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = ('OptiExchange', os.environ.get('MAIL_USERNAME', 'your-email@gmail.com'))

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

# ============ FIX 1: Currency Converter API with Validation ============
@app.route('/api/convert')
def convert_currency():
    """Convert currency using Frankfurter API (server-side proxy to avoid CORS)"""
    try:
        from_curr = request.args.get('from', '').upper().strip()
        to_curr = request.args.get('to', '').upper().strip()
        amount = request.args.get('amount', type=float)
        
        # Validation
        if amount is None or amount <= 0:
            return jsonify({'error': 'Please enter a valid positive amount'}), 400
        
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY', 'INR', 'SGD']
        
        if from_curr not in valid_currencies:
            return jsonify({'error': f'Invalid source currency: {from_curr}. Please use valid ISO code like USD, EUR, GBP'}), 400
        
        if to_curr not in valid_currencies:
            return jsonify({'error': f'Invalid target currency: {to_curr}. Please use valid ISO code like USD, EUR, GBP'}), 400
        
        # Call Frankfurter API
        response = requests.get(
            f'https://api.frankfurter.app/latest',
            params={'from': from_curr, 'to': to_curr, 'amount': amount},
            timeout=10,
            headers={'User-Agent': 'OptiExchange/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            converted = data['rates'][to_curr]
            rate = converted / amount
            
            return jsonify({
                'success': True,
                'converted_amount': round(converted, 2),
                'rate': round(rate, 4),
                'from_currency': from_curr,
                'to_currency': to_curr,
                'amount': amount
            })
        else:
            return jsonify({'error': 'Exchange rate service temporarily unavailable. Please try again.'}), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except Exception as e:
        app.logger.error(f"Conversion error: {str(e)}")
        return jsonify({'error': f'Conversion error: {str(e)}'}), 500

# ============ FIX 2: Trends API with Server-Side Proxy ============
@app.route('/api/trends')
def get_trends():
    """Get historical exchange rate trends for a specific year"""
    try:
        from_curr = request.args.get('from', '').upper().strip()
        to_curr = request.args.get('to', '').upper().strip()
        year = request.args.get('year', '')
        
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY', 'INR', 'SGD']
        
        if from_curr not in valid_currencies:
            return jsonify({'error': f'Invalid source currency: {from_curr}'}), 400
        
        if to_curr not in valid_currencies:
            return jsonify({'error': f'Invalid target currency: {to_curr}'}), 400
        
        if not year or not year.isdigit() or int(year) < 1999 or int(year) > 2025:
            return jsonify({'error': 'Please select a valid year between 1999 and 2025'}), 400
        
        # Fetch data for the entire year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        response = requests.get(
            f"https://api.frankfurter.app/{start_date}..{end_date}",
            params={'from': from_curr, 'to': to_curr},
            timeout=30,
            headers={'User-Agent': 'OptiExchange/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'rates' not in data or not data['rates']:
                return jsonify({'error': f'No exchange rate data available for {year}'}), 404
            
            # Format data for chart
            dates = []
            rates = []
            for date, rate_data in sorted(data['rates'].items()):
                dates.append(date)
                rates.append(rate_data[to_curr])
            
            # Sample data if too many points (more than 100)
            if len(dates) > 100:
                step = len(dates) // 100
                dates = dates[::step]
                rates = rates[::step]
            
            return jsonify({
                'success': True,
                'dates': dates,
                'rates': rates,
                'from_currency': from_curr,
                'to_currency': to_curr,
                'year': year
            })
        else:
            return jsonify({'error': 'Unable to fetch trend data. Please try again later.'}), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except Exception as e:
        app.logger.error(f"Trends error: {str(e)}")
        return jsonify({'error': f'Error fetching trends: {str(e)}'}), 500

# ============ FIX 3: Exchange Finder API with Fallback ============
@app.route('/api/exchanges', methods=['GET', 'POST'])
def find_exchanges():
    """Find currency exchange locations near a given location"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            lat = data.get('lat')
            lon = data.get('lon')
            radius = data.get('radius', 2000)
        else:
            lat = request.args.get('lat')
            lon = request.args.get('lon')
            radius = request.args.get('radius', 2000)
        
        if not lat or not lon:
            return jsonify({'error': 'Location coordinates required'}), 400
        
        # Convert to float
        lat = float(lat)
        lon = float(lon)
        radius = float(radius)
        
        # Overpass API query to find currency exchange services
        # Using multiple tags to find exchange locations
        overpass_query = f"""
        [out:json];
        (
          node["amenity"="currency_exchange"](around:{radius},{lat},{lon});
          way["amenity"="currency_exchange"](around:{radius},{lat},{lon});
          node["shop"="currency_exchange"](around:{radius},{lat},{lon});
          way["shop"="currency_exchange"](around:{radius},{lat},{lon});
          node["amenity"="bureau_de_change"](around:{radius},{lat},{lon});
          way["amenity"="bureau_de_change"](around:{radius},{lat},{lon});
        );
        out body;
        """
        
        response = requests.post(
            'https://overpass-api.de/api/interpreter',
            data={'data': overpass_query},
            headers={'User-Agent': 'OptiExchange/1.0'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            exchanges = []
            
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                
                # Get the best available name
                name = tags.get('name', '')
                if not name:
                    name = tags.get('brand', '')
                if not name:
                    name = tags.get('operator', '')
                if not name:
                    name = 'Currency Exchange'
                
                # Get address components
                address = tags.get('addr:full', '')
                if not address:
                    address = tags.get('addr:street', '')
                if not address:
                    address = f"Near {lat:.4f}, {lon:.4f}"
                
                exchange = {
                    'name': name,
                    'lat': element.get('lat', element.get('center', {}).get('lat', lat)),
                    'lon': element.get('lon', element.get('center', {}).get('lon', lon)),
                    'address': address,
                    'opening_hours': tags.get('opening_hours', 'Hours not specified'),
                    'phone': tags.get('phone', tags.get('contact:phone', 'Not available'))
                }
                exchanges.append(exchange)
            
            # Remove duplicates (by coordinates)
            seen = set()
            unique_exchanges = []
            for ex in exchanges:
                key = (round(ex['lat'], 4), round(ex['lon'], 4))
                if key not in seen:
                    seen.add(key)
                    unique_exchanges.append(ex)
            
            # If no exchanges found, provide fallback data
            if not unique_exchanges:
                unique_exchanges = get_fallback_exchanges(lat, lon)
                return jsonify({
                    'success': True,
                    'exchanges': unique_exchanges,
                    'count': len(unique_exchanges),
                    'note': 'Using sample data (no exchange providers found in this area)'
                })
            
            return jsonify({
                'success': True,
                'exchanges': unique_exchanges[:10],  # Limit to 10 results
                'count': len(unique_exchanges[:10])
            })
        else:
            # Return fallback data if Overpass API fails
            fallback = get_fallback_exchanges(lat, lon)
            return jsonify({
                'success': True,
                'exchanges': fallback,
                'count': len(fallback),
                'note': 'Using sample data (Overpass API temporarily unavailable)'
            })
            
    except requests.exceptions.Timeout:
        fallback = get_fallback_exchanges(float(lat) if lat else 40.7128, float(lon) if lon else -74.0060)
        return jsonify({
            'success': True,
            'exchanges': fallback,
            'count': len(fallback),
            'note': 'Using sample data (request timeout)'
        })
    except Exception as e:
        app.logger.error(f"Exchange finder error: {str(e)}")
        fallback = get_fallback_exchanges(40.7128, -74.0060)
        return jsonify({
            'success': True,
            'exchanges': fallback,
            'count': len(fallback),
            'note': f'Using sample data (service temporarily unavailable)'
        })

def get_fallback_exchanges(lat, lon):
    """Provide fallback exchange locations when API fails"""
    lat = float(lat) if lat else 40.7128
    lon = float(lon) if lon else -74.0060
    
    # Create sample exchanges around the given location
    return [
        {
            'name': 'Central Currency Exchange',
            'lat': lat + 0.002,
            'lon': lon + 0.001,
            'address': 'Downtown Financial District, Main Street',
            'opening_hours': 'Mon-Fri 9:00-17:00, Sat 10:00-14:00',
            'phone': '+1 (555) 123-4567'
        },
        {
            'name': 'International Money Transfer',
            'lat': lat - 0.0015,
            'lon': lon + 0.0025,
            'address': 'City Shopping Mall, Level 2, Unit 45',
            'opening_hours': 'Mon-Sat 10:00-20:00, Sun 11:00-18:00',
            'phone': '+1 (555) 234-5678'
        },
        {
            'name': 'Global Exchange Services',
            'lat': lat + 0.001,
            'lon': lon - 0.002,
            'address': 'International Airport, Terminal 3, Arrivals Hall',
            'opening_hours': 'Open 24 hours, 7 days a week',
            'phone': '+1 (555) 345-6789'
        },
        {
            'name': 'FastCash Currency',
            'lat': lat - 0.002,
            'lon': lon - 0.001,
            'address': 'Metro Plaza, Ground Floor, Shop G12',
            'opening_hours': 'Mon-Fri 9:30-18:30, Sat 10:00-16:00',
            'phone': '+1 (555) 456-7890'
        },
        {
            'name': 'Premier Exchange Bureau',
            'lat': lat + 0.0025,
            'lon': lon - 0.0015,
            'address': 'Business Tower, First Floor',
            'opening_hours': 'Mon-Fri 9:00-18:00, Closed weekends',
            'phone': '+1 (555) 567-8901'
        }
    ]

# ============ Original Routes (Preserved) ============

def get_prediction(currency, date):
    try:
        # Convert date string to datetime for validation
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        current_date = datetime.now()
        
        # For past dates, fetch historical data from Frankfurter API
        if selected_date.date() <= current_date.date():
            try:
                response = requests.get(f"https://api.frankfurter.app/{date}?from=USD&to={currency}", timeout=10)
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
            response = requests.get(f"https://api.frankfurter.app/latest?from=USD&to={currency}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_rate = data['rates'][currency]
                # Simulate a prediction by adding slight variation
                variation = random.uniform(-0.05, 0.05)  # ±5% variation
                predicted_rate = latest_rate * (1 + variation)
                return f"1 USD = {predicted_rate:.4f} {currency} (predicted)"
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
    message_type = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        currency = request.form.get('currency')
        alert_type = request.form.get('alert_type')
        threshold = float(request.form.get('threshold'))
        notification_method = request.form.get('notification_method')

        try:
            response = requests.get(f"https://api.frankfurter.app/latest?from=USD&to={currency}", timeout=10)
            if response.status_code != 200:
                flash('Error fetching exchange rate.', 'error')
                return redirect(url_for('alerts'))
                
            data = response.json()
            current_rate = data['rates'][currency]

            if (alert_type == 'above' and current_rate > threshold) or (alert_type == 'below' and current_rate < threshold):
                alert_message = f"Alert Triggered: USD/{currency} rate is {current_rate:.4f}, which is {alert_type} your threshold of {threshold:.4f}!"
                
                if notification_method == 'email' and app.config['MAIL_USERNAME'] != 'your-email@gmail.com':
                    try:
                        msg = Message(
                            subject=f"Currency Alert: USD/{currency}",
                            recipients=[email],
                            body=alert_message
                        )
                        mail.send(msg)
                        message = "Alert triggered successfully! Email sent."
                        message_type = 'success'
                    except Exception as e:
                        message = "Alert triggered! (Email configuration needed)"
                        message_type = 'info'
                        app.logger.error(f"Failed to send email: {str(e)}")
                else:
                    message = "Alert triggered successfully!"
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
    """Legacy endpoint for exchange finder"""
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    radius = float(request.args.get('radius', 5000))

    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"[out:json];node[\"amenity\"=\"bureau_de_change\"](around:{radius},{lat},{lng});out body;"
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
