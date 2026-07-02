import React from 'react';
import MessageBubble from './MessageBubble';

const SUGGESTIONS = [
  {
    tag: "Hostel Allotments",
    question: "How do hostel allotments work?",
    desc: "Check guest accommodation limits and warden rules."
  },
  {
    tag: "Academic Calendar",
    question: "When is the next Senate meeting?",
    desc: "Scan calendar deadlines and academic schedules."
  },
  {
    tag: "ERP Guidelines",
    question: "How do I apply for a minor in AI?",
    desc: "Check CGPA requirements and registration slots."
  },
  {
    tag: "Campus Rules",
    question: "What are the fine rules for heavy appliances?",
    desc: "Find out HMC guidelines on electrical items."
  }
];

export default function ChatFeed({ 
  messages, 
  isGenerating, 
  onSendMessage, 
  onFeedback, 
  feedRef 
}) {
  return (
    <section className="chat-feed" ref={feedRef}>
      {messages.length === 0 ? (
        <div className="welcome-screen">
          <div className="welcome-logo">🎓</div>
          <h2>Welcome to KGP Insight</h2>
          <p>
            Ask natural language queries regarding the IIT KGP academic curriculum, 
            minor requirements, calendar schedules, or HMC hostel guidelines.
          </p>
          
          <div className="suggestion-grid">
            {SUGGESTIONS.map((s, idx) => (
              <div 
                key={idx} 
                className="suggestion-card glass" 
                onClick={() => onSendMessage(s.question)}
              >
                <h4>{s.tag}</h4>
                <p>{s.question}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        messages.map((msg, idx) => (
          <MessageBubble 
            key={idx} 
            msg={msg} 
            msgIdx={idx} 
            onFeedback={onFeedback} 
          />
        ))
      )}
    </section>
  );
}
