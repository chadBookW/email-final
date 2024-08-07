import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import './App.css';
import Email from './components/Email';
import Reply from './components/Reply';

function App() {
    return (
        <Router>
            <div className="App">
                <h1>Email Manager</h1>
                <Routes>
                    <Route path="/" element={<EmailList />} />
                    <Route path="/reply/:id" element={<Reply />} />
                </Routes>
            </div>
        </Router>
    );
}

function EmailList() {
    const [emails, setEmails] = useState([]);

    useEffect(() => {
        fetch('http://localhost:8080/emails')
            .then(response => response.json())
            .then(data => setEmails(data))
            .catch(error => console.error('Error fetching emails:', error));
    }, []);

    return (
        <div className="email-container">
            {emails.map((email, index) => (
                <Email key={index} email={email} />
            ))}
        </div>
    );
}

export default App;
