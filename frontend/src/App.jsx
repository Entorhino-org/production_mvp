import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar/Sidebar';
import Performance from './pages/Performance/Performance';
import Announcements from './pages/Announcements/AnnouncementsPage';
import AttendancePortal from './pages/Attendance/AttendancePortal';
import AiPortal from './pages/LearnWithAI/AiPortal';
import FeedbackPortal from './pages/Feedback/FeedbackPage';
import LeaderboardPortal from './pages/Leaderboard/LeaderboardPortal';
import TestsPortal from './pages/Tests/TestsPortal';
import GapAnalysisPortal from './pages/GapAnalysis/GapAnalysisPortal';
import HomeworkPortal from './pages/Homework/HomeworkPortal';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import './App.css';

// Layout wrapper to inject sidebar into a group of routes
const DashboardLayout = ({ user, handleLogout, children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const location = useLocation();

  const activePageMap = {
    '/': 'My Performance',
    '/tests': 'Tests',
    '/homework': 'Homework',
    '/attendance': 'Attendance',
    '/ai-portal': 'Learn with AI',
    '/feedback': 'Give Feedback',
    '/leaderboard': 'Leaderboard',
    '/gap-analysis': 'Gap Analysis',
    '/alerts': 'Alerts',
  };

  const activePage = activePageMap[location.pathname] || 'My Performance';

  return (
    <div className={`app-container ${(isSidebarOpen || isHovered) ? 'sidebar-open' : 'sidebar-closed'}`}>
      <div 
        className="sidebar-trigger"
        onMouseEnter={() => setIsHovered(true)}
      />

      <Sidebar 
        isOpen={isSidebarOpen || isHovered} 
        setHovered={setIsHovered} 
        activePage={activePage}
        onLogout={handleLogout}
      />
      
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser && savedUser !== 'undefined') {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        console.error("Session parse error", e);
      }
    }
    setLoading(false);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  if (loading) return (
    <div style={{ background: '#050505', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a855f7' }}>
      <h1>SYNCING NEURONS...</h1>
    </div>
  );

  return (
    <Router>
      <Routes>
        {/* Auth Routes */}
        <Route 
          path="/login" 
          element={!user ? <Login onLoginSuccess={(u) => setUser(u)} /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/register" 
          element={!user ? <Register onRegisterSuccess={(u) => setUser(u)} /> : <Navigate to="/" replace />} 
        />

        {/* Dashboard Routes (Flat Pattern) */}
        <Route path="/" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><Performance user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/tests" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><TestsPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/homework" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><HomeworkPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/attendance" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><AttendancePortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/ai-portal" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><AiPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/feedback" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><FeedbackPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/leaderboard" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><LeaderboardPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/gap-analysis" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><GapAnalysisPortal user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />
        <Route path="/alerts" element={user ? <DashboardLayout user={user} handleLogout={handleLogout}><Announcements user={user} /></DashboardLayout> : <Navigate to="/login" replace />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
