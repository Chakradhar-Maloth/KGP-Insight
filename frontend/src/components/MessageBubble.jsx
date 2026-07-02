import React from 'react';
import { FiThumbsUp, FiThumbsDown, FiFileText } from 'react-icons/fi';

export default function MessageBubble({ msg, msgIdx, onFeedback }) {
  
  // Clean Markdown/Text parser helper to render basic tables and bold strings
  const renderMessageText = (text) => {
    if (!text) return "";
    
    // Check if text contains a Markdown table
    if (text.includes("### Tabular Data:") || text.includes("| --- |")) {
      const parts = text.split("### Tabular Data:");
      const plainText = parts[0];
      const tableText = parts[1] || "";
      
      const lines = tableText.split("\n").map(l => l.trim()).filter(l => l.startsWith("|"));
      if (lines.length >= 2) {
        const parseRow = (line) => line.split("|").map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        const headers = parseRow(lines[0]);
        const rows = lines.slice(2).map(parseRow);
        
        return (
          <div>
            <p style={{ whiteSpace: 'pre-wrap' }}>{renderBoldText(plainText)}</p>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    {headers.map((h, i) => <th key={i}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => <td key={cIdx}>{cell}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      }
    }
    
    return <p style={{ whiteSpace: 'pre-wrap' }}>{renderBoldText(text)}</p>;
  };

  const renderBoldText = (text) => {
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, index) => {
      return index % 2 === 1 ? <strong key={index} style={{ fontWeight: '700' }}>{part}</strong> : part;
    });
  };

  return (
    <div className={`message-row ${msg.sender} fade-in`}>
      {msg.sender === 'bot' && (
        <div className="message-avatar">AI</div>
      )}
      
      <div className="message-bubble">
        {msg.text ? (
          renderMessageText(msg.text)
        ) : (
          <div className="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}

        {/* Latency & Cache Metadata */}
        {msg.sender === 'bot' && msg.latency !== null && (
          <div style={{ marginTop: '12px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Response Latency: <strong>{msg.latency}ms</strong>
            {msg.isCacheHit && <span className="latency-pill">Semantic Cache Hit</span>}
          </div>
        )}

        {/* Citations Card Panel */}
        {msg.sender === 'bot' && msg.sources && msg.sources.length > 0 && (
          <div className="citation-container">
            <span className="citation-title">Sources Cited</span>
            <div className="citation-list">
              {msg.sources.map((src, sIdx) => {
                const baseName = src.split("/").pop() || "source";
                return (
                  <a 
                    key={sIdx} 
                    href={src} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="citation-card"
                  >
                    <FiFileText size={12} /> {baseName}
                  </a>
                );
              })}
            </div>
          </div>
        )}

        {/* Feedback Actions */}
        {msg.sender === 'bot' && msg.text && (
          <div className="feedback-actions">
            <button 
              className={`feedback-btn ${msg.vote === 'up' ? 'active' : ''}`}
              onClick={() => onFeedback(msgIdx, 'up')}
            >
              <FiThumbsUp size={12} /> Upvote
            </button>
            <button 
              className={`feedback-btn down ${msg.vote === 'down' ? 'active' : ''}`}
              onClick={() => onFeedback(msgIdx, 'down')}
            >
              <FiThumbsDown size={12} /> Downvote
            </button>
          </div>
        )}
      </div>
      
      {msg.sender === 'user' && (
        <div className="message-avatar">ME</div>
      )}
    </div>
  );
}
