import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import ConnectPage from './pages/ConnectPage';
import Repositories from './pages/Repositories';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/repositories" element={<Repositories />} />
        {/* Fallback to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
