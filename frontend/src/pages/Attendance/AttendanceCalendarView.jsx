/* AttendanceCalendarView.jsx */
import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

const AttendanceCalendarView = ({ onClose }) => {
  const [currentMonth, setCurrentMonth] = useState('October 2023');
  
  // Dummy data for a month grid (31 days starting logic simplified)
  const days = Array.from({ length: 31 }, (_, i) => ({
    date: i + 1,
    status: i % 7 === 0 ? 'absent' : (i % 15 === 0 ? 'leave' : 'present'),
    isCurrent: i < 25 // Current date is 25th
  }));

  const weekDays = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

  return (
    <div className="calendar-half-view">
      <div className="calendar-header">
        <div className="cal-title-box">
          <button className="cal-nav-btn"><ChevronLeft size={16} /></button>
          <h3>{currentMonth}</h3>
          <button className="cal-nav-btn"><ChevronRight size={16} /></button>
        </div>
        <div className="cal-actions">
           <button className="cal-filter-btn active">Month</button>
           <button className="cal-filter-btn">Day</button>
           <button className="close-cal" onClick={onClose}><X size={18} /></button>
        </div>
      </div>

      <div className="calendar-grid">
        {weekDays.map(d => <div key={d} className="weekday-label">{d}</div>)}
        {days.map(d => (
          <div 
            key={d.date} 
            className={`calendar-day ${d.status} ${!d.isCurrent ? 'future' : ''}`}
          >
            <span className="day-number">{d.date}</span>
            {d.isCurrent && <div className="status-dot" />}
          </div>
        ))}
      </div>

      <div className="calendar-legend">
        <div className="leg-item"><div className="dot present" /> Present</div>
        <div className="leg-item"><div className="dot absent" /> Absent</div>
        <div className="leg-item"><div className="dot leave" /> Leave</div>
        <div className="leg-item"><div className="dot" /> Future</div>
      </div>
    </div>
  );
};

export default AttendanceCalendarView;
