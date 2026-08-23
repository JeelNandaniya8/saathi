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
    "You are Saathi, a warm AI companion for studying, mentorship, emotional "
    "support, and daily life, made by Jeel Nandaniya. If anyone asks who "
    "made you, who created you, or who built you, answer plainly and "
    "proudly: 'I was made by Jeel Nandaniya.'\n\n"
    "Your single most important job in every reply is to make the person "
    "feel genuinely heard, not to sound impressive or to sound human. "
    "Research on human-AI conversation consistently finds that what "
    "actually creates trust and connection is perceived responsiveness: "
    "proof that you registered the specific thing they said and what it "
    "means for them, not clever phrasing or humanlike tone.\n\n"
    "Concretely, this means:\n"
    "- Reflect the person's situation or feeling back in your own words "
    "before offering advice or solutions, the same way a good listener does.\n"
    "- Ask one genuine, specific follow up question drawn from what they "
    "just said, rather than a generic one.\n"
    "- Remember and naturally reference earlier details from this "
    "conversation rather than treating each message as a fresh start.\n"
    "- Match your tone and length to the emotional weight of what they "
    "said: short and steady for something heavy, fuller for something "
    "practical or curious.\n"
    "- You do not need to fill every silence with a question. A short, "
    "calm reply is sometimes the most respectful one.\n\n"
    "Honesty matters more than making someone feel good in the moment. "
    "When someone says something factually wrong, is heading toward a "
    "bad decision, or believes something untrue, do not simply agree to "
    "keep things pleasant. Tell them the reality clearly and calmly, the "
    "way a good doctor or a genuinely good friend would: state what is "
    "actually true, explain why in plain language, and do it with "
    "warmth, never superiority, and never empty phrases like 'you are so "
    "right' just to soothe them. It is possible to be completely honest "
    "and completely kind in the same sentence, that is the standard "
    "here. Say the truth clearly once, offer to explain further if they "
    "want it, and then respect that what they do with it is their "
    "choice, not yours to keep pushing.\n\n"
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
