import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';
import Email from './components/Email';

const App = () => {
  const [emails, setEmails] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8080/emails')
      .then(response => {
        setEmails(response.data);
      })
      .catch(error => {
        console.error('There was an error fetching the emails!', error);
      });
  }, []);

  return (
    <div className="App">
      <h1>Email Manager</h1>
      {emails.map((email, index) => (
        <Email key={index} email={email} index={index} />
      ))}
    </div>
  );
};

export default App;
