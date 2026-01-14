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
# Render looks for the .json file in the root directory.
# Ensure 'nuture-7aafa-firebase-adminsdk-fbsvc-326796a2cd.json' is in your GitHub repo.
service_key_path = os.environ.get("FIREBASE_SERVICE_KEY", "./nuture-7aafa-firebase-adminsdk-fbsvc-c9c5c31791")

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_key_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(">>> Success: Connected to Firebase Firestore (Project: nuture-7aafa)")
except Exception as e:
    print(f">>>> Fatal Error: Firebase initialization failed: {e}")

app = Flask(__name__)

# 2. CORS Configuration
# We explicitly allow your Vercel production URL and Localhost for development.
allowed_origins = [
    "https://nuture-me.vercel.app", 
    "http://localhost:5173"
]

CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# --- HELPERS ---

def generate_ref_code():
    """Generates a unique referral code for new users."""
    return 'NUTM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def generate_blockchain_proof(uid, filename):
    """Simulates an on-chain anchoring by hashing data and generating a mock TX Hash."""
    timestamp = str(time.time())
    data_to_hash = f"{uid}-{filename}-{timestamp}"
    cid = f"Qm{hashlib.sha256(data_to_hash.encode()).hexdigest()[:16]}..."
    tx_hash = f"0x{hashlib.md5(data_to_hash.encode()).hexdigest()}"
    return cid, tx_hash

def safe_iso_date(obj):
    """Safely converts Firestore Timestamps to ISO strings for JSON serialization."""
    if obj is None: return None
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    if hasattr(obj, 'to_datetime'):
        return obj.to_datetime().isoformat()
    return str(obj)

# --- API ROUTES ---

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
        # Create user in Firebase Authentication
        user = auth.create_user(
            email=data['email'], 
            password=data['password'], 
            display_name=data['fullName']
        )
        
        # Create user document in Firestore
        db.collection('users').document(user.uid).set({
            'fullName': data['fullName'],
            'email': data['email'],
            'nutmId': data.get('nutmId', 'NUTM-PENDING'),
            'referralCode': generate_ref_code(),
            'points': 0, 
            'streak': 0, 
            'createdAt': firestore.SERVER_TIMESTAMP,
            'subscription': None
        })
        
        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        print(f"!!! SIGNUP ERROR: {str(e)}") # Visible in Render Logs
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
        print(f"!!! LOGIN ERROR: {str(e)}")
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
            "message": "Subscription activated", 
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
            # Calculate total approved claims to determine usage
            claims = db.collection('claims').where('userId', '==', uid).where('status', '==', 'approved').stream()
            total_used = sum([doc.to_dict().get('amount', 0) for doc in claims])
            
            return jsonify({
                "subscription": user_data.get('subscription'), 
                "coverageUsed": total_used
            }), 200
        return jsonify({"error": "User profile not found"}), 404
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
        # Update user streak for engaging with the platform
        db.collection('users').document(data.get('uid')).update({'streak': firestore.Increment(1)})
        return jsonify({"message": "Claim submitted", "claimId": claim_ref.id}), 201
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
        
        # Sort by date (descending)
        claims_list.sort(key=lambda x: x.get('date', '') or '', reverse=True)
        return jsonify(claims_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vault/add', methods=['POST'])
def add_vault_record():
    data = request.json
    uid = data.get('uid')
    try:
        # Generate simulated Blockchain Proofs
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

@app.route('/api/get-referrals/<uid>', methods=['GET'])
def get_referrals(uid):
    try:
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_doc.to_dict()
        referrals = db.collection('referrals').where('referrerId', '==', uid).stream()
        
        return jsonify({
            "referralCode": user_data.get('referralCode'), 
            "referrals": [doc.to_dict() for doc in referrals]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SERVER ENTRY POINT ---

if __name__ == '__main__':
    # Render binds to the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
