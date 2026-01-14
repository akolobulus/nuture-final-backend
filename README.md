# Nuture: Secure Student Health Insurance & Digital Vault

**Nuture** is a decentralized health insurance platform specifically designed for NUTM students. It combines modern fintech payment processing, a cloud-based claims system, and a blockchain-simulated digital health vault to provide students with transparent and immediate medical coverage.


##  Key Features

### 1. **Automated Onboarding & Auth**

* **Firebase Authentication:** Secure sign-up and sign-in flow.
* **Student Profiles:** Automatic generation of unique NUTM IDs and referral codes upon registration.

### 2. **Seamless Policy Management**

* **Plan Selection:** Diverse health plans (Basic, Premium, Elite) tailored for student budgets.
* **Paystack Integration:** Real-time payment processing for instant policy activation.
* **Smart Dashboard:** Visual tracking of coverage limits, monthly premiums, and "On-Chain Secured" status.

### 3. **Smart Claims Tracking**

* **Digital Submission:** Students can submit medical expenses with descriptions, categories, and file attachments (receipts/prescriptions).
* **Real-time Tracking:** Monitor the status of claims (Pending, Approved, Rejected) directly from the portal.
* **Automated Ledger:** Claims are stored in Firestore and linked to the student's coverage utilization bar.

### 4. **Blockchain Health Vault**

* **Cryptographic Anchoring:** Every uploaded medical record is "minted" with a Content Identifier (CID) and a Transaction Hash using SHA-256 hashing.
* **Decentralized Simulation:** Records are simulated as being stored on a distributed ledger to ensure data integrity and immutability.
* **Next of Kin Emergency Access:** A "3-of-5" multi-sig simulation that allows trusted contacts to unlock medical records in case of an emergency.

### 5. **Referral & Gamification**

* **Referral Program:** Students earn ₦500 for every peer they invite who activates a plan.
* **Points & Streaks:** Automated point increments for policy renewals and successful claim submissions.

---

##  Backend Architecture (Python & Flask)

The backend is built with **Python 3.10+** and **Flask**, acting as the bridge between the React frontend and Firebase services.

### Core Python Technologies:

* **Firebase Admin SDK:** For deep integration with Firestore (Database) and Firebase Auth.
* **Flask-CORS:** To handle secure cross-origin requests from the React frontend.
* **Hashlib & Time:** Used to simulate blockchain mechanics (generating hashes and CIDs).
* **Datetime:** To ensure ISO-standardized time tracking across global servers.

### How Python is used:

* **Upsert Logic:** Uses `.set(..., merge=True)` to prevent 404 errors during user profile updates.
* **Data Serialization:** Python handles the conversion of complex Firebase `Sentinel` objects (Server Timestamps) into JSON-serializable strings that React can display.
* **Server-Side Sorting:** To bypass the need for manual Firestore Indexing during the development phase, the backend performs high-performance Python sorting on lists of claims and vault records.
* **Blockchain Simulation:** Python functions generate unique 64-character SHA-256 strings to verify that a document has been "anchored" to the chain.

---

## Installation & Setup

### Prerequisites

* Node.js (v16+)
* Python (v3.9+)
* Firebase Project (Service Account JSON key)

### 1. Backend Setup

```bash
cd backend
pip install flask flask-cors firebase-admin
# Place your firebase-adminsdk.json in this folder
python backend.py

```

### 2. Frontend Setup

```bash
# In the root folder
npm install
npm run dev

```

---

## 📂 Project Structure

```text
├── src/
│   ├── components/       # Reusable UI (Buttons, Icons)
│   ├── pages/            # Dashboard, Vault, Referrals, Claims
│   ├── types/            # TypeScript interfaces for data safety
│   └── lib/              # Mock data and configurations
├── backend/
│   └── backend.py        # Flask Server & Firebase Logic
└── public/               # Static assets

```

---

## Security & Privacy

* **Data Encrypted at Rest:** All medical records are flagged as encrypted within Firestore.
* **Authenticated Requests:** API endpoints are designed to require a valid Firebase `uid`.
* **Next of Kin Protocol:** Private records remain locked unless a majority threshold of trusted contacts provides authorization.

**Nuture** is more than just insurance; it is a digital safety net for the NUTM community.


# Nuture Backend

This directory contains the complete Python backend for the Nuture application, built with Flask and SQLAlchemy.

## Features

- **User Authentication**: Secure sign-up and sign-in using JWT (JSON Web Tokens).
- **Database**: Uses SQLite for simplicity, making setup easy.
- **API Endpoints**: Provides all necessary endpoints for managing users, plans, subscriptions, claims, and referrals.
- **File Uploads**: Handles receipt uploads for claim submissions.
- **CORS Enabled**: Configured to allow requests from your frontend application.

## Setup and Installation

Follow these steps to get the backend server running locally.

### 1. Prerequisites

- Python 3.8+
- `pip` (Python package installer)
- `venv` (recommended for creating virtual environments)

### 2. Create a Virtual Environment

It's highly recommended to use a virtual environment to keep project dependencies isolated.

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment named 'venv'
python -m venv venv
```

### 3. Activate the Virtual Environment

- **On macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

- **On Windows:**
  ```bash
  .\\venv\\Scripts\\activate
  ```

Your command prompt should now be prefixed with `(venv)`.

### 4. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the `backend` directory by copying the example file.

```bash
cp .env.example .env
```

Now, open the `.env` file and change the `SECRET_KEY` to a long, random, and secret string. This key is crucial for securing user sessions.

```ini
# .env
SECRET_KEY='your-super-secret-and-long-random-string-here'
```

### 6. Run the Backend Server

Once everything is set up, you can start the Flask server.

```bash
flask run
```

The server will start, and you should see output similar to this:

```
 * Serving Flask app 'backend'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

The backend is now running and ready to accept requests at `http://127.0.0.1:5000`.

When you run the server for the first time, it will automatically create a `nuture.db` file (the SQLite database) and an `uploads` directory in the `backend` folder.

## Next Steps

With the backend running, you can now modify your frontend application to make API calls to `http://127.0.0.1:5000` instead of using `localStorage`.
