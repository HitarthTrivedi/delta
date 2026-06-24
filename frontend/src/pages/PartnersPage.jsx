import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Handshake, BookOpen, BarChart3, ShieldCheck, Send } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const benefits = [
  {
    icon: BarChart3,
    title: 'Targeted Reach',
    description: 'Your courses are recommended only to students whose profile, goals, and current phase make them the right fit — not blasted to everyone.',
  },
  {
    icon: ShieldCheck,
    title: 'Quality-First Curation',
    description: 'Delta reviews every course before adding it to our recommendation pool. Students trust Delta because we never push paid content without vetting it.',
  },
  {
    icon: BookOpen,
    title: 'Context-Aware Placement',
    description: 'Courses appear inside the weekly roadmap at the exact moment the student needs them — not buried in a marketplace with ten thousand alternatives.',
  },
];

export default function PartnersPage() {
  const [form, setForm] = useState({ company: '', name: '', email: '', website: '', message: '' });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    setForm({ company: '', name: '', email: '', website: '', message: '' });
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

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 48 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <Handshake size={22} style={{ color: 'rgba(255,255,255,0.5)' }} />
              <p style={{ color: 'rgba(255,255,255,0.48)', fontSize: 13, fontWeight: 600, margin: 0 }}>
                Course Partners
              </p>
            </div>
            <h1 style={{ color: '#fff', fontSize: 'clamp(2rem, 4vw, 3rem)', lineHeight: 1.12, fontWeight: 700, margin: '0 0 16px' }}>
              Get your courses in front of the right students
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 16, lineHeight: 1.7, maxWidth: 640, margin: 0 }}>
              Delta recommends courses, certifications, and learning resources to thousands of students as part of their personalized weekly roadmap. We partner with platforms like Coursera, Udemy, and independent creators who want their best content to reach students at the perfect moment in their learning journey.
            </p>
          </motion.div>

          {/* How it works for partners */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 48 }}
          >
            <h2 style={{ color: '#fff', fontSize: 22, fontWeight: 650, margin: '0 0 6px' }}>
              How partnering works
            </h2>
            <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14, lineHeight: 1.7, margin: '0 0 24px' }}>
              We review your courses, verify quality, and integrate them into Delta's recommendation engine.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
              {['Submit your course catalog', 'Delta reviews and curates', 'Students get matched automatically'].map((step, i) => (
                <div key={i} style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 10,
                  padding: '22px 20px',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12, fontWeight: 700, display: 'block', marginBottom: 10 }}>
                    Step {i + 1}
                  </span>
                  <p style={{ color: '#fff', fontSize: 15, fontWeight: 550, margin: 0 }}>{step}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Benefits */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 48 }}
          >
            <h2 style={{ color: '#fff', fontSize: 22, fontWeight: 650, margin: '0 0 24px' }}>
              Why partner with Delta
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
              {benefits.map((b, i) => {
                const Icon = b.icon;
                return (
                  <div key={i} style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 10,
                    padding: '24px 20px',
                  }}>
                    <Icon size={20} style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 14 }} />
                    <h3 style={{ color: '#fff', fontSize: 16, fontWeight: 600, margin: '0 0 8px' }}>{b.title}</h3>
                    <p style={{ color: 'rgba(255,255,255,0.48)', fontSize: 14, lineHeight: 1.6, margin: 0 }}>{b.description}</p>
                  </div>
                );
              })}
            </div>
          </motion.div>

          {/* Partner inquiry form */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
          >
            <div style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              padding: '32px 28px',
              maxWidth: 560,
            }}>
              <h2 style={{ color: '#fff', fontSize: 20, fontWeight: 650, margin: '0 0 6px' }}>
                Reach out to partner
              </h2>
              <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14, margin: '0 0 24px' }}>
                Tell us about your platform and courses. We will review and get back to you.
              </p>

              {submitted ? (
                <p style={{ color: 'rgba(100,255,180,0.9)', fontSize: 15, fontWeight: 500 }}>
                  Thanks for reaching out. We will review your submission and get back to you soon.
                </p>
              ) : (
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <input style={inputStyle} placeholder="Company / Platform name" required
                    value={form.company} onChange={e => setForm(f => ({ ...f, company: e.target.value }))} />
                  <input style={inputStyle} placeholder="Your name"
                    value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  <input style={inputStyle} placeholder="Email address" type="email" required
                    value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                  <input style={inputStyle} placeholder="Website URL"
                    value={form.website} onChange={e => setForm(f => ({ ...f, website: e.target.value }))} />
                  <textarea style={{ ...inputStyle, minHeight: 90, resize: 'vertical' }}
                    placeholder="Tell us about your courses and how you'd like to partner"
                    value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} />
                  <button type="submit" style={{
                    background: '#fff', color: '#000', border: 'none', borderRadius: 999,
                    padding: '11px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                    display: 'inline-flex', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
                    transition: 'background 0.2s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = '#e5e5e5'}
                    onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                  >
                    Submit inquiry <Send size={13} />
                  </button>
                </form>
              )}
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
