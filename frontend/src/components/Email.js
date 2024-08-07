import React from 'react';



function Email({ email }) {
    return (
        <div className="email">
            <p><strong>Email:</strong> {email.email}</p>
            <p><strong>Sentiment:</strong> Positive: {email.sentiment.pos}, Negative: {email.sentiment.neg}, Neutral: {email.sentiment.neu}</p>
            <p><strong>Keywords:</strong> {email.keywords.join(', ')}</p>
        </div>
    );
}

export default Email;