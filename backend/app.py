from flask import Flask, jsonify
from flask_cors import CORS  # Import CORS
import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import spacy
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})  # Enable CORS for specific origin

# Setup nltk and spacy
nltk.download('vader_lexicon')
nltk.download('punkt')
nlp = spacy.load('en_core_web_sm')
sentiment_analyzer = SentimentIntensityAnalyzer()

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
creds = None

# Load credentials
def load_credentials():
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

load_credentials()

# Gmail API service
try:
    service = build('gmail', 'v1', credentials=creds)
except Exception as e:
    logging.error(f"Failed to create Gmail service: {e}")
    service = None

def fetch_emails():
    if not service:
        return []

    try:
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])
        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            for part in msg_data['payload'].get('parts', []):
                if part['mimeType'] == 'text/plain':
                    body_data = part['body']['data']
                    email_text = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    emails.append(email_text)
        return emails
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []

def analyze_email(email):
    try:
        doc = nlp(email)
        sentiment = sentiment_analyzer.polarity_scores(email)
        keywords = [token.text for token in doc if not token.is_stop and not token.is_punct]
        return {
            'email': email,
            'sentiment': sentiment,
            'keywords': keywords
        }
    except Exception as e:
        logging.error(f"Error analyzing email: {e}")
        return {
            'email': email,
            'sentiment': {},
            'keywords': []
        }

@app.route('/emails', methods=['GET'])
def get_emails():
    emails = fetch_emails()
    analyzed_emails = [analyze_email(email) for email in emails]
    return jsonify(analyzed_emails)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
