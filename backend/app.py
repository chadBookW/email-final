from flask import Flask, jsonify, request, send_from_directory, redirect, url_for
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

def load_credentials():
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config({
                "web": {
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                    "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
                    "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
                    "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "redirect_uris": [url_for('oauth2callback', _external=True)]
                }
            }, SCOPES)
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
from nltk.corpus import wordnet as wn

# Predefined categories and associated keywords
categories = {
    'work': ['project', 'deadline', 'meeting', 'report', 'client'],
    'finance': ['invoice', 'payment', 'salary', 'expense', 'billing'],
    'personal': ['party', 'dinner', 'vacation', 'family', 'birthday'],
    # Add more categories and keywords as needed
}

def extract_keywords(email_body):
    """
    Extract relevant keywords and categorize the email as work or personal.
    """
    # Load the NLP model and process the email body
    doc = nlp(email_body)

    # Extract company names using Named Entity Recognition (NER)
    company_names = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
    print(f"Extracted Company Names: {company_names}")  # Debugging line

    # Define keywords related to requests
    request_keywords = ['availability', 'pricing', 'quote', 'features', 'datasheet', 'support', 'warranty']
    
    # Extract relevant requests by looking for these keywords in the text
    requests = [token.text for token in doc if token.lemma_.lower() in request_keywords]
    print(f"Extracted Requests: {requests}")  # Debugging line

    # Use sets to ensure uniqueness
    company_names = list(set(company_names))
    requests = list(set(requests))

    # Combine the company names and requests as keywords
    keywords = company_names + requests
    print(f"Combined Keywords: {keywords}")  # Debugging line

    # Classify email as work or personal based on content
    work_related_keywords = ['project', 'team', 'meeting', 'deadline', 'report', 'procurement', 'contract']
    personal_related_keywords = ['family', 'friend', 'party', 'holiday', 'gift', 'reunion']

    # Check if any of the work or personal keywords are present in the email
    email_text = email_body.lower()
    is_work = any(keyword in email_text for keyword in work_related_keywords)
    is_personal = any(keyword in email_text for keyword in personal_related_keywords)

    category = 'work' if is_work else 'personal' if is_personal else 'unknown'
    
    return {
        'keywords': ','.join(keywords),
        'category': category
    }



def analyze_email(email):
    try:
        # Extract sentiment
        sentiment = sentiment_analyzer.polarity_scores(email.body)

        # Extract keywords and category from the email body
        result = extract_keywords(email.body)
        keywords = result['keywords']
        category = result['category']

        return {
            'id': email.id,
            'subject': email.subject,
            'date': email.date,
            'sender': email.sender,
            'body': email.body,
            'sentiment': sentiment,
            'keywords': keywords.split(','),
            'category': category
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
            'keywords': [],
            'category': 'unknown'
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
        response_text = response.text
        if "\n" in response_text:
            subject, body = response_text.split("\n", 1)
        else:
            subject, body = "Re:", response_text  # Handle cases with no clear subject

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

@app.route('/oauth2callback')
def oauth2callback():
    flow = InstalledAppFlow.from_client_config({
        "web": {
            "client_id": os.getenv('GOOGLE_CLIENT_ID'),
            "project_id": os.getenv('GOOGLE_PROJECT_ID'),
            "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
            "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
            "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
            "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
            "redirect_uris": [url_for('oauth2callback', _external=True)]
        }
    }, SCOPES)
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials

    # Save credentials to environment-specific storage
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))