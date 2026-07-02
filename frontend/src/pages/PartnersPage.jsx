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

  const inputClass =
    'w-full px-3.5 py-3 bg-paper border border-rule text-ink placeholder:text-ink-soft/70 text-sm outline-none focus:border-oxblood transition-colors';

  return (
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[920px] mx-auto px-6">

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-12"
          >
            <div className="flex items-center gap-2.5 mb-3.5">
              <Handshake size={22} className="text-oxblood" />
              <p className="kicker m-0">
                Course Partners
              </p>
            </div>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-4" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
              Get your courses in front of the right students
            </h1>
            <p className="text-ink-soft text-base leading-[1.7] max-w-[640px] m-0">
              Delta recommends courses, certifications, and learning resources to thousands of students as part of their personalized weekly roadmap. We partner with platforms like Coursera, Udemy, and independent creators who want their best content to reach students at the perfect moment in their learning journey.
            </p>
          </motion.div>

          {/* How it works for partners */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="mb-12"
          >
            <h2 className="font-display text-oxblood text-2xl font-semibold m-0 mb-1.5">
              How partnering works
            </h2>
            <p className="text-ink-soft text-sm leading-[1.7] m-0 mb-6">
              We review your courses, verify quality, and integrate them into Delta's recommendation engine.
            </p>

            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
              {['Submit your course catalog', 'Delta reviews and curates', 'Students get matched automatically'].map((step, i) => (
                <div key={i} className="bg-paper border border-rule px-5 py-[22px]">
                  <span className="kicker block mb-2.5" style={{ color: 'var(--oxblood)' }}>
                    Step {i + 1}
                  </span>
                  <p className="font-display text-ink text-lg font-semibold m-0">{step}</p>
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
            className="mb-12"
          >
            <h2 className="font-display text-oxblood text-2xl font-semibold m-0 mb-6">
              Why partner with Delta
            </h2>
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
              {benefits.map((b, i) => {
                const Icon = b.icon;
                return (
                  <div key={i} className="bg-paper border border-rule px-5 py-6">
                    <Icon size={20} className="text-oxblood mb-3.5" />
                    <h3 className="font-display text-ink text-lg font-semibold m-0 mb-2">{b.title}</h3>
                    <p className="text-ink-soft text-sm leading-[1.6] m-0">{b.description}</p>
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
            <div className="bg-paper border border-rule px-7 py-8 max-w-[560px]">
              <h2 className="font-display text-oxblood text-xl font-semibold m-0 mb-1.5">
                Reach out to partner
              </h2>
              <p className="text-ink-soft text-sm m-0 mb-6">
                Tell us about your platform and courses. We will review and get back to you.
              </p>

              {submitted ? (
                <p className="text-oxblood text-[15px] font-medium">
                  Thanks for reaching out. We will review your submission and get back to you soon.
                </p>
              ) : (
                <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
                  <input className={inputClass} placeholder="Company / Platform name" required
                    value={form.company} onChange={e => setForm(f => ({ ...f, company: e.target.value }))} />
                  <input className={inputClass} placeholder="Your name"
                    value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  <input className={inputClass} placeholder="Email address" type="email" required
                    value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                  <input className={inputClass} placeholder="Website URL"
                    value={form.website} onChange={e => setForm(f => ({ ...f, website: e.target.value }))} />
                  <textarea className={`${inputClass} min-h-[90px] resize-y`}
                    placeholder="Tell us about your courses and how you'd like to partner"
                    value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} />
                  <button
                    type="submit"
                    className="bg-oxblood text-bone border border-oxblood font-mono text-xs uppercase tracking-[0.14em] px-6 py-3 cursor-pointer inline-flex items-center gap-1.5 self-start hover:bg-ink hover:border-ink transition-colors"
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
