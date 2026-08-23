"""
Saathi backend
==============
This tiny server has exactly one job: keep the real AI API key safe on
the server, and talk to the AI model on Saathi's behalf.

Why this file needs to exist at all:
A webpage's code (HTML/CSS/JS) is fully visible to anyone who opens
"view source" in their browser. If we put a real API key inside
saathi.html, anyone visiting the site could copy it and use it as
their own, and it could rack up cost or get shut down within a day.
So instead, the browser talks to THIS Python server, and only this
server, running privately, ever touches the real key.

This uses Google's Gemini API, because it has a genuinely free tier
(no credit card required) that is strong enough for a real chatbot.
"""

import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)  # allows the browser to call this server from the same site

# --------------------------------------------------------------------
# The API key is read from an environment variable, never typed
# directly into this file. This is the standard, safe way to handle
# secrets: keep them OUT of your code, so they never get accidentally
# shared, uploaded, or shown on screen.
#
# To set it locally before running this file:
#   Windows (PowerShell):  $env:GEMINI_API_KEY = "your-key-here"
#   Mac / Linux:           export GEMINI_API_KEY="your-key-here"
# --------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)

# Saathi's personality lives here, on the server, not in the browser code.
SYSTEM_PROMPT = (
    "You are Saathi, a warm, emotionally intelligent AI companion. "
    "You help with studying, mentorship, emotional support, and daily "
    "life guidance. You are caring but never fake or overly sweet, you "
    "speak like a genuinely thoughtful friend, not a corporate "
    "assistant. Keep replies concise and conversational unless the "
    "person is asking for deep help with a study topic. You are not a "
    "therapist or doctor. If something sounds medically or "
    "psychologically serious, gently encourage the person to reach out "
    "to a real professional or someone they trust, without being "
    "alarmist. Never pretend to have already sent a reminder or text "
    "unless the user is clearly asking you to roleplay that scenario."
)


@app.route("/")
def home():
    """Serves the website itself, so the site and the API live together."""
    return send_from_directory(".", "saathi.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Receives the conversation so far from the browser, sends it to
    Gemini along with Saathi's personality, and returns the reply.
    """
    if not GEMINI_API_KEY:
        return jsonify({
            "error": "The server has no GEMINI_API_KEY set. "
                     "Add one before this will work. See the README."
        }), 500

    body = request.get_json(force=True, silent=True) or {}
    messages = body.get("messages", [])

    # Gemini expects a slightly different shape than our frontend uses:
    # role "user" or "model" (not "assistant"), each with a list of "parts".
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
    # debug=True auto-reloads while you're building. Turn it off before
    # putting this on the real internet.
    app.run(host="0.0.0.0", port=port, debug=True)
