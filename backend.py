import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import random
import string
import hashlib
import time

# 1. Initialize Firebase
# Using environment variable for the key path makes it easier to manage on Render
service_key_path = os.environ.get("FIREBASE_SERVICE_KEY", "./nuture-7aafa-firebase-adminsdk-fbsvc-326796a2cd.json")

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_key_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(">>> Success: Connected to Firebase Firestore")
except Exception as e:
    print(f">>>> Error: Could not find or load Firebase key at {service_key_path}")
    print(f">>> Details: {e}")

app = Flask(__name__)

# 2. Optimized CORS
# Replace 'https://nuture-final.vercel.app' with your actual Vercel project URL
allowed_origins = [
    "https://nuture-final.vercel.app", 
    "http://localhost:5173"
]

CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# --- HELPERS ---

def generate_ref_code():
    return 'NUTM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def generate_blockchain_proof(uid, filename):
    timestamp = str(time.time())
    data_to_hash = f"{uid}-{filename}-{timestamp}"
    cid = f"Qm{hashlib.sha256(data_to_hash.encode()).hexdigest()[:16]}..."
    tx_hash = f"0x{hashlib.md5(data_to_hash.encode()).hexdigest()}"
    return cid, tx_hash

def safe_iso_date(obj):
    """Helper to convert Firestore timestamps or strings to ISO format safely."""
    if obj is None: return None
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    # Handle Firestore Timestamp objects
    if hasattr(obj, 'to_datetime'):
        return obj.to_datetime().isoformat()
    return str(obj)

# --- ROUTES ---

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online", 
        "database": "connected" if firebase_admin._apps else "error",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    try:
        user = auth.create_user(
            email=data['email'], 
            password=data['password'], 
            display_name=data['fullName']
        )
        db.collection('users').document(user.uid).set({
            'fullName': data['fullName'],
            'email': data['email'],
            'nutmId': data.get('nutmId', 'NUTM-PENDING'),
            'referralCode': generate_ref_code(),
            'points': 0, 
            'streak': 0, 
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        return jsonify({"message": "User created", "uid": user.uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    try:
        user = auth.get_user_by_email(data.get('email'))
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        return jsonify({
            "uid": user.uid, 
            "email": user.email, 
            "fullName": user_data.get('fullName', user.display_name)
        }), 200
    except Exception as e:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/subscribe', methods=['POST'])
def subscribe_user():
    data = request.json
    uid = data.get('uid')
    try:
        user_ref = db.collection('users').document(uid)
        subscription_data = {
            'planId': data.get('planId'), 
            'status': 'active', 
            'startDate': firestore.SERVER_TIMESTAMP, 
            'paymentReference': data.get('reference')
        }
        user_ref.set({'subscription': subscription_data, 'points': firestore.Increment(100)}, merge=True)
        return jsonify({
            "message": "Active", 
            "subscription": {**subscription_data, 'startDate': datetime.now().isoformat()}
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-subscription/<uid>', methods=['GET'])
def get_subscription(uid):
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Fetch approved claims to calculate remaining coverage
            claims = db.collection('claims').where('userId', '==', uid).where('status', '==', 'approved').stream()
            total_used = sum([doc.to_dict().get('amount', 0) for doc in claims])
            return jsonify({
                "subscription": user_data.get('subscription'), 
                "coverageUsed": total_used
            }), 200
        return jsonify({"error": "User not found"}), 404
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
            'date': firestore.SERVER_TIMESTAMP, 
            'receipts': data.get('receipts', [])
        }
        claim_ref.set(claim_data)
        # Bonus: Increment user streak for being proactive about health
        db.collection('users').document(data.get('uid')).update({'streak': firestore.Increment(1)})
        return jsonify({"message": "Success", "claimId": claim_ref.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/get-claims/<uid>', methods=['GET'])
def get_user_claims(uid):
    try:
        docs = db.collection('claims').where('userId', '==', uid).stream()
        claims_list = []
        for doc in docs:
            c = doc.to_dict()
            c['date'] = safe_iso_date(c.get('date'))
            claims_list.append(c)
        # Sort by most recent
        claims_list.sort(key=lambda x: x.get('date', '') or '', reverse=True)
        return jsonify(claims_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vault/add', methods=['POST'])
def add_vault_record():
    data = request.json
    uid = data.get('uid')
    try:
        cid, tx_hash = generate_blockchain_proof(uid, data.get('name'))
        doc_ref = db.collection('vault').document()
        record = {
            'id': doc_ref.id, 
            'userId': uid, 
            'name': data.get('name'), 
            'type': data.get('type'), 
            'size': data.get('size'), 
            'uploadDate': datetime.now().isoformat(), 
            'isEncrypted': True, 
            'cid': cid, 
            'txHash': tx_hash
        }
        doc_ref.set(record)
        return jsonify(record), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/vault/get/<uid>', methods=['GET'])
def get_vault(uid):
    try:
        docs = db.collection('vault').where('userId', '==', uid).stream()
        records = [doc.to_dict() for doc in docs]
        records.sort(key=lambda x: x.get('uploadDate', ''), reverse=True)
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RENDER DEPLOYMENT CONFIGURATION ---

if __name__ == '__main__':
    # Render assigns a port via environment variable. 
    port = int(os.environ.get("PORT", 5000))
    print(f">>> Nuture Backend active on port {port}")
    app.run(host='0.0.0.0', port=port)
