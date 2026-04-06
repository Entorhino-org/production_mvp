/* FormattedAiResponse.jsx */
import React from 'react';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

const FormattedAiResponse = ({ content }) => {
  // Simple parser to separate text from LaTeX blocks marked with [math]...[/math] or $$...$$
  const parseContent = (text) => {
    const parts = text.split(/(\[math\].*?\[\/math\]|\$\$.*?\$\$)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('[math]') && part.endsWith('[/math]')) {
        const formula = part.substring(6, part.length - 7);
        return <BlockMath key={idx} math={formula} />;
      }
      if (part.startsWith('$$') && part.endsWith('$$')) {
        const formula = part.substring(2, part.length - 2);
        return <InlineMath key={idx} math={formula} />;
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="formatted-response">
      {parseContent(content)}
    </div>
  );
};

export default FormattedAiResponse;
