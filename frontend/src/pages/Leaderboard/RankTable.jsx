/* RankTable.jsx */
import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const RankTable = ({ students }) => {
  return (
    <div className="lb-list-section">
      <div className="lb-table-head">
        <span>Rank</span>
        <span>Student</span>
        <span>Efficiency</span>
        <span>Momentum</span>
        <span style={{ textAlign: 'right', paddingRight: '15px' }}>Total Score</span>
      </div>

      <div className="lb-table-body">
        {students.map((s, idx) => (
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
                <div className="lb-eff-bar"><div className="lb-eff-fill" style={{ width: `${s.efficiency}%` }} /></div>
             </div>
             <div className="lb-momentum">
                {s.momentum === 'up' && <TrendingUp size={16} color="var(--neon-green)" />}
                {s.momentum === 'down' && <TrendingDown size={16} color="#f87171" />}
                {s.momentum === 'flat' && <Minus size={16} color="var(--neon-cyan)" />}
             </div>
             <div className="lb-score">{s.score.toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RankTable;
