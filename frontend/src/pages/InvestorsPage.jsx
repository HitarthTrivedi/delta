import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Lock, ArrowRight, Eye, Users, Globe, Zap } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const highlights = [
  { icon: Users, stat: '40M+', label: 'Indian higher-ed students — our entry wedge' },
  { icon: Globe, stat: '$300B+', label: 'Global career-services & upskilling market' },
  { icon: Zap, stat: '3-Agent', label: 'AI engine: intake, roadmap, progress — all connected' },
  { icon: TrendingUp, stat: 'Weekly', label: 'Market pulse + adaptive plan = compounding advantage' },
];

const pitchSections = [
  {
    title: 'The Problem',
    content: 'Every year, hundreds of millions of students make the most important decision of their lives — what to become — with almost no real information. They Google "best skills 2026" and get listicles. They buy expensive courses and finish them with no idea if it mattered. They ask ChatGPT for a roadmap and get a generic plan that forgets them the moment they close the tab. Nobody is connecting three things that must be connected: who you are, what the market wants right now, and what you should do this week.',
  },
  {
    title: 'The Solution',
    content: 'Delta is an AI Career Operating System. One intake conversation builds a deep understanding of the student. A living Career Memory Vault remembers everything. A weekly Market Pulse reads the real job market. A Central Engine fuses the two into a personalized roadmap, weekly plan, project proof, and resume — then adapts without amnesia when the student changes. Every feature asks the same question: "Given who this person is and what the market is doing today, what should happen next?"',
  },
  {
    title: 'Why We Win',
    content: 'Delta runs a dual-model AI engine — frontier accuracy for critical extraction, efficient models for high-frequency conversation. Structural cost advantage that compounds at scale. The Career Memory Vault is the data moat: the longer you use Delta, the smarter it gets and the harder it is to leave. ChatGPT forgets you. Coursera sells content and walks away. LinkedIn shows jobs you are not ready for. Delta is the only system that closes the loop between you, the market, and this week.',
  },
  {
    title: 'Business Model',
    content: 'Freemium intake + roadmap hooks every student on day one. Delta Pro subscription unlocks the weekly loop, market pulse, unlimited career chat, ATS resume engine, and portfolio assessment. Domain Packs extend into Data/AI, Design, Product, and Finance verticals. B2B2C licensing to colleges and bootcamps provides distribution. The talent marketplace — once Delta knows who is genuinely job-ready with proof — is a second, larger company hiding inside the first.',
  },
  {
    title: 'The Vision',
    content: 'Phase 1: Own the wedge — become the default career OS for Indian CS and engineering students. Phase 2: Generalize — domain packs for every ambitious field. Phase 3: Become infrastructure — the career memory layer that follows a person from their first year of college through every job change for the next 40 years. Your career will have one continuous brain. It will be Delta.',
  },
];

export default function InvestorsPage() {
  const [form, setForm] = useState({ name: '', email: '', firm: '', role: '' });
  const [unlocked, setUnlocked] = useState(false);

  const handleUnlock = (e) => {
    e.preventDefault();
    if (form.name.trim() && form.email.trim()) {
      setUnlocked(true);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '12px 14px',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    color: '#fff',
    fontSize: 14,
    outline: 'none',
    fontFamily: "'Inter', sans-serif",
  };

  return (
    <div style={{ background: '#000', minHeight: '100vh' }}>
      <Header />
      <main style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: 920, margin: '0 auto', padding: '0 1.5rem' }}>

          {/* Hero */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 48 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <TrendingUp size={22} style={{ color: 'rgba(255,255,255,0.5)' }} />
              <p style={{ color: 'rgba(255,255,255,0.48)', fontSize: 13, fontWeight: 600, margin: 0 }}>
                For Investors
              </p>
            </div>
            <h1 style={{ color: '#fff', fontSize: 'clamp(2rem, 4vw, 3rem)', lineHeight: 1.12, fontWeight: 700, margin: '0 0 16px' }}>
              The missing brain for every career
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 16, lineHeight: 1.7, maxWidth: 640, margin: 0 }}>
              Delta is building the AI career operating system for the next billion students. A working product, a clear wedge, and a category waiting to be defined.
            </p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 16, marginBottom: 48,
            }}
          >
            {highlights.map((h, i) => {
              const Icon = h.icon;
              return (
                <div key={i} style={{
                  background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 10, padding: '22px 20px', textAlign: 'center',
                }}>
                  <Icon size={20} style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 10 }} />
                  <p style={{ color: '#fff', fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>{h.stat}</p>
                  <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13, margin: 0, lineHeight: 1.4 }}>{h.label}</p>
                </div>
              );
            })}
          </motion.div>

          {/* Gate or pitch */}
          {!unlocked ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45 }}
            >
              <div style={{
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12, padding: '36px 28px', maxWidth: 480, margin: '0 auto', textAlign: 'center',
              }}>
                <Lock size={28} style={{ color: 'rgba(255,255,255,0.35)', marginBottom: 16 }} />
                <h2 style={{ color: '#fff', fontSize: 20, fontWeight: 650, margin: '0 0 6px' }}>
                  View the full pitch
                </h2>
                <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14, margin: '0 0 24px', lineHeight: 1.6 }}>
                  Enter your details to access Delta's investor pitch — the full vision, market thesis, architecture, and business model.
                </p>

                <form onSubmit={handleUnlock} style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
                  <input style={inputStyle} placeholder="Your name *" required
                    value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  <input style={inputStyle} placeholder="Email address *" type="email" required
                    value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                  <input style={inputStyle} placeholder="Firm / company (optional)"
                    value={form.firm} onChange={e => setForm(f => ({ ...f, firm: e.target.value }))} />
                  <input style={inputStyle} placeholder="Your role (optional)"
                    value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} />
                  <button type="submit" style={{
                    background: '#fff', color: '#000', border: 'none', borderRadius: 999,
                    padding: '12px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                    width: '100%', marginTop: 4, transition: 'background 0.2s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = '#e5e5e5'}
                    onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                  >
                    <Eye size={14} /> View Pitch
                  </button>
                </form>
              </div>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div style={{
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 12, padding: '8px 12px', marginBottom: 32, display: 'inline-flex',
                alignItems: 'center', gap: 8,
              }}>
                <Eye size={14} style={{ color: 'rgba(255,255,255,0.5)' }} />
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
                  Viewing as {form.name} ({form.email})
                </span>
              </div>

              {pitchSections.map((section, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.04 }}
                  style={{
                    borderTop: i === 0 ? 'none' : '1px solid rgba(255,255,255,0.08)',
                    padding: '28px 0',
                  }}
                >
                  <h2 style={{ color: '#fff', fontSize: 22, fontWeight: 650, margin: '0 0 12px' }}>
                    {section.title}
                  </h2>
                  <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: 15, lineHeight: 1.75, margin: 0 }}>
                    {section.content}
                  </p>
                </motion.div>
              ))}

              {/* CTA */}
              <div style={{
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12, padding: '28px 24px', marginTop: 16, textAlign: 'center',
              }}>
                <h3 style={{ color: '#fff', fontSize: 18, fontWeight: 600, margin: '0 0 8px' }}>
                  Interested in Delta?
                </h3>
                <p style={{ color: 'rgba(255,255,255,0.48)', fontSize: 14, margin: '0 0 18px' }}>
                  We are raising to turn a working product into a category. Let's talk.
                </p>
                <a href="mailto:hitartht318@gmail.com?subject=Delta%20Investment%20Inquiry" style={{
                  background: '#fff', color: '#000', border: 'none', borderRadius: 999,
                  padding: '11px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: 6, textDecoration: 'none',
                  transition: 'background 0.2s',
                }}>
                  Contact the founder <ArrowRight size={14} />
                </a>
              </div>
            </motion.div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
