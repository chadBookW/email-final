import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, Typography, Button, TextField, CircularProgress, Box } from '@mui/material';
import axios from 'axios';

function Reply() {
    const location = useLocation();
    const { email } = location.state;
    const [reply, setReply] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        axios.post('http://localhost:8080/generate_reply', { body: email.body })
            .then(response => {
                setReply(response.data.reply);
                setLoading(false);
            })
            .catch(error => {
                console.error('Error generating reply:', error);
                setError('Failed to generate reply. Please try again later.');
                setLoading(false);
            });
    }, [email.body]);

    const handleCopyClick = () => {
        navigator.clipboard.writeText(reply);
        alert('Reply copied to clipboard!');
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
                    <Typography variant="subtitle1">
                        <strong>Subject:</strong> {email.subject}
                    </Typography>
                    <Typography variant="body1" paragraph>
                        <strong>Original Email:</strong>
                    </Typography>
                    <Typography variant="body2" paragraph>
                        {email.body}
                    </Typography>
                    <Typography variant="body1" paragraph>
                        <strong>Recommended Reply:</strong>
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
                            value={reply}
                            InputProps={{
                                readOnly: true,
                            }}
                        />
                    )}
                    <Box mt={2} display="flex" justifyContent="space-between">
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleCopyClick}
                            disabled={!reply}
                        >
                            Copy Reply
                        </Button>
                    </Box>
                </CardContent>
            </Card>
        </Box>
    );
}

export default Reply;
