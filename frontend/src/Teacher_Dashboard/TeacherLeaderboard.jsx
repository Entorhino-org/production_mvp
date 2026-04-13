import React, { useState } from 'react';
import { 
  Calendar, 
  FileText, 
  CheckSquare, 
  Download, 
  ChevronLeft, 
  ChevronRight, 
  Plus,
  Award,
  Star
} from 'lucide-react';
import './TeacherLeaderboard.css';

const TeacherLeaderboard = () => {
  const [metric, setMetric] = useState('Attendance');
  const [classFilter, setClassFilter] = useState('ALL GRADES');
  const [termToggle, setTermToggle] = useState('THIS TERM');

  const topThree = [
    { rank: 2, name: 'Alex Thompson', score: '98.4%', avatar: 'https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=100&h=100&fit=crop' },
    { rank: 1, name: 'Sarah Jenkins', score: '99.8%', badge: 'GOLD SCHOLAR', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop' },
    { rank: 3, name: 'Liam Carter', score: '97.2%', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop' }
  ];

  const performers = [
    { rank: '04', name: 'Emma Watson', initials: 'EW', color: '#818cf8', admn: 'L-2023-452', cls: 'Grade 12-A', score: '96.5%' },
    { rank: '05', name: 'Daniel Radcliffe', initials: 'DR', color: '#34d399', admn: 'L-2023-118', cls: 'Grade 11-B', score: '96.1%' },
    { rank: '06', name: 'Rupert Grint', initials: 'RG', color: '#a78bfa', admn: 'L-2023-094', cls: 'Grade 12-A', score: '95.8%' },
    { rank: '07', name: 'Millie Brown', initials: 'MB', color: '#60a5fa', admn: 'L-2023-772', cls: 'Grade 10-C', score: '94.2%' },
    { rank: '08', name: 'Finn Wolfhard', initials: 'FW', color: '#9ca3af', admn: 'L-2023-331', cls: 'Grade 10-A', score: '93.9%' }
  ];

  return (
    <div className="tl-container">
      {/* Header Area */}
      <div className="tl-header">
        <div>
          <span className="tl-super-title">INSTITUTIONAL PERFORMANCE</span>
          <h2 className="tl-title">Academic Leaderboard</h2>
        </div>
        
        <div className="tl-toggle-pill">
          <button 
            className={`tl-toggle-btn ${termToggle === 'THIS TERM' ? 'active' : ''}`}
            onClick={() => setTermToggle('THIS TERM')}
          >
            THIS TERM
          </button>
          <button 
            className={`tl-toggle-btn ${termToggle === 'HISTORICAL' ? 'active' : ''}`}
            onClick={() => setTermToggle('HISTORICAL')}
          >
            HISTORICAL
          </button>
        </div>
      </div>

      <div className="tl-content-grid">
        
        {/* Left Sidebar Layout */}
        <div className="tl-sidebar-col">
          {/* Select Metric Box */}
          <div className="tl-box">
            <h4 className="tl-box-title">SELECT METRIC</h4>
            <div className="tl-metric-list">
              <button 
                className={`tl-metric-btn ${metric === 'Attendance' ? 'active' : ''}`}
                onClick={() => setMetric('Attendance')}
              >
                <span>Attendance</span>
                <Calendar size={18} />
              </button>
              <button 
                className={`tl-metric-btn ${metric === 'Test Score' ? 'active' : ''}`}
                onClick={() => setMetric('Test Score')}
              >
                <span>Test Score</span>
                <FileText size={18} />
              </button>
              <button 
                className={`tl-metric-btn ${metric === 'Homework Score' ? 'active' : ''}`}
                onClick={() => setMetric('Homework Score')}
              >
                <span>Homework Score</span>
                <CheckSquare size={18} />
              </button>
            </div>
          </div>

          {/* Class Filter Box */}
          <div className="tl-box">
            <h4 className="tl-box-title">CLASS FILTER</h4>
            <div className="tl-filter-tags">
              {['ALL GRADES', 'GRADE 10', 'GRADE 11', 'GRADE 12'].map((cls) => (
                <button 
                  key={cls}
                  className={`tl-filter-tag ${classFilter === cls ? 'active' : ''}`}
                  onClick={() => setClassFilter(cls)}
                >
                  {cls}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Main Area */}
        <div className="tl-main-col">
          
          {/* Podium Area */}
          <div className="tl-podium-container">
            {topThree.map((item, index) => (
              <div key={index} className={`tl-podium tl-podium-${item.rank}`}>
                <div className="tl-podium-card">
                  <div className="tl-rank-icon">
                    {item.rank === 1 ? <Award size={40} color="var(--td-surface)" className="gold-icon" /> : 
                     <Star size={32} color={item.rank === 2 ? '#cbd5e1' : '#fcd34d'} opacity={0.6} /> }
                  </div>
                  
                  <div className="tl-avatar-wrapper">
                    <img src={item.avatar} alt={item.name} className="tl-avatar" />
                  </div>
                  
                  <div className="tl-podium-info">
                    <span className="tl-rank-label">RANK 0{item.rank}</span>
                    <h4 className="tl-podium-name">{item.name}</h4>
                    <span className="tl-podium-score">{item.score}</span>
                    
                    {item.badge && (
                      <span className="tl-gold-badge">{item.badge}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Top Performers Table */}
          <div className="tl-table-card">
            <div className="tl-table-header">
              <h3>Top Performers List</h3>
              <button className="tl-export-btn">EXPORT CSV <Download size={14} /></button>
            </div>

            <div className="tl-table-wrapper">
              <table className="tl-table">
                <thead>
                  <tr>
                    <th>RANK</th>
                    <th>NAME</th>
                    <th>ADM NO.</th>
                    <th>CLASS</th>
                    <th className="right-align">ATTENDANCE %</th>
                  </tr>
                </thead>
                <tbody>
                  {performers.map((p, idx) => (
                    <tr key={idx}>
                      <td className="tl-td-rank">{p.rank}</td>
                      <td>
                        <div className="tl-td-name">
                          <div className="tl-initials" style={{ backgroundColor: `${p.color}20`, color: p.color }}>
                            {p.initials}
                          </div>
                          <span>{p.name}</span>
                        </div>
                      </td>
                      <td className="tl-td-admn">{p.admn}</td>
                      <td className="tl-td-cls">{p.cls}</td>
                      <td className="tl-td-score right-align">{p.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="tl-pagination">
              <span className="tl-page-info">SHOWING 1-5 OF 142 STUDENTS</span>
              <div className="tl-page-controls">
                <button className="tl-page-btn"><ChevronLeft size={14}/></button>
                <button className="tl-page-btn active">1</button>
                <button className="tl-page-btn">2</button>
                <button className="tl-page-btn">3</button>
                <button className="tl-page-btn"><ChevronRight size={14}/></button>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Floating Action Button */}
      <button className="tl-fab">
        <Plus size={24} />
      </button>
    </div>
  );
};

export default TeacherLeaderboard;
