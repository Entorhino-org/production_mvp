import React from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  CheckSquare, 
  BookOpen, 
  Calendar, 
  LineChart, 
  Users, 
  Megaphone, 
  MessageSquare, 
  Trophy, 
  PieChart, 
  Bell, 
  Plus
} from 'lucide-react';
import './TeacherDashboard.css';

const TeacherSidebar = ({ activePage, onPageChange }) => {
  const menuItems = [
    { icon: LayoutDashboard, label: 'Overview' },
    { icon: FileText, label: 'Topics / Notes' },
    { icon: CheckSquare, label: 'Tests' },
    { icon: BookOpen, label: 'Homework' },
    { icon: Calendar, label: 'Attendance' },
    { icon: LineChart, label: 'Class Insights' },
    { icon: Users, label: 'Join Requests' },
    { icon: Megaphone, label: 'Announcements' },
    { icon: MessageSquare, label: 'My Feedback' },
    { icon: Trophy, label: 'Leaderboard' },
    { icon: PieChart, label: 'Gap Analysis' },
    { icon: Bell, label: 'Alerts' },
  ];

  return (
    <div className="td-sidebar">
      <div className="td-sidebar-header">
        <h2>Academic Curator</h2>
        <p>Senior Faculty</p>
      </div>

      <div className="td-nav">
        {menuItems.map((item, index) => (
          <div 
            key={index} 
            className={`td-nav-item ${activePage === item.label ? 'active' : ''}`}
            onClick={() => onPageChange && onPageChange(item.label)}
            style={{ cursor: 'pointer' }}
          >
            <item.icon size={18} className="td-nav-icon" />
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      <div className="td-sidebar-footer">
        <button className="td-create-btn">
          <Plus size={18} />
          Create New Class
        </button>
        
        <div className="td-profile">
          <img 
            src="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&h=150&fit=crop&crop=faces" 
            alt="Dr. Julian Vance" 
            className="td-profile-img" 
          />
          <div className="td-profile-info">
            <h4>Dr. Julian Vance</h4>
            <p>Curator Level 4</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeacherSidebar;
