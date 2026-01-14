import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainDashboard from './pages/Main';
import FileBrowser from './pages/Files';

const App: React.FC = () => {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route path="/" element={<MainDashboard />} />
          <Route path="/files" element={<FileBrowser />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
