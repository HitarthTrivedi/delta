import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Code, FlaskConical, Rocket, Users } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';
import api from '../lib/api';

const trainedDomains = [
  { icon: Code, label: 'Computer Engineering' },
  { icon: FlaskConical, label: 'Cloud Computing' },
  { icon: Rocket, label: 'AI / ML Engineering' },
];

export default function EarlyAccessPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [domain, setDomain] = useState('');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    try {
      await api.post('/feedback', {
        name, email,
        message: message || `Early access signup — domain: ${domain || 'not specified'}`,
        source: 'beta_signup',
        meta: { domain, signup: true },
      });
    } catch { /* ok */ }
    setSubmitted(true);
    setSending(false);
  };

  const inputStyle = {
    width: '100%', padding: '12px 14px',
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8, color: '#fff', fontSize: 14, outline: 'none',
    fontFamily: "'Inter', sans-serif",
  };

  return (
    <div style={{ background: '#000', minHeight: '100vh' }}>
      <Header />
      <main style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', padding: '0 1.5rem' }}>

          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
            <h1 style={{ color: '#fff', fontSize: 'clamp(2rem, 4vw, 3rem)', lineHeight: 1.12, fontWeight: 700, margin: '0 0 16px' }}>
              Join the early access
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.75, margin: '0 0 14px', maxWidth: 600 }}>
              Delta is built for everyone. But right now it is trained and tested for <strong style={{ color: 'rgba(255,255,255,0.85)' }}>computer engineering, AI/ML, and cloud computing</strong> students. The architecture is domain-agnostic — it works for any field. We want to expand to design, commerce, arts, medicine, law, and everything in between.
            </p>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.75, margin: '0 0 32px', maxWidth: 600 }}>
              If your domain is not covered yet, sign up below and help us build it.
            </p>
          </motion.div>

          {/* Currently trained */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}
            style={{ marginBottom: 28 }}>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, fontWeight: 600, margin: '0 0 12px' }}>Currently trained for</p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {trainedDomains.map((d, i) => {
                const Icon = d.icon;
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, padding: '9px 14px',
                  }}>
                    <Icon size={15} style={{ color: 'rgba(255,255,255,0.5)' }} />
                    <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 500 }}>{d.label}</span>
                  </div>
                );
              })}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'rgba(255,200,50,0.05)', border: '1px dashed rgba(255,200,50,0.25)',
                borderRadius: 8, padding: '9px 14px',
              }}>
                <Users size={15} style={{ color: 'rgba(255,200,50,0.6)' }} />
                <span style={{ color: 'rgba(255,200,50,0.7)', fontSize: 13, fontWeight: 500 }}>Your domain?</span>
              </div>
            </div>
          </motion.div>

          {/* What you get */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}
            style={{ marginBottom: 32 }}>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, fontWeight: 600, margin: '0 0 12px' }}>What early access gets you</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                'Every unreleased version before public launch',
                'Direct line to the team — your feedback shapes what we build next',
                'A chance to work with us and help expand Delta to your field',
                'Your name in the credits as a founding contributor',
              ].map((perk, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.35)', marginTop: 7, flexShrink: 0 }} />
                  <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 14, lineHeight: 1.5 }}>{perk}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Form */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.45 }}>
            {submitted ? (
              <div style={{
                background: 'rgba(100,255,180,0.05)', border: '1px solid rgba(100,255,180,0.2)',
                borderRadius: 10, padding: '32px 28px', textAlign: 'center',
              }}>
                <p style={{ color: 'rgba(100,255,180,0.9)', fontSize: 18, fontWeight: 600, margin: '0 0 8px' }}>You are in.</p>
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 14, margin: 0 }}>We have your details. You will hear from us before the next release drops.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} style={{
                background: '#050505', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 10, padding: 24, display: 'flex', flexDirection: 'column', gap: 14,
              }}>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <input type="text" placeholder="Name" value={name}
                    onChange={e => setName(e.target.value)} style={{ ...inputStyle, flex: '1 1 200px' }} />
                  <input type="email" placeholder="Email *" required value={email}
                    onChange={e => setEmail(e.target.value)} style={{ ...inputStyle, flex: '1 1 200px' }} />
                </div>
                <input type="text" placeholder="Your field / domain (e.g. Design, Commerce, Medicine)"
                  value={domain} onChange={e => setDomain(e.target.value)} style={inputStyle} />
                <textarea placeholder="What would you want Delta to do for your field? (optional)"
                  value={message} onChange={e => setMessage(e.target.value)} rows={3}
                  style={{ ...inputStyle, resize: 'vertical', minHeight: 80 }} />
                <button type="submit" disabled={sending || !email.trim()} style={{
                  background: '#fff', color: '#000', border: 'none', borderRadius: 999,
                  padding: '11px 24px', fontSize: 14, fontWeight: 600,
                  cursor: sending ? 'wait' : 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
                  opacity: !email.trim() ? 0.5 : 1, transition: 'background 0.2s',
                }}
                  onMouseEnter={e => { if (email.trim()) e.currentTarget.style.background = '#e5e5e5'; }}
                  onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                >
                  {sending ? 'Sending...' : <><Send size={13} /> Join Early Access</>}
                </button>
              </form>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
