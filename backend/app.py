from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import spacy
import logging
import os
import base64
from datetime import datetime, timezone
from models import db, Email, DeletedEmail
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///your-local-database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Setup nltk and spacy
nltk.download('vader_lexicon')
nltk.download('punkt')
nlp = spacy.load('en_core_web_sm')
sentiment_analyzer = SentimentIntensityAnalyzer()

# Google API setup
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

creds = None

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def load_credentials():
    try:
        creds = flow.run_local_server(port=8080)
        # Add additional code to handle the credentials if necessary
    except AttributeError as e:
        logging.error("Failed to retrieve URI. Make sure all OAuth configurations are set correctly.")
        logging.error(f"Error: {str(e)}")
        raise e

if __name__ == "__main__":
    load_credentials()


load_credentials()

# Gmail API service
try:
    service = build('gmail', 'v1', credentials=creds)
except Exception as e:
    logging.error(f"Failed to create Gmail service: {e}")
    service = None

# Fetch emails
def fetch_emails():
    emails = []
    next_page_token = None
    try:
        deleted_ids = {email.id for email in DeletedEmail.query.all()}

        while True:
            results = service.users().messages().list(
                userId='me', 
                labelIds=['INBOX'], 
                maxResults=10,
                pageToken=next_page_token
            ).execute()

            messages = results.get('messages', [])
            next_page_token = results.get('nextPageToken')

            for msg in messages:
                msg_id = msg['id']

                # Skip if email was previously deleted
                if msg_id in deleted_ids:
                    continue

                msg_data = service.users().messages().get(userId='me', id=msg_id).execute()

                msg_headers = {header['name']: header['value'] for header in msg_data['payload']['headers']}
                subject = msg_headers.get('Subject', 'No Subject')
                sender = msg_headers.get('From', 'Unknown Sender')
                date = msg_headers.get('Date', '')

                # Handle date formats and make it timezone-aware
                if 'GMT' in date:
                    date = date.replace(' GMT', '')
                    email_date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S')
                    email_date = email_date.replace(tzinfo=timezone.utc)  # Make it timezone-aware
                else:
                    email_date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z')

                email_date_iso = email_date.isoformat()

                # Decode the email body
                body = ''
                if 'data' in msg_data['payload'].get('body', {}):
                    body_data = msg_data['payload']['body']['data']
                    body = base64.urlsafe_b64decode(body_data.encode('UTF-8')).decode('UTF-8')
                else:
                    parts = msg_data['payload'].get('parts', [])
                    for part in parts:
                        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data'].encode('UTF-8')).decode('UTF-8')
                            break

                # Add email to the list for sorting
                emails.append({
                    'id': msg_id,
                    'subject': subject,
                    'date': email_date,
                    'sender': sender,
                    'body': body,
                })

            if not next_page_token:
                break

        # Sort emails by date in descending order
        emails.sort(key=lambda x: x['date'], reverse=True)

        # Add sorted emails to the database
        for email in emails:
            if not Email.query.filter_by(id=email['id']).first():
                email_record = Email(
                    id=email['id'],
                    subject=email['subject'],
                    date=email['date'].isoformat(),
                    sender=email['sender'],
                    body=email['body'],
                    sentiment_pos=0.0,
                    sentiment_neg=0.0,
                    sentiment_neu=0.0,
                    keywords=""
                )
                db.session.add(email_record)

        db.session.commit()

    except Exception as e:
        logging.error(f"Failed to fetch emails: {e}")
    
    return emails

# Analyze email
def analyze_email(email):
    try:
        doc = nlp(email.body)
        sentiment = sentiment_analyzer.polarity_scores(email.body)
        keywords = [token.text for token in doc if not token.is_stop and not token.is_punct][:3]

        # Update sentiment and keywords in the database
        email.sentiment_pos = sentiment['pos']
        email.sentiment_neg = sentiment['neg']
        email.sentiment_neu = sentiment['neu']
        email.keywords = ','.join(keywords)
        db.session.commit()

        return {
            'id': email.id,
            'subject': email.subject,
            'date': email.date,
            'sender': email.sender,
            'body': email.body,
            'sentiment': sentiment,
            'keywords': keywords
        }
    except Exception as e:
        logging.error(f"Error analyzing email: {e}")
        return {
            'id': email.id,
            'subject': email.subject,
            'date': email.date,
            'sender': email.sender,
            'body': email.body,
            'sentiment': {},
            'keywords': []
        }

@app.route('/emails', methods=['GET'])
def get_emails():
    # Fetch latest emails and store them in the database
    fetched_emails = fetch_emails()

    # Analyze and return the emails sorted by date (newest first)
    analyzed_emails = [analyze_email(email) for email in Email.query.order_by(Email.date.desc()).all()]
    return jsonify(analyzed_emails)

@app.route('/emails/<email_id>', methods=['GET'])
def get_email(email_id):
    email = Email.query.get_or_404(email_id)
    analyzed_email = analyze_email(email)
    return jsonify(analyzed_email)

@app.route('/emails/delete', methods=['POST'])
def delete_emails():
    email_ids = request.json.get('email_ids', [])
    try:
        if not email_ids:
            return jsonify({'status': 'error', 'message': 'No email IDs provided'}), 400

        for email_id in email_ids:
            email = db.session.get(Email, email_id)
            if email:
                logging.info(f"Deleting email with ID: {email_id}")
                db.session.delete(email)
                deleted_email = DeletedEmail(id=email_id)
                db.session.add(deleted_email)  # Optionally add to DeletedEmail table if you want to keep track of deleted emails
            else:
                logging.warning(f"Email with ID {email_id} not found.")
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Emails deleted successfully'})
    except Exception as e:
        logging.error(f"Error deleting emails: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to delete emails: {str(e)}'}), 500

@app.route('/generate_reply', methods=['POST'])
def generate_reply():
    email_body = request.json.get('body')
    prompt = f"Given the following email body:\n\n{email_body}\n\nCompose a professional and appropriate reply. Provide both a subject and body."

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        # Assume response contains two parts: a subject and a body
        subject, body = response.text.split("\n", 1)  # Assuming LLM generates the subject on the first line
        
        # Remove unwanted prefixes like 'Subject:'
        if subject.lower().startswith("subject:"):
            subject = subject[len("subject:"):].strip()

        return jsonify({
            'subject': subject.strip(),
            'body': body.strip()
        })
    except Exception as e:
        logging.error(f"Error generating reply: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to generate reply'}), 500

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory('static/uploads', filename)

if __name__ == '__main__':
    app.run(port=8080)
