import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json # Add this import
from datetime import datetime

# 1. Initialize Firebase using the Environment Variable
service_account_info = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

try:
    if not firebase_admin._apps:
        if service_account_info:
            # Load from Render Environment Variable
            cred_dict = json.loads(service_account_info)
            cred = credentials.Certificate(cred_dict)
            print(">>> Initializing Firebase from Environment Variable")
        else:
            # Fallback for local development
            cred = credentials.Certificate("./nuture-7aafa-firebase-adminsdk-fbsvc-326796a2cd.json")
            print(">>> Initializing Firebase from Local JSON File")
            
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print(">>> Success: Connected to Firebase Firestore")
except Exception as e:
    print(f">>>> ERROR: Firebase Initialization Failed: {e}")

# ... rest of your Flask app code ...
