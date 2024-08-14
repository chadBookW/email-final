import React, { useState } from 'react';
import { Card, CardContent, Typography, CardActionArea, Chip, Box, Checkbox } from '@mui/material';
import { useNavigate } from 'react-router-dom';

function Email({ email, onEmailSelect, selectedEmails }) {
    const navigate = useNavigate();
    const [isChecked, setIsChecked] = useState(selectedEmails.includes(email.id));

    const handleEmailClick = () => {
        navigate(`/reply/${email.id}`, { state: { email } });
    };

    const handleCheckboxChange = (event) => {
        event.stopPropagation(); // Prevents the card click event from being triggered
        setIsChecked(!isChecked);
        onEmailSelect(email.id);
    };

    const truncateBody = (body, maxLength = 150) => {
        return body.length > maxLength ? body.substring(0, maxLength) + '...' : body;
    };

    const topKeywords = email.keywords.slice(0, 3);

    // Define sentiment emojis
    const sentimentEmoji = {
        pos: '😊',
        neg: '😟',
        neu: '😐'
    };

    return (
        <Card variant="outlined" sx={{ mb: 2 }}>
            <Box display="flex" alignItems="center">
                <Checkbox
                    checked={isChecked}
                    onChange={handleCheckboxChange}
                    inputProps={{ 'aria-label': 'select email' }}
                />
                <CardActionArea onClick={handleEmailClick}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            {email.subject}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                            <strong>From:</strong> {email.sender}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                            <strong>Date:</strong> {new Date(email.date).toLocaleString()}
                        </Typography>
                        <Typography variant="body2" paragraph>
                            <strong>Body:</strong> {truncateBody(email.body)}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                            <strong>Sentiment:</strong> 
                            {sentimentEmoji.pos} Positive: {email.sentiment?.pos ?? 'N/A'}, 
                            {sentimentEmoji.neg} Negative: {email.sentiment?.neg ?? 'N/A'}, 
                            {sentimentEmoji.neu} Neutral: {email.sentiment?.neu ?? 'N/A'}
                        </Typography>
                        <Box mt={1}>
                            {topKeywords.map((keyword, index) => (
                                <Chip label={keyword} key={index} size="small" style={{ marginRight: '4px' }} />
                            ))}
                        </Box>
                    </CardContent>
                </CardActionArea>
            </Box>
        </Card>
    );
}

export default Email;
