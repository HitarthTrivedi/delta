import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Send } from 'lucide-react';
import api from '../lib/api';

const Feedback = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [rating, setRating] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setSending(true);
    try {
      await api.post('/feedback', { name, email, message, rating, source: 'feedback' });
    } catch { /* endpoint may not be ready */ }
    setSubmitted(true);
    setSending(false);
    setTimeout(() => { setName(''); setEmail(''); setMessage(''); setRating(0); setSubmitted(false); }, 3000);
  };

  const inputStyle = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8, color: '#fff', padding: '10px 14px', fontSize: 14,
    outline: 'none', width: '100%', fontFamily: "'Inter', sans-serif", transition: 'border-color 0.2s',
  };

  return (
    <section id="feedback" style={{ background: '#000', padding: '5rem 1.5rem' }}>
      <div style={{ maxWidth: 700, margin: '0 auto' }}>

        {/* Beta teaser */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          style={{ borderTop: '1px solid rgba(255,255,255,0.12)', paddingTop: 36, marginBottom: 40 }}
        >
          <h2 style={{
            color: '#fff', fontSize: 'clamp(1.8rem, 3.6vw, 2.5rem)',
            lineHeight: 1.15, fontWeight: 700, margin: '0 0 16px',
          }}>
            Delta is built for everyone. But we need your help to get there.
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.75, margin: '0 0 14px', maxWidth: 620 }}>
            Right now, Delta is trained and tested for <strong style={{ color: 'rgba(255,255,255,0.85)' }}>computer engineering, AI/ML, and cloud computing</strong> students. But the architecture is domain-agnostic — it works for any field. We want to expand to design, commerce, arts, medicine, law, and everything in between.
          </p>
          <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.75, margin: '0 0 24px', maxWidth: 620 }}>
            That is where you come in. If your domain is not covered yet, sign up and help us build it. You will get every unreleased version before anyone else, a chance to work directly with the team, and the knowledge that you helped shape the career OS for your entire field.
          </p>
          <button
            onClick={() => window.location.href = '/early-access'}
            style={{
              background: '#fff', color: '#000', border: 'none', borderRadius: 999,
              padding: '11px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#e5e5e5'}
            onMouseLeave={e => e.currentTarget.style.background = '#fff'}
          >
            Join Early Access <ArrowRight size={14} />
          </button>
        </motion.div>

        {/* Feedback form */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
        >
          <h3 style={{ color: '#fff', fontSize: 20, fontWeight: 650, margin: '0 0 6px' }}>
            Share your feedback
          </h3>
          <p style={{ color: 'rgba(255,255,255,0.42)', fontSize: 14, margin: '0 0 20px' }}>
            Tell us what to improve, fix, or build next.
          </p>

          <form onSubmit={handleSubmit} style={{
            background: '#050505', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10, padding: 24, display: 'flex', flexDirection: 'column', gap: 14,
          }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <input type="text" placeholder="Name (optional)" value={name}
                onChange={e => setName(e.target.value)} style={{ ...inputStyle, flex: '1 1 200px' }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.3)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'} />
              <input type="email" placeholder="Email (optional)" value={email}
                onChange={e => setEmail(e.target.value)} style={{ ...inputStyle, flex: '1 1 200px' }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.3)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'} />
            </div>
            <textarea placeholder="What should we improve, fix, or build next?" value={message}
              onChange={e => setMessage(e.target.value)} rows={3} required
              style={{ ...inputStyle, resize: 'vertical', minHeight: 80 }}
              onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.3)'}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'} />
            <div>
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, margin: '0 0 10px' }}>Rate your experience (optional)</p>
              <div style={{ display: 'flex', gap: 8 }}>
                {[1,2,3,4,5].map(n => (
                  <button key={n} type="button" onClick={() => setRating(n)} style={{
                    width: 34, height: 34, borderRadius: '50%',
                    border: `1px solid ${n <= rating ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.12)'}`,
                    background: n <= rating ? 'rgba(255,255,255,0.12)' : 'transparent',
                    color: n <= rating ? '#fff' : 'rgba(255,255,255,0.3)',
                    fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>{n}</button>
                ))}
              </div>
            </div>
            <button type="submit" disabled={sending || !message.trim()} style={{
              background: submitted ? 'rgba(255,255,255,0.08)' : '#fff',
              color: submitted ? 'rgba(255,255,255,0.7)' : '#000',
              border: submitted ? '1px solid rgba(255,255,255,0.2)' : 'none',
              borderRadius: 999, padding: '10px 22px', fontSize: 14, fontWeight: 600,
              cursor: sending ? 'wait' : 'pointer', display: 'inline-flex', alignItems: 'center',
              gap: 8, alignSelf: 'flex-start', transition: 'all 0.2s',
              opacity: (!message.trim() && !submitted) ? 0.5 : 1,
            }}>
              {submitted ? 'Thanks for your feedback!' : sending ? 'Sending...' : <><Send size={13} /> Submit</>}
            </button>
          </form>
        </motion.div>
      </div>
    </section>
  );
};

export default Feedback;
