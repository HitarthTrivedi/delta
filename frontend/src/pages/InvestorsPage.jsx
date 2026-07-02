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

  const inputClass =
    'w-full px-3.5 py-3 bg-paper border border-rule text-ink placeholder:text-ink-soft/70 text-sm outline-none focus:border-oxblood transition-colors';

  return (
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[920px] mx-auto px-6">

          {/* Hero */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-12"
          >
            <div className="flex items-center gap-2.5 mb-3.5">
              <TrendingUp size={22} className="text-oxblood" />
              <p className="kicker m-0">
                For Investors
              </p>
            </div>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-4" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
              The missing brain for every career
            </h1>
            <p className="text-ink-soft text-base leading-[1.7] max-w-[640px] m-0">
              Delta is building the AI career operating system for the next billion students. A working product, a clear wedge, and a category waiting to be defined.
            </p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="grid gap-px bg-rule border border-rule mb-12"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
          >
            {highlights.map((h, i) => {
              const Icon = h.icon;
              return (
                <div key={i} className="bg-paper px-5 py-[22px] text-center">
                  <Icon size={20} className="text-oxblood mb-2.5 inline-block" />
                  <p className="font-display text-ink text-[1.75rem] font-semibold m-0 mb-1">{h.stat}</p>
                  <p className="text-ink-soft text-[13px] leading-[1.4] m-0">{h.label}</p>
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
              <div className="bg-paper border border-rule px-7 py-9 max-w-[480px] mx-auto text-center">
                <Lock size={28} className="text-ink-soft mb-4 inline-block" />
                <h2 className="font-display text-oxblood text-2xl font-semibold m-0 mb-1.5">
                  View the full pitch
                </h2>
                <p className="text-ink-soft text-sm leading-[1.6] m-0 mb-6">
                  Enter your details to access Delta's investor pitch — the full vision, market thesis, architecture, and business model.
                </p>

                <form onSubmit={handleUnlock} className="flex flex-col gap-3 text-left">
                  <input className={inputClass} placeholder="Your name *" required
                    value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  <input className={inputClass} placeholder="Email address *" type="email" required
                    value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                  <input className={inputClass} placeholder="Firm / company (optional)"
                    value={form.firm} onChange={e => setForm(f => ({ ...f, firm: e.target.value }))} />
                  <input className={inputClass} placeholder="Your role (optional)"
                    value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} />
                  <button
                    type="submit"
                    className="bg-oxblood text-bone border border-oxblood font-mono text-xs uppercase tracking-[0.14em] px-6 py-3 cursor-pointer inline-flex items-center justify-center gap-1.5 w-full mt-1 hover:bg-ink hover:border-ink transition-colors"
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
              <div className="bg-paper border border-rule px-3 py-2 mb-8 inline-flex items-center gap-2">
                <Eye size={14} className="text-ink-soft" />
                <span className="font-mono text-[12px] text-ink-soft">
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
                  className={`py-7 ${i === 0 ? '' : 'border-t border-rule'}`}
                >
                  <h2 className="font-display text-oxblood text-2xl font-semibold m-0 mb-3">
                    {section.title}
                  </h2>
                  <p className="text-ink-soft text-[15px] leading-[1.75] m-0">
                    {section.content}
                  </p>
                </motion.div>
              ))}

              {/* CTA */}
              <div className="bg-accent-surface border border-rule px-6 py-7 mt-4 text-center">
                <h3 className="font-display text-ink text-xl font-semibold m-0 mb-2">
                  Interested in Delta?
                </h3>
                <p className="text-ink-soft text-sm m-0 mb-4">
                  We are raising to turn a working product into a category. Let's talk.
                </p>
                <a
                  href="mailto:hitartht318@gmail.com?subject=Delta%20Investment%20Inquiry"
                  className="bg-oxblood text-bone border border-oxblood font-mono text-xs uppercase tracking-[0.14em] px-6 py-3 cursor-pointer inline-flex items-center gap-1.5 no-underline hover:bg-ink hover:border-ink transition-colors"
                >
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
