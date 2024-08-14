from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Email(db.Model):
    id = db.Column(db.String, primary_key=True)
    subject = db.Column(db.String, nullable=True)
    date = db.Column(db.String, nullable=True)
    sender = db.Column(db.String, nullable=True)
    body = db.Column(db.Text, nullable=True)
    sentiment_pos = db.Column(db.Float, nullable=True)
    sentiment_neg = db.Column(db.Float, nullable=True)
    sentiment_neu = db.Column(db.Float, nullable=True)
    keywords = db.Column(db.String, nullable=True)

    def __init__(self, id, subject, date, sender, body, sentiment_pos, sentiment_neg, sentiment_neu, keywords):
        self.id = id
        self.subject = subject
        self.date = date
        self.sender = sender
        self.body = body
        self.sentiment_pos = sentiment_pos
        self.sentiment_neg = sentiment_neg
        self.sentiment_neu = sentiment_neu
        self.keywords = keywords

    def __repr__(self):
        return f'<Email {self.subject}>'

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'date': self.date,
            'sender': self.sender,
            'body': self.body,
            'sentiment': {
                'pos': self.sentiment_pos,
                'neg': self.sentiment_neg,
                'neu': self.sentiment_neu
            },
            'keywords': self.keywords.split(',') if self.keywords else []
        }
