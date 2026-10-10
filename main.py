"""
Food Calorie Estimation API using Flask and CNN Deep Learning Model
"""
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_cors import CORS
import numpy as np
import base64
import io
import json
import os
from PIL import Image
import requests
API_KEY = os.environ.get("USDA_API_KEY", "ZRREJ2EWXdQvYYckq9EAQdlbKNSbn6Nbk8yybRbI")

def get_calories_from_api(food_name):
    try:
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={API_KEY}"

        response = requests.get(url)
        data = response.json()

        if "foods" not in data or len(data["foods"]) == 0:
            return None

        nutrients = data["foods"][0].get("foodNutrients", [])

        calories = protein = carbs = fat = "Unknown"

        for n in nutrients:
            name = n.get("nutrientName")
            value = n.get("value")

            if name == "Energy":
                calories = value
            elif name == "Protein":
                protein = value
            elif name == "Carbohydrate, by difference":
                carbs = value
            elif name == "Total lipid (fat)":
                fat = value

        return {
            "calories": calories,
            "serving": "100g",
            "protein": protein,
            "carbs": carbs,
            "fat": fat
        }

    except Exception as e:
        print("API ERROR:", e)
        return None

# TensorFlow imports commented out
# import tensorflow as tf
# from tensorflow import keras

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_dev_key")
CORS(app)

# ─── SQLite Database Setup ───────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

ADMIN_EMAILS = [
    "admin@example.com",
    "YOUR_REAL_EMAIL@gmail.com"
]

def get_db():
    """Get a per-request SQLite connection stored on Flask's 'g' object."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
        g.db.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Create all tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            email       TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            banned      INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT,
            last_active TEXT
        );

        CREATE TABLE IF NOT EXISTS foods (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            calories REAL,
            protein  REAL,
            carbs    REAL,
            fat      REAL,
            serving  TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email  TEXT,
            action_type TEXT,
            food_name   TEXT,
            quantity    TEXT,
            calories    REAL,
            timestamp   TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id        INTEGER,
            admin_username  TEXT,
            action          TEXT,
            target_user_id  INTEGER,
            details         TEXT,
            timestamp       TEXT
        );
    """)
    
    # Dynamic schema updates for user goals
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'calorie_goal' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN calorie_goal INTEGER DEFAULT 2000")
    if 'protein_goal' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN protein_goal INTEGER DEFAULT 150")
    if 'carbs_goal' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN carbs_goal INTEGER DEFAULT 250")
    if 'fat_goal' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN fat_goal INTEGER DEFAULT 70")
        
    conn.commit()
    conn.close()
    print("[OK] SQLite database initialised at", DB_PATH)

init_db()

def create_default_admin():
    """Insert the default admin account if it doesn't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", ("admin@example.com",))
    if cur.fetchone() is None:
        from datetime import datetime
        cur.execute(
            "INSERT INTO users (username, email, password, role, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?)",
            ("admin", "admin@example.com", generate_password_hash("admin123"),
             "admin", datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        print("[OK] Default admin created  ->  admin@example.com / admin123")
    conn.close()

create_default_admin()

# Food classes that our model can predict
FOOD_CLASSES = [
    "apple", "banana", "burger", "pizza", "dosa", 
    "french_fries", "hot_dog", "ice_cream", "omelette", 
    "pasta", "rice", "salad", "sandwich", "sushi", "tacos"
]

# Calorie data for each food item (per serving)
CALORIE_DATA = {
    "apple": {"calories": 95, "serving": "1 medium (182g)", "protein": "0.5g", "carbs": "25g", "fat": "0.3g"},
    "banana": {"calories": 105, "serving": "1 medium (118g)", "protein": "1.3g", "carbs": "27g", "fat": "0.4g"},
    "burger": {"calories": 354, "serving": "1 burger (110g)", "protein": "20g", "carbs": "29g", "fat": "17g"},
    "pizza": {"calories": 285, "serving": "1 slice (107g)", "protein": "12g", "carbs": "36g", "fat": "10g"},
    "dosa": {"calories": 168, "serving": "1 dosa (100g)", "protein": "4g", "carbs": "29g", "fat": "4g"},
    "french_fries": {"calories": 312, "serving": "1 medium (117g)", "protein": "3.4g", "carbs": "41g", "fat": "15g"},
    "hot_dog": {"calories": 290, "serving": "1 hot dog (98g)", "protein": "11g", "carbs": "24g", "fat": "17g"},
    "ice_cream": {"calories": 207, "serving": "1 cup (132g)", "protein": "3.5g", "carbs": "24g", "fat": "11g"},
    "omelette": {"calories": 154, "serving": "1 omelette (2 eggs)", "protein": "11g", "carbs": "1g", "fat": "12g"},
    "pasta": {"calories": 220, "serving": "1 cup cooked (140g)", "protein": "8g", "carbs": "43g", "fat": "1.3g"},
    "rice": {"calories": 206, "serving": "1 cup cooked (158g)", "protein": "4.3g", "carbs": "45g", "fat": "0.4g"},
    "salad": {"calories": 152, "serving": "1 bowl (207g)", "protein": "3g", "carbs": "11g", "fat": "12g"},
    "sandwich": {"calories": 252, "serving": "1 sandwich (145g)", "protein": "10g", "carbs": "29g", "fat": "10g"},
    "sushi": {"calories": 200, "serving": "6 pieces (158g)", "protein": "9g", "carbs": "38g", "fat": "0.7g"},
    "tacos": {"calories": 226, "serving": "1 taco (135g)", "protein": "9g", "carbs": "20g", "fat": "12g"}
}

# Global model variable
model = None

# API_KEY is set globally at the top of the file

# Food Label Mapping System
food_labels = [
    "apple pie", "baby back ribs", "baklava", "beef carpaccio", "beef tartare", "beet salad", "beignets",
    "bibimbap", "bread pudding", "breakfast burrito", "bruschetta", "caesar salad", "cannoli", "caprese salad",
    "carrot cake", "ceviche", "cheesecake", "cheese plate", "chicken curry", "chicken quesadilla", "chicken wings",
    "chocolate cake", "chocolate mousse", "churros", "clam chowder", "club sandwich", "crab cakes", "creme brulee",
    "croque madame", "cup cakes", "deviled eggs", "donuts", "dumplings", "edamame", "eggs benedict", "escargots",
    "falafel", "filet mignon", "fish and chips", "foie gras", "french fries", "french onion soup", "french toast",
    "fried calamari", "fried rice", "frozen yogurt", "garlic bread", "gnocchi", "greek salad", "grilled cheese sandwich",
    "grilled salmon", "guacamole", "hamburger", "hot and sour soup", "hot dog", "huevos rancheros", "hummus",
    "ice cream", "lasagna", "lobster bisque", "lobster roll sandwich", "macaroni and cheese", "macarons", "miso soup",
    "mussels", "nachos", "omelette", "onion rings", "oysters", "pad thai", "paella", "pancakes", "panna cotta",
    "peking duck", "pho", "pizza", "pork chop", "poutine", "prime rib", "pulled pork sandwich", "ramen", "ravioli",
    "red velvet cake", "risotto", "samosa", "sashimi", "scallops", "seaweed salad", "shrimp and grits",
    "spaghetti bolognese", "spaghetti carbonara", "spring rolls", "steak", "strawberry shortcake", "sushi", "tacos",
    "takoyaki", "tiramisu", "tuna tartare", "waffles"
]

def get_food_name(class_id, confidence):

    global food_labels

    # lower unknown threshold
    if confidence < 0.05:
        return "Unknown Food"

    if class_id < len(food_labels):
        return food_labels[class_id]

    return "Unknown Food"

# Normalize model food names for USDA lookups and calorie mapping
def normalize_food_name(food_name):
    if not food_name:
        return None

    normalized = food_name.lower().strip()

    # Simple alias mapping for commonly misclassified names
    aliases = {
        'french fries': 'french fries',
        'fries': 'french fries',
        'hot dog': 'hot dog',
        'hamburger': 'burger',
        'ice cream': 'ice cream',
        'chicken wings': 'chicken wings',
        'pizza': 'pizza',
        'sushi': 'sushi',
        'tacos': 'tacos',
        'bibimbap': 'bibimbap',
        'burger': 'burger',
        'dosa': 'dosa',
        'salad': 'salad',
    }

    if normalized in aliases:
        return aliases[normalized]

    # remove punctuation and underscores
    normalized = normalized.replace('_', ' ').replace('-', ' ').strip()

    return normalized

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import json

def load_mapping():
    """Load class label mapping file (food101_classes.txt or JSON)."""
    global food_labels
    mapping_path = os.path.join(os.path.dirname(__file__), 'food101_classes.txt')
    try:
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                food_labels = [line.strip().replace('_', ' ').title() for line in f if line.strip()]
            print("Loaded food101_classes.txt mapping.")
        else:
            print("Mapping file not found, using fallback array.")
    except Exception as e:
        print(f"Error loading mapping: {e}")

load_mapping()

# Standard ImageNet pre-processing transform for MobileNetV2
predict_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def load_model():
    """Load CNN model weights from local path."""
    global model
    try:
        model_path = os.path.join(os.path.dirname(__file__), 'food101_mobilenet_v2.pth')
        if os.path.exists(model_path):
            print("Loading CNN model weights from:", model_path)
            model = models.mobilenet_v2(num_classes=101)
            model.load_state_dict(torch.load(model_path, map_location='cpu'))
            model.eval()
            print("[OK] CNN Model loaded successfully!")
        else:
            print("[Warning] Local CNN model file not found. Fallback to mock.")
            model = None
    except Exception as e:
        print("Error loading CNN model:", e)
        model = None
    return model

# Load model at startup
load_model()

import io

def predict_food(image_data):
    """
    Perform CNN food classification on the input image.
    """
    global model, food_labels
    if model is None:
        load_model()
    if model is None:
        print("CNN model unavailable, fallback to mock Pizza")
        return "Pizza", 0.92, [
            {"name": "Pizza", "confidence": 92.0},
            {"name": "Burger", "confidence": 5.0},
            {"name": "Pasta", "confidence": 3.0}
        ]

    try:
        img = Image.open(io.BytesIO(image_data)).convert('RGB')
        tensor = predict_transform(img).unsqueeze(0)
        
        with torch.no_grad():
            outputs = model(tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            
        top3_prob, top3_indices = torch.topk(probabilities, 3)
        
        predictions_list = []
        for i in range(3):
            prob = float(top3_prob[i])
            idx = int(top3_indices[i])
            # Fetch label and clean it
            class_name = food_labels[idx]
            predictions_list.append({
                "name": class_name,
                "confidence": round(prob * 100, 1)
            })
            
        best_name = predictions_list[0]["name"]
        best_conf = predictions_list[0]["confidence"] / 100.0
        
        return best_name, best_conf, predictions_list
    except Exception as e:
        print("Prediction error:", e)
        return "Pizza", 0.92, [
            {"name": "Pizza", "confidence": 92.0},
            {"name": "Burger", "confidence": 5.0},
            {"name": "Pasta", "confidence": 3.0}
        ]
    
import time

@app.route('/predict', methods=['POST'])
@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Predict food and calories from uploaded image.
    
    Accepts:
    - File upload with key 'image'
    - Base64 encoded image in JSON body with key 'image'
    
    Returns:
    - Predicted food name (or Unknown Food)
    - Calorie information
    - Confidence score & top 3 predictions
    """
    try:
        image_data = None
        
        # Check for file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                image_data = file.read()
        
        # Check for base64 encoded image in JSON
        if image_data is None and request.is_json:
            data = request.get_json()
            if 'image' in data:
                # Remove data URL prefix if present
                base64_str = data['image']
                if ',' in base64_str:
                    base64_str = base64_str.split(',')[1]
                image_data = base64.b64decode(base64_str)
        
        if image_data is None:
            return jsonify({
                "success": False,
                "error": "No image provided. Please upload an image file or send base64 encoded image."
            }), 400
        
        # Predict food class with final fix logic
        food_name, confidence, predictions_list = predict_food(image_data)

        # Apply a usage threshold to reduce obvious classification errors
        if confidence < 0.15 or food_name == "Unknown Food":
            predicted_food = "Unknown Food"
        else:
            predicted_food = food_name

        # UI Compatibility Mapper wrapper
        prediction_result = {
            "food": predicted_food,
            "final_food": predicted_food,
            "confidence": confidence,
            "predictions": predictions_list,
            "top3": predictions_list,
            "is_unknown": (predicted_food == "Unknown Food")
        }

        # Get calorie information from USDA API (or fallback to stored CALORIE_DATA)
        calorie_info = None
        if predicted_food != "Unknown Food":
            normalized_name = normalize_food_name(predicted_food)
            calorie_info = get_calories_from_api(normalized_name)
            if not calorie_info or calorie_info.get("calories") == "Unknown":
                if normalized_name in CALORIE_DATA:
                    calorie_info = CALORIE_DATA[normalized_name]
                elif normalized_name.replace(' ', '_') in CALORIE_DATA:
                    calorie_info = CALORIE_DATA[normalized_name.replace(' ', '_')]

        if calorie_info is None:
            calorie_info = {
                "calories": "Unknown",
                "serving": "Unknown",
                "protein": "Unknown",
                "carbs": "Unknown",
                "fat": "Unknown"
            }

        return jsonify({
            "success": True,
            "predictions": prediction_result.get("predictions", []),
            "is_unknown": prediction_result.get("is_unknown", False),
            # Dual-struct payload dynamically handling the new data shape natively
            "final_food": predicted_food,
            "confidence": prediction_result.get("confidence", 0),
            "top3": prediction_result.get("predictions", []),
            "calories_data": {
                "calories": calorie_info["calories"],
                "serving_size": calorie_info["serving"],
                "protein": calorie_info["protein"],
                "carbohydrates": calorie_info["carbs"],
                "fat": calorie_info["fat"]
            },
            # UI Backward compatibility
            "prediction": {
                "food": predicted_food,
                "confidence": prediction_result.get("confidence", 0),
                "top3": prediction_result.get("predictions", []),
                "nutrition": {
                    "calories": calorie_info["calories"],
                    "serving_size": calorie_info["serving"],
                    "protein": calorie_info["protein"],
                    "carbohydrates": calorie_info["carbs"],
                    "fat": calorie_info["fat"]
                }
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/manual', methods=['POST'])
def manual_entry():
    """
    Handle manual food entry:
    - If calories_per_unit and quantity are provided, uses them directly.
    - Else falls back to USDA grams-based lookup with 'grams'.
    """
    try:
        data = request.get_json()
        if not data or 'food' not in data:
            return jsonify({"success": False, "error": "Missing food name."}), 400

        food_name = data['food'].strip()
        if not food_name:
            return jsonify({"success": False, "error": "Food name must not be empty."}), 400

        calories_per_unit = data.get('calories_per_unit')
        unit = data.get('unit')
        quantity = data.get('quantity')

        if calories_per_unit is not None and unit is not None and quantity is not None:
            try:
                calories_per_unit = float(calories_per_unit)
                quantity = float(quantity)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Calories per unit and quantity must be numeric."}), 400

            if calories_per_unit <= 0 or quantity <= 0:
                return jsonify({"success": False, "error": "Calories per unit and quantity must be positive."}), 400

            if unit not in ['grams', 'pieces']:
                return jsonify({"success": False, "error": "Unit must be 'grams' or 'pieces'."}), 400

            total_calories = round(calories_per_unit * quantity, 2)
            nutrition = {
                "calories_per_unit": calories_per_unit,
                "quantity": quantity,
                "unit": unit,
                "total_calories": total_calories
            }

            return jsonify({
                "success": True,
                "food": food_name.title(),
                "nutrition": nutrition
            })

        # Fallback flow: grams-based USDA lookup
        if 'grams' not in data:
            return jsonify({"success": False, "error": "Missing calories or grams data for manual entry."}), 400

        try:
            grams = float(data['grams'])
            if grams <= 0:
                raise ValueError()
        except ValueError:
            return jsonify({"success": False, "error": "Grams must be a positive number."}), 400

        calorie_info = get_calories_from_api(food_name)
        if calorie_info is None or calorie_info.get("calories") == "Unknown":
            return jsonify({"success": False, "error": f"Could not find exact nutrition data for '{food_name}'."}), 404

        multiplier = grams / 100.0

        def calc_prop(val):
            try:
                if isinstance(val, str):
                    import re
                    num_str = re.sub(r'[^\d.]', '', val)
                    if num_str:
                        return round(float(num_str) * multiplier, 2)
                    return "Unknown"
                return round(float(val) * multiplier, 2)
            except (ValueError, TypeError):
                return "Unknown"
                
        calculated = {
            "calories": calc_prop(calorie_info.get("calories", "Unknown")),
            "serving_size": f"{grams}g",
            "protein": calc_prop(calorie_info.get("protein", "Unknown")),
            "carbohydrates": calc_prop(calorie_info.get("carbs", "Unknown")),
            "fat": calc_prop(calorie_info.get("fat", "Unknown"))
        }
        
        return jsonify({
            "success": True,
            "food": food_name.title(),
            "nutrition": calculated
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/foods', methods=['GET'])
def get_foods():
    """Get list of all supported foods and their calorie information."""
    foods = []
    for food_class in FOOD_CLASSES:
        info = CALORIE_DATA.get(food_class, {})
        foods.append({
            "name": food_class.replace("_", " ").title(),
            "calories": info.get("calories", "Unknown"),
            "serving": info.get("serving", "Unknown")
        })
    return jsonify({"foods": foods})

# Initialize model on startup disabled
# load_model()

@app.route("/")
def home():
    if 'user_id' in session:
        role = session.get('role', 'user')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            if user['banned']:
                if request.is_json:
                    return jsonify({"success": False, "error": "Your account has been banned. Please contact the administrator."}), 403
                flash('Your account has been banned. Please contact the administrator.', 'error')
                return render_template('login.html')

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user['email']

            from datetime import datetime
            db.execute("UPDATE users SET last_active = ? WHERE id = ?",
                       (datetime.utcnow().isoformat(), user['id']))
            db.commit()

            role = session['role']
            redirect_url = url_for("admin_dashboard") if role == "admin" else url_for("user_dashboard")

            if request.is_json:
                return jsonify({"success": True, "role": role, "user_id": user['id'],
                                "username": user['username'], "redirect": redirect_url})
            return redirect(redirect_url)
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid email or password"}), 401
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

        if not username or not password or not email:
            if request.is_json:
                return jsonify({"success": False, "error": "Username, email and password are required"}), 400
            flash('Username, email and Password are required', 'error')
            return render_template('signup.html')

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?", (email, username)
        ).fetchone()
        if existing:
            if request.is_json:
                return jsonify({"success": False, "error": "Username or email already exists"}), 409
            flash('Username or email already exists', 'error')
            return render_template('signup.html')

        from datetime import datetime
        now_iso = datetime.utcnow().isoformat()
        role = "admin" if email in ADMIN_EMAILS else "user"
        hashed_password = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, email, password, role, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, hashed_password, role, now_iso, now_iso)
        )
        db.commit()

        if request.is_json:
            return jsonify({"success": True, "message": "Account created successfully! Please login.",
                            "redirect": url_for("login")})
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route("/register", methods=['POST'])
def register():
    return signup()

@app.route("/user-dashboard")
def user_dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard', 'error')
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('user-dashboard.html', username=session['username'])

@app.route('/calorie', methods=['GET'])
def calorie_page():
    # direct static calorie calculator UI
    if 'user_id' not in session:
        flash('Please login to access the calorie calculator', 'error')
        return redirect(url_for('login'))
    return render_template('calorie_page.html', username=session.get('username', 'User'))

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route("/api/health")
def health():
    return {"status": "ok"}

@app.route("/api/foods")
def foods():
    return {"foods": food_labels}

@app.route("/api/user/goals", methods=['GET', 'POST'])
def user_goals():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    
    db = get_db()
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.get_json()
        calorie_goal = data.get('calorie_goal')
        protein_goal = data.get('protein_goal')
        carbs_goal = data.get('carbs_goal')
        fat_goal = data.get('fat_goal')
        
        try:
            calorie_goal = int(calorie_goal)
            protein_goal = int(protein_goal)
            carbs_goal = int(carbs_goal)
            fat_goal = int(fat_goal)
            if calorie_goal <= 0 or protein_goal <= 0 or carbs_goal <= 0 or fat_goal <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid goals. Must be positive integers."}), 400
            
        db.execute(
            "UPDATE users SET calorie_goal = ?, protein_goal = ?, carbs_goal = ?, fat_goal = ? WHERE id = ?",
            (calorie_goal, protein_goal, carbs_goal, fat_goal, user_id)
        )
        db.commit()
        return jsonify({"success": True, "message": "Goals updated successfully."})
        
    user = db.execute("SELECT calorie_goal, protein_goal, carbs_goal, fat_goal FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
        
    return jsonify({
        "success": True,
        "goals": {
            "calorie_goal": user['calorie_goal'],
            "protein_goal": user['protein_goal'],
            "carbs_goal": user['carbs_goal'],
            "fat_goal": user['fat_goal']
        }
    })

@app.route('/api/log_activity', methods=['POST'])
def log_activity():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data = request.get_json()
    action_type = data.get('action_type', 'unknown')
    food_name = data.get('food_name', '')
    quantity = data.get('quantity', '')
    calories = data.get('calories', 0)

    from datetime import datetime
    now_iso = datetime.utcnow().isoformat()

    db = get_db()
    email = session.get('email', 'Unknown')

    # Update last_active for the user
    db.execute("UPDATE users SET last_active = ? WHERE id = ?",
               (now_iso, session['user_id']))

    # Insert activity log
    db.execute(
        "INSERT INTO activity_logs (user_email, action_type, food_name, quantity, calories, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (email, action_type, food_name, quantity, calories, now_iso)
    )
    db.commit()

    return jsonify({"success": True})

# === Admin API Routes ===
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access restricted.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin/stats")
@admin_required
def admin_stats():
    from datetime import datetime
    from collections import Counter

    db = get_db()
    total_users  = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_foods  = db.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
    admin_count  = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
    user_count   = db.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]
    total_searches = db.execute("SELECT COUNT(*) FROM activity_logs WHERE action_type = 'search'").fetchone()[0]

    today_str = datetime.utcnow().date().isoformat()
    active_today = db.execute(
        "SELECT COUNT(*) FROM users WHERE last_active LIKE ?", (today_str + '%',)
    ).fetchone()[0]

    row = db.execute(
        "SELECT food_name FROM activity_logs WHERE action_type = 'search' AND food_name != '' "
        "GROUP BY food_name ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    most_searched = row[0] if row else "None"

    return jsonify({
        "totalUsers": total_users,
        "totalFoods": total_foods,
        "adminUsers": admin_count,
        "regularUsers": user_count,
        "totalSearches": total_searches,
        "activeToday": active_today,
        "mostSearched": most_searched
    })

@app.route("/admin/activity_logs")
@admin_required
def admin_activity_logs():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM activity_logs ORDER BY timestamp DESC"
    ).fetchall()
    return jsonify({"logs": [dict(r) for r in rows]})

@app.route("/admin/get_foods")
@admin_required
def get_foods_api():
    db = get_db()
    rows = db.execute("SELECT * FROM foods").fetchall()
    return jsonify({"foods": [dict(r) for r in rows]})

@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    # Render previously separated admin-dashboard UI directly
    return render_template('admin-dashboard.html')

@app.route("/admin/users")
@admin_required
def admin_users():
    db = get_db()
    rows = db.execute(
        "SELECT id, username, email, role, banned, created_at, last_active FROM users"
    ).fetchall()
    users_safe = [dict(r) for r in rows]
    if request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({"users": users_safe})
    return render_template('users.html', users=users_safe)

@app.route("/admin/delete_user/<int:id>", methods=['POST'])
@admin_required
def delete_user(id):
    if id == session.get('user_id'):
        flash('Cannot delete yourself!', 'error')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (id,))
    db.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route("/admin/foods")
@admin_required
def admin_foods():
    db = get_db()
    foods = [dict(r) for r in db.execute("SELECT * FROM foods").fetchall()]
    return render_template('foods.html', foods=foods)

@app.route("/admin/add_food", methods=['GET', 'POST'])
@admin_required
def add_food():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            calories = data.get('calories')
            serving = data.get('serving')
            protein = data.get('protein', 0)
            carbs = data.get('carbs', 0)
            fat = data.get('fat', 0)
        else:
            name = request.form.get('name')
            calories = request.form.get('calories')
            serving = request.form.get('serving', '100g')
            protein = request.form.get('protein', 0)
            carbs = request.form.get('carbs', 0)
            fat = request.form.get('fat', 0)

        if not name or not calories:
            if request.is_json:
                return jsonify({"success": False, "error": "Name and Calories are required."}), 400
            flash('Name and Calories are required.', 'error')
            return render_template('add_food.html')

        db = get_db()
        cur = db.execute(
            "INSERT INTO foods (name, calories, protein, carbs, fat, serving) VALUES (?, ?, ?, ?, ?, ?)",
            (name, float(calories), float(protein), float(carbs), float(fat), serving)
        )
        db.commit()
        new_food = {"id": cur.lastrowid, "name": name, "calories": float(calories),
                    "protein": float(protein), "carbs": float(carbs), "fat": float(fat), "serving": serving}

        if request.is_json:
            return jsonify({"success": True, "message": "Food added successfully.", "food": new_food})
        flash('Food added successfully.', 'success')
        return redirect(url_for('admin_foods'))

    return render_template('add_food.html')

@app.route("/admin/delete_food/<int:id>", methods=['POST'])
@admin_required
def delete_food(id):
    db = get_db()
    db.execute("DELETE FROM foods WHERE id = ?", (id,))
    db.commit()
    flash('Food deleted successfully.', 'success')
    return redirect(url_for('admin_foods'))


from datetime import datetime

def write_audit_log(admin_id, admin_username, action, target_user_id=None, details=""):
    """Write an entry to the admin audit log."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_logs (admin_id, admin_username, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (admin_id, admin_username, action, target_user_id, details, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


# ── BAN / UNBAN USER ─────────────────────────────────────────────
@app.route("/admin/ban_user/<int:id>", methods=['POST'])
@admin_required
def ban_user(id):
    if id == session.get('user_id'):
        return jsonify({"success": False, "error": "You cannot ban yourself."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    db.execute("UPDATE users SET banned = 1 WHERE id = ?", (id,))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "ban_user", id,
                    f"Banned user: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"User '{user['username']}' has been banned."})


@app.route("/admin/unban_user/<int:id>", methods=['POST'])
@admin_required
def unban_user(id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    db.execute("UPDATE users SET banned = 0 WHERE id = ?", (id,))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "unban_user", id,
                    f"Unbanned user: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"User '{user['username']}' has been unbanned."})


# ── PROMOTE USER TO ADMIN ────────────────────────────────────────
@app.route("/admin/promote_user/<int:id>", methods=['POST'])
@admin_required
def promote_user(id):
    if id == session.get('user_id'):
        return jsonify({"success": False, "error": "You are already an admin."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404
    if user['role'] == 'admin':
        return jsonify({"success": False, "error": "User is already an admin."}), 400

    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (id,))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "promote_user", id,
                    f"Promoted user to admin: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"User '{user['username']}' has been promoted to admin."})


# ── DEMOTE ADMIN TO USER ─────────────────────────────────────────
@app.route("/admin/demote_user/<int:id>", methods=['POST'])
@admin_required
def demote_user(id):
    if id == session.get('user_id'):
        return jsonify({"success": False, "error": "You cannot demote yourself."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404
    if user['role'] != 'admin':
        return jsonify({"success": False, "error": "User is not an admin."}), 400

    db.execute("UPDATE users SET role = 'user' WHERE id = ?", (id,))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "demote_user", id,
                    f"Demoted admin to user: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"User '{user['username']}' has been demoted to regular user."})


# ── EDIT USER (username / email) ─────────────────────────────────
@app.route("/admin/edit_user/<int:id>", methods=['POST'])
@admin_required
def edit_user(id):
    data = request.get_json()
    new_username = data.get('username', '').strip()
    new_email = data.get('email', '').strip()
    new_password = data.get('password', '').strip()

    if not new_username or not new_email:
        return jsonify({"success": False, "error": "Username and email are required."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    # Check duplicates (excluding self)
    dup = db.execute(
        "SELECT id FROM users WHERE (email = ? OR username = ?) AND id != ?",
        (new_email, new_username, id)
    ).fetchone()
    if dup:
        return jsonify({"success": False, "error": "Email or username already in use."}), 409

    old_username = user['username']
    if new_password:
        db.execute(
            "UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?",
            (new_username, new_email, generate_password_hash(new_password), id)
        )
    else:
        db.execute(
            "UPDATE users SET username = ?, email = ? WHERE id = ?",
            (new_username, new_email, id)
        )
    db.commit()

    write_audit_log(session['user_id'], session['username'], "edit_user", id,
                    f"Edited user: {old_username} → {new_username} ({new_email})"
                    + (" [password reset]" if new_password else ""))
    return jsonify({"success": True, "message": f"User '{new_username}' updated successfully."})


# ── DELETE USER (JSON response version for AJAX) ─────────────────
@app.route("/admin/delete_user_ajax/<int:id>", methods=['POST'])
@admin_required
def delete_user_ajax(id):
    if id == session.get('user_id'):
        return jsonify({"success": False, "error": "You cannot delete yourself."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    db.execute("DELETE FROM users WHERE id = ?", (id,))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "delete_user", id,
                    f"Deleted user: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"User '{user['username']}' deleted."})


# ── AUDIT LOG VIEWER ─────────────────────────────────────────────
@app.route("/admin/audit_logs")
@admin_required
def admin_audit_logs():
    db = get_db()
    rows = db.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC").fetchall()
    return jsonify({"logs": [dict(r) for r in rows]})


# ── RESET USER PASSWORD ───────────────────────────────────────────
@app.route("/admin/reset_password/<int:id>", methods=['POST'])
@admin_required
def reset_password(id):
    data = request.get_json()
    new_password = data.get('password', '').strip()

    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    db.execute("UPDATE users SET password = ? WHERE id = ?",
               (generate_password_hash(new_password), id))
    db.commit()

    write_audit_log(session['user_id'], session['username'], "reset_password", id,
                    f"Reset password for: {user['username']} ({user['email']})")
    return jsonify({"success": True, "message": f"Password for '{user['username']}' has been reset."})

if __name__ == "__main__":
    # Disable debug=True for production
    app.run(debug=os.environ.get("FLASK_DEBUG", "False").lower() == "true")