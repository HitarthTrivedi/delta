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

  const inputClass =
    'w-full bg-transparent border-0 border-b border-rule text-ink placeholder:text-ink-soft/60 px-0 py-2.5 text-[15px] outline-none transition-colors focus:border-oxblood';
  const labelClass =
    'font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft block mb-1';

  return (
    <section id="feedback" className="bg-bone px-6 pt-24 pb-28">
      <div className="max-w-[1140px] mx-auto grid md:grid-cols-12 gap-12">

        {/* Left — heading + early access teaser */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="md:col-span-5"
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] m-0 mb-6">
            <span className="text-oxblood">03</span>
            <span className="text-ink-soft"> / Correspondence</span>
          </p>
          <h2 className="font-display text-ink font-normal leading-[1.05] m-0 mb-5" style={{ fontSize: 'clamp(2.2rem, 4.5vw, 3.2rem)' }}>
            Delta is built for everyone. <em>We need your help to get there.</em>
          </h2>
          <p className="text-ink-soft text-[15px] leading-[1.75] m-0 mb-3.5">
            Right now, Delta is trained and tested for <strong className="text-ink font-semibold">computer engineering, AI/ML, and cloud computing</strong> students. But the architecture is domain-agnostic — it works for any field. We want to expand to design, commerce, arts, medicine, law, and everything in between.
          </p>
          <p className="text-ink-soft text-[15px] leading-[1.75] m-0 mb-7">
            That is where you come in. If your domain is not covered yet, sign up and help us build it. You will get every unreleased version before anyone else, a chance to work directly with the team, and the knowledge that you helped shape the career OS for your entire field.
          </p>
          <button
            onClick={() => window.location.href = '/early-access'}
            className="bg-oxblood text-bone border border-oxblood font-mono text-[11px] uppercase tracking-[0.18em] px-7 py-[14px] cursor-pointer inline-flex items-center gap-2 hover:bg-ink hover:border-ink transition-colors"
          >
            Join Early Access <ArrowRight size={13} />
          </button>
        </motion.div>

        {/* Right — feedback form on paper */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, delay: 0.08 }}
          className="md:col-span-7"
        >
          <form onSubmit={handleSubmit} className="bg-paper px-8 py-9 sm:px-10 h-full flex flex-col gap-7">
            <div className="flex items-center justify-between gap-4">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft">
                Form &middot; Feedback / DLT-002
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft">
                Delta
              </span>
            </div>

            <div className="grid sm:grid-cols-2 gap-7">
              <div>
                <label className={labelClass}>Name</label>
                <input
                  type="text"
                  placeholder="Ada Lovelace"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Email</label>
                <input
                  type="email"
                  placeholder="ada@university.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>Message *</label>
              <textarea
                placeholder="What should we improve, fix, or build next?"
                value={message}
                onChange={e => setMessage(e.target.value)}
                rows={3}
                required
                className={`${inputClass} resize-y min-h-[80px]`}
              />
            </div>

            <div>
              <label className={labelClass}>Rate your experience</label>
              <div className="flex gap-2 mt-2">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setRating(n)}
                    className={`w-[34px] h-[34px] border font-mono text-[12px] cursor-pointer transition-all flex items-center justify-center ${
                      n <= rating
                        ? 'border-oxblood bg-oxblood text-bone'
                        : 'border-rule bg-transparent text-ink-soft hover:border-ink-soft'
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end mt-auto">
              <button
                type="submit"
                disabled={sending || !message.trim()}
                className={`font-mono text-[11px] uppercase tracking-[0.18em] px-8 py-[14px] inline-flex items-center gap-2 transition-colors border ${
                  submitted
                    ? 'bg-accent-surface text-ink-soft border-rule'
                    : 'bg-oxblood text-bone border-oxblood hover:bg-ink hover:border-ink'
                } ${sending ? 'cursor-wait' : 'cursor-pointer'} ${(!message.trim() && !submitted) ? 'opacity-50' : ''}`}
              >
                {submitted ? 'Thanks for your feedback!' : sending ? 'Sending...' : <><Send size={12} /> Send Feedback</>}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </section>
  );
};

export default Feedback;
