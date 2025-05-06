
**Anjali_BtechCSE(DS)_CurrencyExchangeOptimizationApp**

# PROJECT TITLE 
**OptiExchange**

# TEAM MEMBERS  
- Anjali (2301420021)  
- Jigyasa Singh (2301420032)  
- Bhuveeta Sarohi (2301420011)  
- Shubham Dey (2301420012)

# PROJECT DESCRIPTION 
OptiExchange is a lightweight web application that predicts currency exchange rates for any selected date. It supports major currencies like USD, EUR, GBP, and JPY with a clean, responsive interface featuring dark/light mode. The app calculates predictions client-side using market trend algorithms to estimate historical, current, and future exchange rates. Designed for travelers and forex enthusiasts, it provides quick rate checks through a simple one-page form. Built with HTML, CSS, and vanilla JavaScript, this frontend demo simulates realistic rate fluctuations based on volatility patterns.

# VIDEO EXPLANATION 
[Click here to watch the video presentation](https://krmangalameduin-my.sharepoint.com/:f:/g/personal/2301420021_krmu_edu_in/Er7bRq16NnZPhFUBFABkiX4B6nL50qZjSucoStyLNorKBw?e=0G4z6eth)

# PROTOTYPE (Figma Design)  
[Click here to view the Figma Prototype](https://www.figma.com/proto/v8HIb3K6mNRuX1tMUBt1SD/optiexchange?page-id=1649%3A6986&node-id=1661-6433&p=f&viewport=182%2C105%2C0.07&t=xXYblK55r0BTlEtO-1&scaling=scale-down&content-scaling=fixed&starting-point-node-id=1649%3A13239)

# DEPLOYMENT
Current URL: https://optiexchange.onrender.com
- Deployed using Render’s free tier with a PostgreSQL database (optiexchange-db).

# TECHNOLOGIES USED

**BACKEND:**  
- Flask 2.3.2 (Python web framework)
- Flask-SQLAlchemy 3.0.3 (database ORM)
- Flask-Login 0.6.2 (user authentication)
- Gunicorn 20.1.0 (WSGI server for deployment)
- PostgreSQL (database hosted on Render)

**FRONTEND:**  
- HTML5
- CSS3 (with Bootstrap 5 for responsive styling)
- JavaScript (for dynamic client-side interactions)
- Jinja2 (template engine for Flask)

**APIs INTEGRATED:**  
- Frankfurter API (real-time and historical exchange rates)
- Overpass API (currency exchange locations via OpenStreetMap)

**DEPLOYMENT:**  
- Render (cloud platform for hosting)
- GitHub (version control and CI/CD integration)

# KEY FEATURES  
- User Authentication: Secure registration and login with Flask-Login and Flask-SQLAlchemy.
- Currency Converter: Convert between major currencies (e.g., USD, EUR, GBP, JPY) using real-time data from the Frankfurter API.
- Exchange Rate Trends: Display historical and current exchange rate trends for selected currencies.
- Exchange Finder: Locate nearby currency exchange services using the Overpass API and Leaflet for map visualization.
- Responsive Design: Mobile-friendly interface with Bootstrap and custom CSS.
- Secure Deployment: Hosted on Render with PostgreSQL for persistent data storage.
