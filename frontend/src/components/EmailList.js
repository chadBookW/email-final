import React, { useState, useEffect } from 'react';
import { Button, Typography, Box, List } from '@mui/material';
import Email from './Email';
import axios from 'axios';

function EmailList() {
    const [emails, setEmails] = useState([]);
    const [selectedEmails, setSelectedEmails] = useState([]);

    useEffect(() => {
        fetchEmails();
    }, []);

    const fetchEmails = async () => {
        try {
            const response = await axios.get('http://localhost:8080/emails');
            setEmails(response.data || []); // Ensure data is at least an empty array
        } catch (error) {
            console.error('Error fetching emails:', error);
            setEmails([]); // Fallback to an empty array in case of error
        }
    };

    const handleEmailSelect = (emailId) => {
        setSelectedEmails(prevSelected =>
            prevSelected.includes(emailId)
                ? prevSelected.filter(id => id !== emailId)
                : [...prevSelected, emailId]
        );
    };

    const deleteSelectedEmails = async () => {
        try {
            await axios.post('http://localhost:8080/emails/delete', { email_ids: selectedEmails });
            fetchEmails(); // Refresh email list
            setSelectedEmails([]); // Clear selected emails
        } catch (error) {
            console.error('Error deleting emails:', error);
        }
    };

    return (
        <Box mt={4}>
            <Typography variant="h5" gutterBottom>Email List</Typography>
            <Button
                variant="contained"
                color="secondary"
                onClick={deleteSelectedEmails}
                disabled={selectedEmails.length === 0}
            >
                Delete Selected Emails
            </Button>
            <List>
                {emails.length > 0 ? (
                    emails.map(email => (
                        <Email
                            key={email.id}
                            email={email}
                            onEmailSelect={handleEmailSelect}
                            selectedEmails={selectedEmails}
                        />
                    ))
                ) : (
                    <Typography variant="body1">No emails available.</Typography>
                )}
            </List>
        </Box>
    );
}

export default EmailList;
