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

  const inputClass =
    'w-full px-3.5 py-3 bg-paper border border-rule text-ink placeholder:text-ink-soft/70 text-sm outline-none focus:border-oxblood transition-colors';

  return (
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[720px] mx-auto px-6">

          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-4" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
              Join the early access
            </h1>
            <p className="text-ink-soft text-[15px] leading-[1.75] m-0 mb-3.5 max-w-[600px]">
              Delta is built for everyone. But right now it is trained and tested for <strong className="text-ink font-semibold">computer engineering, AI/ML, and cloud computing</strong> students. The architecture is domain-agnostic — it works for any field. We want to expand to design, commerce, arts, medicine, law, and everything in between.
            </p>
            <p className="text-ink-soft text-[15px] leading-[1.75] m-0 mb-8 max-w-[600px]">
              If your domain is not covered yet, sign up below and help us build it.
            </p>
          </motion.div>

          {/* Currently trained */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}
            className="mb-7">
            <p className="kicker m-0 mb-3">Currently trained for</p>
            <div className="flex gap-2.5 flex-wrap">
              {trainedDomains.map((d, i) => {
                const Icon = d.icon;
                return (
                  <div key={i} className="flex items-center gap-2 bg-paper border border-rule px-3.5 py-[9px]">
                    <Icon size={15} className="text-oxblood" />
                    <span className="text-ink text-[13px] font-medium">{d.label}</span>
                  </div>
                );
              })}
              <div className="flex items-center gap-2 bg-accent-surface border border-dashed border-oxblood/40 px-3.5 py-[9px]">
                <Users size={15} className="text-oxblood" />
                <span className="text-oxblood text-[13px] font-medium">Your domain?</span>
              </div>
            </div>
          </motion.div>

          {/* What you get */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}
            className="mb-8">
            <p className="kicker m-0 mb-3">What early access gets you</p>
            <div className="flex flex-col gap-2">
              {[
                'Every unreleased version before public launch',
                'Direct line to the team — your feedback shapes what we build next',
                'A chance to work with us and help expand Delta to your field',
                'Your name in the credits as a founding contributor',
              ].map((perk, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <span className="w-[5px] h-[5px] rounded-full bg-oxblood mt-[7px] shrink-0" />
                  <span className="text-ink-soft text-sm leading-normal">{perk}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Form */}
          <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.45 }}>
            {submitted ? (
              <div className="bg-accent-surface border border-rule px-7 py-8 text-center">
                <p className="font-display text-ink text-xl font-semibold m-0 mb-2">You are in.</p>
                <p className="text-ink-soft text-sm m-0">We have your details. You will hear from us before the next release drops.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="bg-paper border border-rule p-6 flex flex-col gap-3.5">
                <div className="flex gap-3 flex-wrap">
                  <input type="text" placeholder="Name" value={name}
                    onChange={e => setName(e.target.value)} className={inputClass} style={{ flex: '1 1 200px' }} />
                  <input type="email" placeholder="Email *" required value={email}
                    onChange={e => setEmail(e.target.value)} className={inputClass} style={{ flex: '1 1 200px' }} />
                </div>
                <input type="text" placeholder="Your field / domain (e.g. Design, Commerce, Medicine)"
                  value={domain} onChange={e => setDomain(e.target.value)} className={inputClass} />
                <textarea placeholder="What would you want Delta to do for your field? (optional)"
                  value={message} onChange={e => setMessage(e.target.value)} rows={3}
                  className={`${inputClass} resize-y min-h-[80px]`} />
                <button
                  type="submit"
                  disabled={sending || !email.trim()}
                  className={`bg-oxblood text-bone border border-oxblood font-mono text-xs uppercase tracking-[0.14em] px-6 py-3 inline-flex items-center gap-1.5 self-start hover:bg-ink hover:border-ink transition-colors ${sending ? 'cursor-wait' : 'cursor-pointer'} ${!email.trim() ? 'opacity-50' : ''}`}
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
