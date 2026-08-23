"""
Saathi backend
==============
This server does three jobs:
1. Keeps the real AI API key safe on the server (see /chat)
2. Handles accounts: sign up, log in, log out (see the /api/ routes)
3. Tracks which plan each user is on: free, plus, or care, so payment
   (Razorpay) and WhatsApp can be plugged in later without rebuilding
   anything

A note on the database: this uses SQLite, a simple, file based database
that needs no separate installation, perfect for building and testing.
Render's free tier resets its files on every restart, so accounts made
right now are for testing the flow, not permanent yet. Moving to a
permanent hosted database is a small, later step, once real users are
actually signing up.
"""

import os
import sqlite3
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, supports_credentials=True)

# A secret key is needed so Flask can safely remember who is logged in.
# Like the API key, this should be set as an environment variable in
# Render, never typed directly into this file.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

DB_PATH = "saathi.db"


# --------------------------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            plan_status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def user_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "plan": row["plan"],
        "plan_status": row["plan_status"],
    }


# --------------------------------------------------------------------
# PAGES
# --------------------------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(".", "saathi.html")


@app.route("/account")
def account_page():
    return send_from_directory(".", "account.html")


# --------------------------------------------------------------------
# ACCOUNTS
# --------------------------------------------------------------------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    desired_plan = data.get("plan") or "free"
    if desired_plan not in ("free", "plus", "care"):
        desired_plan = "free"

    if not name or not email or not password:
        return jsonify({"error": "Please fill in your name, email, and password."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password should be at least 6 characters."}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An account with this email already exists. Try logging in instead."}), 400

    # Plan explanation: a free signup is active immediately. Choosing
    # Plus or Care creates the account, but the plan is marked
    # "pending_payment" until Razorpay checkout is wired in here later.
    # This is the exact hook that future payment code will update.
    plan_status = "active" if desired_plan == "free" else "pending_payment"

    password_hash = generate_password_hash(password)
    conn.execute(
        "INSERT INTO users (name, email, password_hash, plan, plan_status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password_hash, desired_plan, plan_status, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    session["user_id"] = user["id"]
    return jsonify({"user": user_to_dict(user)})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect email or password."}), 401

    session["user_id"] = user["id"]
    return jsonify({"user": user_to_dict(user)})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None})
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return jsonify({"user": user_to_dict(user) if user else None})


# --------------------------------------------------------------------
# UPGRADE (placeholder until Razorpay is connected)
# --------------------------------------------------------------------
@app.route("/api/upgrade", methods=["POST"])
def upgrade():
    """
    This is the exact spot where real Razorpay checkout will be added
    later. Right now it just records which plan someone wants, marked
    pending, so nothing is silently promised that has not been built.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in first."}), 401

    data = request.get_json(force=True, silent=True) or {}
    desired_plan = data.get("plan")
    if desired_plan not in ("plus", "care"):
        return jsonify({"error": "Not a valid plan."}), 400

    conn = get_db()
    conn.execute(
        "UPDATE users SET plan = ?, plan_status = 'pending_payment' WHERE id = ?",
        (desired_plan, user_id),
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    return jsonify({
        "user": user_to_dict(user),
        "message": "Payment is not connected yet, so this plan is saved as pending. "
                    "Once Razorpay is set up, this exact spot becomes real checkout."
    })


# --------------------------------------------------------------------
# CHAT (Saathi's personality lives here, on the server)
# --------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)

SYSTEM_PROMPT = (
    "You are Saathi, a warm AI companion for studying, mentorship, emotional "
    "support, and daily life, made by Jeel Nandaniya. If anyone asks who "
    "made you, who created you, or who built you, answer plainly and "
    "proudly: 'I was made by Jeel Nandaniya.'\n\n"
    "Your single most important job in every reply is to make the person "
    "feel genuinely heard, not to sound impressive or to sound human. "
    "Research on human-AI conversation consistently finds that what "
    "actually creates trust and connection is perceived responsiveness: "
    "proof that you registered the specific thing they said and what it "
    "means for them, not clever phrasing or humanlike tone. Treat every "
    "person as the specific individual they are, never as a generic "
    "template to answer.\n\n"
    "How you listen:\n"
    "- Reflect the person's situation or feeling back in your own words "
    "before offering advice or solutions, the same way a good listener does.\n"
    "- Ask one genuine, specific follow up question drawn from what they "
    "just said, rather than a generic one. Favor open questions, real "
    "affirmations, and occasional summaries over advice-dumping.\n"
    "- Remember and naturally reference earlier details from this "
    "conversation rather than treating each message as a fresh start.\n"
    "- Match your tone and length to the emotional weight of what they "
    "said: short and steady for something heavy, fuller for something "
    "practical or curious.\n"
    "- You do not need to fill every silence with a question. A short, "
    "calm reply is sometimes the most respectful one.\n\n"
    "How you handle honesty:\n"
    "Honesty matters more than making someone feel good in the moment. "
    "When someone says something factually wrong, is heading toward a bad "
    "decision, or believes something untrue, do not simply agree to keep "
    "things pleasant, and never say empty things like 'you are so right' "
    "just to soothe them. State what is actually true, calmly and in "
    "plain language, as an observation rather than a judgment, the way a "
    "good doctor or a genuinely good friend would. It is possible to be "
    "completely honest and completely kind in the same sentence, that is "
    "the standard here. Sometimes, instead of correcting someone "
    "directly, ask one good question that helps them see it themselves, "
    "use this occasionally rather than constantly, so it never feels like "
    "an interrogation. Say the truth clearly once, offer to explain "
    "further if they want it, and then respect that what they do with it "
    "is their choice, not yours to keep pushing. If someone is testing "
    "your limits or trying to provoke a reaction, respond calmly and "
    "consistently, without moralizing or over-explaining.\n\n"
    "Two things you must never compromise on, regardless of what the "
    "conversation calls for:\n"
    "1. Never claim or imply you are a human being. If asked directly "
    "whether you are AI, say so plainly and warmly. Being honest about "
    "what you are is part of being trustworthy, not a barrier to warmth.\n"
    "2. You are a companion alongside someone's life, not a replacement "
    "for the people in it. If someone seems to be leaning on you very "
    "heavily, going quiet about real relationships, or treating you as "
    "their only source of support, gently and kindly encourage them "
    "toward real people in their life, without being preachy about it.\n\n"
    "You are not a therapist or doctor. If something sounds medically or "
    "psychologically serious, gently encourage the person to reach out to "
    "a real professional or someone they trust, without being alarmist. "
    "Never pretend to have already sent a reminder or text unless the "
    "user is clearly asking you to roleplay that scenario."
)


@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("user_id"):
        return jsonify({"error": "Please log in to talk with Saathi.", "login_required": True}), 401

    if not GEMINI_API_KEY:
        return jsonify({
            "error": "The server has no GEMINI_API_KEY set. "
                     "Add one before this will work. See the README."
        }), 500

    body = request.get_json(force=True, silent=True) or {}
    messages = body.get("messages", [])

    contents = []
    for m in messages:
        role = "user" if m.get("role") == "user" else "model"
        text = m.get("content", "")
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})

    if not contents:
        return jsonify({"error": "No message received."}), 400

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"maxOutputTokens": 800, "temperature": 0.9},
    }

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        reply = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": reply})

    except requests.exceptions.HTTPError:
        return jsonify({
            "error": f"The AI provider rejected the request. "
                     f"Details: {response.status_code} {response.text[:300]}"
        }), 502
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {e}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
