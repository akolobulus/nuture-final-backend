import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import json
import random
import string
import hashlib
import time
import uuid

# 1. Initialize Firebase (Firestore only)
service_account_env = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

try:
    if not firebase_admin._apps:
        if service_account_env:
            cert_dict = json.loads(service_account_env)
            cred = credentials.Certificate(cert_dict)
        else:
            cred = credentials.Certificate("./nuture-7aafa-firebase-adminsdk-fbsvc-326796a2cd.json")
            
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(">>> Success: Connected to Firebase Firestore (Auth Check Disabled)")
except Exception as e:
    print(f">>>> Fatal Error during Firebase Init: {e}")

app = Flask(__name__)

# 2. Optimized CORS
allowed_origins = ["https://nuture-me.vercel.app", "http://localhost:5173"]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# --- HELPERS ---

def generate_ref_code():
    return 'NUTM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def safe_iso_date(obj):
    if obj is None: return None
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    if hasattr(obj, 'to_datetime'): return obj.to_datetime().isoformat()
    return str(obj)

# --- BYPASS ROUTES ---

@app.route('/api/signup', methods=['POST'])
def signup():
    """Bypasses Firebase Auth and creates a user record directly in Firestore."""
    data = request.json
    try:
        email = data['email']
        # Generate a unique ID manually since we aren't using Firebase Auth
        user_uid = str(uuid.uuid4())
        
        user_data = {
            'uid': user_uid,
            'fullName': data['fullName'],
            'email': email,
            'password': data['password'], # Storing plain for prototype bypass
            'nutmId': data.get('nutmId', 'NUTM-2026-001'),
            'referralCode': generate_ref_code(),
            'points': 0, 
            'streak': 0, 
            'createdAt': firestore.SERVER_TIMESTAMP,
            'subscription': None
        }
        
        db.collection('users').document(user_uid).set(user_data)
        return jsonify({"message": "User created", "uid": user_uid}), 201
    except Exception as e:
        print(f"!!! SIGNUP ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    """Bypasses Firebase Auth by checking the password field in Firestore."""
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        
        # Search Firestore for the user
        users_ref = db.collection('users').where('email', '==', email).limit(1).stream()
        user_list = [doc.to_dict() for doc in users_ref]
        
        if not user_list:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_list[0]
        
        # Simple password check
        if user_data.get('password') == password:
            return jsonify({
                "uid": user_data['uid'], 
                "email": user_data['email'], 
                "fullName": user_data['fullName']
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- REMAINING ROUTES (NO CHANGES NEEDED) ---

@app.route('/api/subscribe', methods=['POST'])
def subscribe_user():
    data = request.json
    uid = data.get('uid')
    try:
        user_ref = db.collection('users').document(uid)
        subscription_data = {
            'planId': data.get('planId'), 
            'status': 'active', 
            'startDate': datetime.now().isoformat(), 
            'paymentReference': data.get('reference')
        }
        user_ref.set({'subscription': subscription_data, 'points': firestore.Increment(100)}, merge=True)
        return jsonify({"message": "Active", "subscription": subscription_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-subscription/<uid>', methods=['GET'])
def get_subscription(uid):
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return jsonify({
                "subscription": user_data.get('subscription'), 
                "coverageUsed": 0 # Placeholder
            }), 200
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-claim', methods=['POST'])
def submit_claim():
    data = request.json
    try:
        claim_ref = db.collection('claims').document()
        claim_data = {
            'id': claim_ref.id, 
            'userId': data.get('uid'), 
            'amount': float(data['amount']), 
            'description': data['description'], 
            'category': data['category'], 
            'status': 'pending', 
            'date': datetime.now().isoformat()
        }
        claim_ref.set(claim_data)
        return jsonify({"message": "Success", "claimId": claim_ref.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- START SERVER ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
