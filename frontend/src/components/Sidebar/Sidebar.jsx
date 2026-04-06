import React from 'react';
import { 
  Activity, 
  FileText, 
  BookOpen, 
  Calendar, 
  Zap, 
  MessageSquare, 
  Trophy, 
  PieChart, 
  Bell, 
  LogOut 
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import logo from '../../assets/logo.png';
import './Sidebar.css';

const Sidebar = ({ isOpen, setHovered, activePage, onLogout }) => {
  const navigate = useNavigate();

  const menuItems = [
    { icon: Activity, label: 'My Performance', path: '/' },
    { icon: FileText, label: 'Tests', path: '/tests' },
    { icon: BookOpen, label: 'Homework', path: '/homework' },
    { icon: Calendar, label: 'Attendance', path: '/attendance' },
    { icon: Zap, label: 'Learn with AI', path: '/ai-portal' },
    { icon: MessageSquare, label: 'Give Feedback', path: '/feedback' },
    { icon: Trophy, label: 'Leaderboard', path: '/leaderboard' },
    { icon: PieChart, label: 'Gap Analysis', path: '/gap-analysis' },
    { icon: Bell, label: 'Alerts', path: '/alerts' },
  ];

  return (
    <motion.div 
      className={`sidebar ${isOpen ? 'open' : 'closed'}`}
      initial={false}
      animate={{ 
        x: isOpen ? 0 : -250, 
        opacity: isOpen ? 1 : 0.4
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Logo Section */}
      <div className="logo-container" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
        <img src={logo} alt="ENTORHINO" className="sidebar-logo-img" />
        <p className="logo-subtext">THE NEON FLUX</p>
      </div>

      {/* Navigation Menu */}
      <nav className="nav-menu">
        {menuItems.map((item, index) => {
          const isActive = activePage === item.label;
          return (
            <motion.div
              key={index}
              whileHover={{ x: 5 }}
              onClick={() => navigate(item.path)}
              className={`nav-item ${isActive ? 'active' : ''}`}
              style={{ cursor: 'pointer' }}
            >
              <item.icon size={18} className="nav-icon" />
              <span className="nav-label">{item.label}</span>
              {isActive && <div className="active-glow" />}
            </motion.div>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="sidebar-footer">
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="pulse-btn"
        >
          UNLOCK PULSE
        </motion.button>
        
        <button 
          className="logout-btn" 
          onClick={(e) => {
            e.stopPropagation();
            onLogout();
            navigate('/login');
          }}
        >
          <LogOut size={16} />
          <span>LOGOUT</span>
        </button>
      </div>
    </motion.div>
  );
};

export default Sidebar;
