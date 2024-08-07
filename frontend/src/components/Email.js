import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Email.css';

function Email({ email }) {
    const navigate = useNavigate();

    const handleEmailClick = () => {
        navigate(`/reply/${email.id}`, { state: { email } });
    };

    // Truncate the email body to a maximum length with ellipsis
    const truncateBody = (body, maxLength = 150) => {
        return body.length > maxLength ? body.substring(0, maxLength) + '...' : body;
    };

    // Get top 3 keywords or fewer if not enough keywords
    const topKeywords = email.keywords.slice(0, 3);

    return (
        <div className="email" onClick={handleEmailClick}>
            <div className="email-header">
                <h3 className="email-subject">{email.subject}</h3>
                <p className="email-from"><strong>From:</strong> {email.sender}</p>
                <p className="email-date"><strong>Date:</strong> {new Date(email.date).toLocaleString()}</p>
            </div>
            <p className="email-body"><strong>Body:</strong> {truncateBody(email.body)}</p>
            <div className="email-details">
                <p><strong>Sentiment:</strong> Positive: {email.sentiment.pos}, Negative: {email.sentiment.neg}, Neutral: {email.sentiment.neu}</p>
                <p><strong>Keywords:</strong> {topKeywords.join(', ')}</p>
            </div>
        </div>
    );
}

export default Email;
