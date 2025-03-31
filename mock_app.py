#!/usr/bin/env python3
"""
Mock Flask application for STB-ReStreamer UI testing.

This application simulates the core features of the STB-ReStreamer app
for UI testing purposes. It provides basic authentication, navigation,
and simulated content pages.
"""
import argparse
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'test_secret_key'

# Mock user credentials
USERS = {
    'admin': 'admin',
    'user': 'password',
}

# HTML Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STB-ReStreamer - Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 40px;
            width: 90%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        button:hover {
            background-color: #45a049;
        }
        .error {
            color: red;
            margin-bottom: 15px;
            text-align: center;
        }
        @media screen and (max-width: 480px) {
            .login-container {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>STB-ReStreamer Login</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Log In</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STB-ReStreamer - Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            display: flex;
            min-height: 100vh;
            flex-wrap: wrap;
        }
        .sidebar {
            background-color: #333;
            color: white;
            width: 250px;
            padding: 20px;
            box-sizing: border-box;
        }
        .content {
            flex: 1;
            padding: 20px;
            box-sizing: border-box;
        }
        h1 {
            margin-top: 0;
            color: #333;
        }
        .welcome {
            margin-bottom: 30px;
            font-size: 18px;
        }
        .nav-item {
            margin-bottom: 15px;
        }
        .nav-item a {
            color: white;
            text-decoration: none;
            display: block;
            padding: 10px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav-item a:hover {
            background-color: #555;
        }
        .logout {
            margin-top: 30px;
        }
        .logout a {
            color: #ff6b6b;
        }
        .stats-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-box {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            flex: 1;
            min-width: 200px;
        }
        .stat-box h3 {
            margin-top: 0;
            color: #666;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
        }
        
        @media screen and (max-width: 768px) {
            .container {
                flex-direction: column;
            }
            .sidebar {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container" id="dashboard">
        <div class="sidebar">
            <div class="welcome">Welcome, {{ username }}</div>
            <div class="nav-item"><a href="{{ url_for('index') }}">Dashboard</a></div>
            <div class="nav-item"><a href="{{ url_for('portals') }}">Portals</a></div>
            <div class="nav-item"><a href="{{ url_for('channels') }}">Channels</a></div>
            <div class="nav-item"><a href="{{ url_for('categories') }}">Categories</a></div>
            <div class="nav-item"><a href="{{ url_for('epg') }}">EPG</a></div>
            <div class="nav-item"><a href="{{ url_for('settings') }}">Settings</a></div>
            <div class="logout"><a href="{{ url_for('logout') }}">Logout</a></div>
        </div>
        <div class="content">
            <h1>Dashboard</h1>
            <div class="stats-container">
                <div class="stat-box">
                    <h3>Active Portals</h3>
                    <div class="stat-value">12</div>
                </div>
                <div class="stat-box">
                    <h3>Channels</h3>
                    <div class="stat-value">348</div>
                </div>
                <div class="stat-box">
                    <h3>Categories</h3>
                    <div class="stat-value">24</div>
                </div>
            </div>
            <div class="stat-box">
                <h3>System Status</h3>
                <p>All systems operational</p>
                <p>Last update: Today at 12:34 PM</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(DASHBOARD_TEMPLATE, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials. Please try again.'
    
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/portals')
def portals():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Portals Page"

@app.route('/channels')
def channels():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Channels Page"

@app.route('/categories')
def categories():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Categories Page"

@app.route('/epg')
def epg():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "EPG Page"

@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Settings Page"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the mock STB-ReStreamer app')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
    app.run(debug=True, port=args.port) 