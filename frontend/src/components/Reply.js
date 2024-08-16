import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, Typography, Button, TextField, CircularProgress, Box } from '@mui/material';
import axios from 'axios';

function Reply() {
    const location = useLocation();
    const { email } = location.state;
    const [replyBody, setReplyBody] = useState('');
    const [replySubject, setReplySubject] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Request reply generation for both subject and body
        axios.post('http://localhost:8080/generate_reply', { body: email.body })
            .then(response => {
                // Set the generated subject and body in the respective text fields
                setReplySubject(response.data.subject);
                setReplyBody(response.data.body);
                setLoading(false);
            })
            .catch(error => {
                console.error('Error generating reply:', error);
                setError('Failed to generate reply. Please try again later.');
                setLoading(false);
            });
    }, [email.body]);

    const handleCopyClick = () => {
        navigator.clipboard.writeText(replyBody);
        alert('Reply copied to clipboard!');
    };

    const sendReply = () => {
        const emailData = {
            recipient: email.sender,
            subject: replySubject,
            body: replyBody,
        };

        axios.post('http://localhost:8080/send_email', emailData)
            .then(response => {
                alert(response.data.message);  // Show success message
            })
            .catch(error => {
                console.error('Error sending email:', error);
                alert('Failed to send email. Please try again later.');
            });
    };

    return (
        <Box sx={{ maxWidth: 800, margin: 'auto', padding: 2 }}>
            <Card variant="outlined">
                <CardContent>
                    <Typography variant="h5" gutterBottom>
                        Reply Recommendation
                    </Typography>
                    <Typography variant="h6">
                        <strong>To:</strong> {email.sender}
                    </Typography>
                    <Typography variant="body1" paragraph>
                        <strong>Original Email:</strong>
                    </Typography>
                    <Typography variant="body2" paragraph>
                        {email.body}
                    </Typography>
                    <Typography variant="body1" paragraph>
                        <strong>Subject:</strong>
                    </Typography>
                    <TextField
                        fullWidth
                        variant="outlined"
                        value={replySubject}
                        onChange={(e) => setReplySubject(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <Typography variant="body1" paragraph>
                        <strong>Reply:</strong>
                    </Typography>
                    {loading ? (
                        <Box display="flex" justifyContent="center" alignItems="center" mt={2}>
                            <CircularProgress />
                        </Box>
                    ) : error ? (
                        <Typography color="error" variant="body2">
                            {error}
                        </Typography>
                    ) : (
                        <TextField
                            multiline
                            rows={6}
                            fullWidth
                            variant="outlined"
                            value={replyBody}
                            onChange={(e) => setReplyBody(e.target.value)}
                        />
                    )}
                    <Box mt={2} display="flex" justifyContent="space-between">
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleCopyClick}
                            disabled={!replyBody}
                        >
                            Copy Reply
                        </Button>
                        <Button
                            variant="contained"
                            color="secondary"
                            onClick={sendReply}
                            disabled={!replyBody || !replySubject}
                        >
                            Send Email
                        </Button>
                    </Box>
                </CardContent>
            </Card>
        </Box>
    );
}

export default Reply;
