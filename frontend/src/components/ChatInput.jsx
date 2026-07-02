import React from 'react';
import { FiSend } from 'react-icons/fi';

export default function ChatInput({
  inputText,
  setInputText,
  isGenerating,
  onSendMessage,
  metrics
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputText.trim() && !isGenerating) {
      onSendMessage(inputText);
    }
  };

  return (
    <section className="input-panel">
      <form onSubmit={handleSubmit} className="input-box-wrapper">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask a campus question (e.g. Minor AI eligibility or Guest room check-in rules)..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isGenerating}
        />
        <button 
          type="submit" 
          className="send-btn" 
          disabled={isGenerating || !inputText.trim()}
          title="Send query"
        >
          <FiSend style={{ marginRight: '8px' }} /> Send Query
        </button>
      </form>
      
      <div className="input-footer-info">
        KGP Insight RAG pipeline is optimized using HNSW vector indexing and Upstash Redis.
        {metrics.lastLatency !== null && (
          <span className="latency-pill">
            Last latency: {metrics.lastLatency}ms {metrics.isCacheHit && "(Cache Hit)"}
          </span>
        )}
      </div>
    </section>
  );
}
