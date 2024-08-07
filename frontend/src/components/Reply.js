import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';

function Reply() {
    const location = useLocation();
    const { email } = location.state;
    const [reply, setReply] = useState('');

    useEffect(() => {
        axios.post('http://localhost:8080/generate_reply', { body: email.body })
            .then(response => setReply(response.data.reply))
            .catch(error => console.error('Error generating reply:', error));
    }, [email.body]);

    const handleCopyClick = () => {
        navigator.clipboard.writeText(reply);
        alert('Reply copied to clipboard!');
    };

    return (
        <div>
            <h3>Reply Recommendation</h3>
            <p><strong>To:</strong> {email.sender}</p>
            <p><strong>Subject:</strong> {email.subject}</p>
            <p><strong>Original Email:</strong> {email.body}</p>
            <p><strong>Recommended Reply:</strong> {reply}</p>
            <button onClick={handleCopyClick}>Copy Reply</button>
        </div>
    );
}

export default Reply;
