/* RankTable.jsx */
import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const RankTable = ({ students, categoryLabel }) => {
  return (
    <div className="lb-list-section">
      <div className="lb-table-head">
        <span>Rank</span>
        <span>Student</span>
        <span>Efficiency</span>
        <span>Momentum</span>
        <span style={{ textAlign: 'right', paddingRight: '15px' }}>{categoryLabel || 'Total Score'}</span>
      </div>

      <div className="lb-table-body">
        {students.map((s, idx) => {
          const isPercent = (categoryLabel || '').includes('Attendance');
          const displayScore = isPercent ? `${s.score}%` : s.score.toLocaleString();

          return (
            <div key={idx} className={`lb-table-row ${s.isUser ? 'highlight-me' : ''}`}>
               <div className="lb-rank-num">{s.rank < 10 ? `0${s.rank}` : s.rank}</div>
               <div className="lb-student">
                  <img src={s.avatar} alt={s.name} className="lb-mini-avatar" />
                  <div>
                     <span className="lb-std-name">{s.name} {s.isUser && '(YOU)'}</span>
                     <span className="lb-std-info">{s.subject}</span>
                  </div>
               </div>
               <div className="lb-efficiency">
                  <div className="lb-eff-bar"><div className="lb-eff-fill" style={{ width: `${s.efficiency || (Math.random() * 40 + 60)}%` }} /></div>
               </div>
               <div className="lb-momentum">
                  {s.momentum === 'up' && <TrendingUp size={16} color="var(--neon-green)" />}
                  {s.momentum === 'down' && <TrendingDown size={16} color="#f87171" />}
                  {(s.momentum === 'flat' || !s.momentum) && <Minus size={16} color="var(--neon-cyan)" />}
               </div>
               <div className="lb-score">{displayScore}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RankTable;

