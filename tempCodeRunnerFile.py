from flask import Flask, render_template, request, jsonify
import requests
import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Supported currencies (matches common ones from Frankfurter API)
currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD']

@app.route('/', methods=['GET', 'POST'])
def index():
    prediction = None
    selected_currency = None
    selected_date = None

    if request.method == 'POST':
        currency = request.form['currency']
        date_str = request.form['date']
        selected_currency = currency
        selected_date = date_str

        try:
            # Get historical rate from Frankfurter API
            response = requests.get(f"https://api.frankfurter.app/{date_str}?to={currency}")
            data = response.json()
            
            if 'rates' in data and currency in data['rates']:
                prediction = round(data['rates'][currency], 4)
            else:
                prediction = "Could not predict rate for selected date"
        except Exception as e:
            prediction = f"Prediction error: {str(e)}"

    return render_template("index.html",
                         currencies=currencies,
                         prediction=prediction,
                         selected_currency=selected_currency,
                         selected_date=selected_date)

@app.route('/alerts', methods=['GET', 'POST'])
def alerts():
    message = None
    if request.method == 'POST':
        email = request.form['email']
        currency = request.form['currency']
        threshold = float(request.form['threshold'])
        alert_type = request.form.get('alert_type', 'above')

        try:
            # Get latest rate from Frankfurter API
            response = requests.get(f"https://api.frankfurter.app/latest?to={currency}")
            data = response.json()
            
            if 'rates' in data and currency in data['rates']:
                current_rate = data['rates'][currency]
                
                # Only show message if alert triggers
                if (alert_type == 'above' and current_rate > threshold) or \
                   (alert_type == 'below' and current_rate < threshold):
                    print(f"\n📧 [SIMULATED EMAIL] To: {email}")
                    print(f"   Currency: {currency}, Rate: {current_rate}")
                    print(f"   Alert: Rate is {'above' if alert_type == 'above' else 'below'} {threshold}\n")
                    message = "Alert triggered successfully!"
        except Exception as e:
            message = f"Error: {str(e)}"

    return render_template("alerts.html", currencies=currencies, message=message)

@app.route('/find_exchanges', methods=['GET'])
def find_exchanges():
    return render_template("exchange_finder.html", currencies=currencies)

@app.route('/api/nearby_exchanges', methods=['GET'])
def nearby_exchanges():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=1000, type=int)  # meters
        
        # Validate parameters
        if lat is None or lng is None:
            return jsonify({"error": "Latitude and longitude are required"}), 400
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Overpass API query
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          node["amenity"="bureau_de_change"](around:{radius},{lat},{lng});
          way["amenity"="bureau_de_change"](around:{radius},{lat},{lng});
          relation["amenity"="bureau_de_change"](around:{radius},{lat},{lng});
        );
        out center;
        """
        
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()
        data = response.json()
        
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)