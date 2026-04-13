import React, { useState } from 'react';
import { 
  History, 
  Save, 
  CheckSquare, 
  Square, 
  ChevronLeft, 
  ChevronRight,
  Check
} from 'lucide-react';
import './TeacherAttendance.css';

const TeacherAttendance = () => {
  const [attendance, setAttendance] = useState({
    1: true,
    2: true,
    3: false,
    4: true,
    5: true,
  });

  const toggleAttendance = (id) => {
    setAttendance(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const markAll = (status) => {
    const newAtt = {};
    students.forEach(s => {
      newAtt[s.id] = status;
    });
    setAttendance(newAtt);
  };

  const students = [
    { id: 1, name: 'Alexander Wright', email: 'wright.a@academy.edu', idNumber: '#S76-0034L', status: 'ON TRACK', statusColor: 'green', avatar: 'https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=50&h=50&fit=crop' },
    { id: 2, name: 'Maya Ishikawa', email: 'ishikawa.m@academy.edu', idNumber: '#S76-4529S', status: 'NEUTRAL', statusColor: 'gray', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&h=50&fit=crop' },
    { id: 3, name: 'Marcus Thorne', email: 'thorne.m@academy.edu', idNumber: '#S76-3026T', status: 'AT RISK', statusColor: 'red', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=50&h=50&fit=crop' },
    { id: 4, name: 'Chloe Simmons', email: 'simmons.c@academy.edu', idNumber: '#S76-1120P', status: 'ON TRACK', statusColor: 'green', avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=50&h=50&fit=crop' },
    { id: 5, name: 'David Chen', email: 'chen.d@academy.edu', idNumber: '#S76-5532H', status: 'ON TRACK', statusColor: 'green', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=50&h=50&fit=crop' },
  ];

  return (
    <div className="ta-container">
      {/* Breadcrumb & Header */}
      <div className="ta-header-area">
        <div className="ta-breadcrumb">Academic Portal &gt; <span>Attendance</span></div>
        <div className="ta-header-content">
          <div>
            <h2 className="ta-title">Class Attendance</h2>
            <p className="ta-subtitle">Mathematics Section B - Oct 24, 2023</p>
          </div>
          <div className="ta-header-actions">
            <button className="ta-btn-secondary">
              <History size={16} /> View History
            </button>
            <button className="ta-btn-primary">
              <Save size={16} /> Save Attendance
            </button>
          </div>
        </div>
      </div>

      <div className="ta-content-grid">
        
        {/* Left Stats Column */}
        <div className="ta-stats-col">
          <div className="ta-stat-card border-purple">
            <h4 className="ta-stat-title">TOTAL STUDENTS</h4>
            <div className="ta-stat-value">42 <span className="ta-stat-sub">Enrolled</span></div>
          </div>
          
          <div className="ta-stat-card border-green">
            <h4 className="ta-stat-title">PRESENT TODAY</h4>
            <div className="ta-stat-value">38 <span className="ta-stat-change pos">+0.5%</span></div>
          </div>
          
          <div className="ta-stat-card border-red">
            <h4 className="ta-stat-title">ABSENT/LATE</h4>
            <div className="ta-stat-value">4 <span className="ta-stat-change neg">-0.5%</span></div>
          </div>

          <div className="ta-automated-card">
            <h4>Automated Mark</h4>
            <p>Mark all students who were present in the previous session as present today.</p>
            <button className="ta-auto-btn">Apply Auto-Attendance</button>
          </div>
        </div>

        {/* Right Register Column */}
        <div className="ta-register-col">
          <div className="ta-register-card">
            
            <div className="ta-reg-header">
              <div className="ta-reg-title-area">
                <h3>Attendance Register</h3>
                <span className="ta-live-badge"><div className="pulse-dot"></div> Live Session</span>
              </div>
              <div className="ta-reg-actions">
                <button className="ta-text-btn blue" onClick={() => markAll(true)}>Mark All Present</button>
                <div className="ta-divider">|</div>
                <button className="ta-text-btn" onClick={() => markAll(false)}>Clear All</button>
              </div>
            </div>

            <div className="ta-table-container">
              <table className="ta-table">
                <thead>
                  <tr>
                    <th>STUDENT NAME</th>
                    <th>ID NUMBER</th>
                    <th>STATUS</th>
                    <th className="align-center">ATTENDANCE</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.id}>
                      <td>
                        <div className="ta-student-info">
                          <img src={student.avatar} alt={student.name} className="ta-avatar" />
                          <div>
                            <div className="ta-name">{student.name}</div>
                            <div className="ta-email">{student.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="ta-id">{student.idNumber}</td>
                      <td>
                        <span className={`ta-status-badge badge-${student.statusColor}`}>
                          {student.status}
                        </span>
                      </td>
                      <td className="align-center">
                        <button 
                          className="ta-checkbox-btn"
                          onClick={() => toggleAttendance(student.id)}
                        >
                          {attendance[student.id] ? (
                            <div className="ta-checked-box"><Check size={14} strokeWidth={3} /></div>
                          ) : (
                            <Square size={20} color="var(--td-border)" fill="var(--td-bg)" />
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="ta-pagination">
              <span className="ta-page-info">Showing 1 of 42 students. Scroll for more.</span>
              <div className="ta-page-controls">
                <button className="ta-page-btn"><ChevronLeft size={16} /></button>
                <button className="ta-page-btn"><ChevronRight size={16} /></button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default TeacherAttendance;
