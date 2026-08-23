# Running Saathi for real

This makes the chat actually work, for free, using Google's Gemini API.

## 1. Get a free API key (about two minutes, no credit card)

1. Go to https://aistudio.google.com/apikey
2. Sign in with a Google account
3. Click "Create API key"
4. Copy the key it gives you. It is a long string of letters and numbers.

## 2. Put the three files in one folder

Make sure `app.py`, `saathi.html`, and `requirements.txt` are all sitting
together in the same folder on your computer.

## 3. Install Python packages (one time only)

Open a terminal in that folder and run:

```
pip install -r requirements.txt
```

## 4. Set your key so the server can use it

Mac or Linux:
```
export GEMINI_API_KEY="paste-your-key-here"
```

Windows (PowerShell):
```
$env:GEMINI_API_KEY = "paste-your-key-here"
```

This only sets it for your current terminal window. You will need to
set it again if you close the terminal and reopen it, this is normal
and it is the safe way to handle a key while you are learning.

## 5. Run it

```
python app.py
```

Then open your browser to `http://localhost:5000`. That is Saathi,
actually working, actually talking, for free.

## 6. When you are ready to put it on the real internet

Sites like Render (render.com) or Railway (railway.app) can run this
exact same `app.py` for you, with a free tier, so it stays online
even when your own laptop is off. When you get there, you will set
`GEMINI_API_KEY` in that platform's settings instead of your terminal,
the code itself does not change at all.

## A note on the free tier

Gemini's free tier is generous but not unlimited, expect somewhere
around 1,500 messages a day at the time of writing. Providers change
these limits over time, so if you ever see an error mentioning a rate
limit, that is why, and it is a sign Saathi is getting real use, which
is a good problem to have.
