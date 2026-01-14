import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import json
import base64
import random
import string
import uuid

# --- 1. FIREBASE INITIALIZATION (BASE64 SECURE) ---
# This method prevents the "Invalid JWT Signature" error caused by Render's handling of JSON strings.
service_account_base64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

try:
    if not firebase_admin._apps:
        if service_account_base64:
            # Decode the base64 string back into the original clean JSON
            decoded_bytes = base64.b64decode(service_account_base64)
            decoded_str = decoded_bytes.decode('utf-8')
            cert_dict = json.loads(decoded_str)
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred)
            print(">>> Success: Initialized Firebase via Base64 Decoding")
        else:
            # Fallback for local development if the file exists
            cred = credentials.Certificate("./nuture-7aafa-firebase-adminsdk-fbsvc-326796a2cd.json")
            firebase_admin.initialize_app(cred)
            print(">>> Success: Initialized Firebase via Local File")
            
    db = firestore.client()
    print(">>> Success: Connected to Firestore (Soft-Auth Mode)")
except Exception as e:
    print(f">>>> Fatal Error during Firebase Init: {e}")

app = Flask(__name__)

# --- 2. CORS CONFIGURATION ---
allowed_origins = [
    "https://nuture-me.vercel.app", 
    "http://localhost:5173"
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# --- HELPERS ---

def generate_ref_code():
    return 'NUTM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def safe_iso_date(obj):
    if obj is None: return None
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    if hasattr(obj, 'to_datetime'): return obj.to_datetime().isoformat()
    return str(obj)

# --- 3. SOFT-AUTH ROUTES (BYPASSING FIREBASE AUTH) ---

@app.route('/api/signup', methods=['POST'])
def signup():
    """Creates a user record directly in Firestore, bypassing Google Auth handshake."""
    data = request.json
    try:
        email = data['email']
        # Check if user already exists
        existing = db.collection('users').where('email', '==', email).limit(1).get()
        if len(existing) > 0:
            return jsonify({"error": "Email already registered"}), 400

        user_uid = str(uuid.uuid4())
        user_data = {
            'uid': user_uid,
            'fullName': data['fullName'],
            'email': email,
            'password': data['password'], # Store plain text for prototype simplicity
            'nutmId': data.get('nutmId', 'NUTM-2026-STUDENT'),
            'referralCode': generate_ref_code(),
            'points': 50, # Welcome bonus
            'streak': 0, 
            'createdAt': firestore.SERVER_TIMESTAMP,
            'subscription': None
        }
        
        db.collection('users').document(user_uid).set(user_data)
        return jsonify({"message": "User created", "uid": user_uid}), 201
    except Exception as e:
        print(f"!!! SIGNUP ERROR: {str(e)}")
        return jsonify({"error": "Signup failed. Please check backend logs."}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Simple Firestore-based login lookup."""
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        
        users = db.collection('users').where('email', '==', email).limit(1).stream()
        user_list = [doc.to_dict() for doc in users]
        
        if not user_list:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_list[0]
        if user_data.get('password') == password:
            return jsonify({
                "uid": user_data['uid'], 
                "email": user_data['email'], 
                "fullName": user_data['fullName']
            }), 200
        else:
            return jsonify({"error": "Incorrect password"}), 401
    except Exception as e:
        print(f"!!! LOGIN ERROR: {str(e)}")
        return jsonify({"error": "Server error during login"}), 500

# --- 4. DASHBOARD & DATA ROUTES ---

@app.route('/api/get-subscription/<uid>', methods=['GET'])
def get_subscription(uid):
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # In soft-auth, we calculate approved claims sum here
            claims = db.collection('claims').where('userId', '==', uid).where('status', '==', 'approved').stream()
            total_used = sum([doc.to_dict().get('amount', 0) for doc in claims])
            
            return jsonify({
                "subscription": user_data.get('subscription'), 
                "coverageUsed": total_used
            }), 200
        return jsonify({"error": "User profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        user_ref.update({
            'subscription': subscription_data, 
            'points': firestore.Increment(100)
        })
        return jsonify({"message": "Active", "subscription": subscription_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-claims/<uid>', methods=['GET'])
def get_user_claims(uid):
    try:
        docs = db.collection('claims').where('userId', '==', uid).stream()
        claims_list = [doc.to_dict() for doc in docs]
        return jsonify(claims_list), 200
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
        return jsonify({"message": "Claim saved", "claimId": claim_ref.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- 5. VAULT ROUTES ---

@app.route('/api/vault/add', methods=['POST'])
def add_vault_record():
    data = request.json
    try:
        doc_ref = db.collection('vault').document()
        record = {
            'id': doc_ref.id, 
            'userId': data.get('uid'), 
            'name': data.get('name'), 
            'type': data.get('type'), 
            'size': data.get('size'), 
            'uploadDate': datetime.now().isoformat(), 
            'isEncrypted': True,
            'cid': f"Qm{uuid.uuid4().hex[:16]}", # Mock IPFS CID
            'txHash': f"0x{uuid.uuid4().hex}"     # Mock Blockchain Hash
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
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 6. SERVER ENTRY ---

if __name__ == '__main__':
    # Default Render port is 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
