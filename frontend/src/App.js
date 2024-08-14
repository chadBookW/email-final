import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Container, Typography, Box, CssBaseline, AppBar, Toolbar, Button } from '@mui/material';
import EmailList from './components/EmailList'; // Ensure this import matches the correct path
import Reply from './components/Reply'; // Ensure this import matches the correct path

function App() {
    return (
        <Router>
            <CssBaseline />
            <AppBar position="static" color="primary">
                <Toolbar>
                    <Typography variant="h5" sx={{ flexGrow: 1, fontWeight: 'bold', color: '#fff' }}>
                        Email Manager
                    </Typography>
                    <Button color="inherit">Login</Button>
                </Toolbar>
            </AppBar>
            <Container maxWidth="lg" sx={{ mt: 4, mx: 'auto' }}> {/* Wider container */}
                <Box sx={{ bgcolor: '#fff', p: 3, borderRadius: 1, boxShadow: 1 }}>
                    <Routes>
                        <Route path="/" element={<EmailList />} />
                        <Route path="/reply/:id" element={<Reply />} />
                    </Routes>
                </Box>
            </Container>
        </Router>
    );
}

export default App;
