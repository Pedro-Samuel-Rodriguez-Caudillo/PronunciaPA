import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/layout';
import { LandingPage } from './pages/LandingPage';
import { PracticePage } from './pages/PracticePage';
import { LearnPage } from './pages/LearnPage';
import { ProgressPage } from './pages/ProgressPage';

const App: React.FC = () => (
  <BrowserRouter>
    <div className="app-root">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/practice" element={<PracticePage />} />
          <Route path="/progress" element={<ProgressPage />} />
        </Routes>
      </main>
    </div>
  </BrowserRouter>
);

export default App;
