from flask import Flask, jsonify, request
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
from datetime import datetime
from models import db, Email,DeletedEmail

# Configuration
GOOGLE_API_KEY = 'AIzaSyCizxQ6wLglJdjErZ5jw1pTiCEj4B9JRP4'
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emails.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Setup nltk and spacy
nltk.download('vader_lexicon')
nltk.download('punkt')
nlp = spacy.load('en_core_web_sm')
sentiment_analyzer = SentimentIntensityAnalyzer()

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

creds = None

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

from datetime import datetime

from datetime import datetime
import logging
import base64

from datetime import datetime, timezone

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
        for email_id in email_ids:
            email = Email.query.get(email_id)
            if email:
                db.session.delete(email)
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
        
        # Remove unwanted prefixes (e.g., '## Subject: Re:')
        if subject.lower().startswith("## subject: re:"):
            subject = subject[15:].strip()
        elif subject.lower().startswith("## subject:"):
            subject = subject[11:].strip()

        return jsonify({
            'subject': subject.strip(),
            'body': body.strip()
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        email_data = request.json
        recipient = email_data['recipient']
        subject = email_data['subject']
        body_text = email_data['body']

        # Create the email message
        message = f"To: {recipient}\r\nSubject: {subject}\r\n\r\n{body_text}"
        encoded_message = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")

        # Create the message payload
        send_message = {
            'raw': encoded_message
        }

        # Send the email
        service.users().messages().send(userId='me', body=send_message).execute()

        return jsonify({'status': 'success', 'message': 'Email sent successfully!'})
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to send email: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True, port=8080)
