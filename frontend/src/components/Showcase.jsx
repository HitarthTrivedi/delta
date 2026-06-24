import React from 'react';
import { motion } from 'framer-motion';

const features = [
  {
    label: 'Weekly Roadmap',
    title: 'Your AI-powered weekly roadmap',
    description:
      "Delta doesn't dump a year-long checklist. Every week, Agent 2 builds your next set of tasks — courses, projects, practice problems — based on your pace, goals, and what the market demands right now. Talk to it like a tutor and adjust your plan in real time.",
    image: '/ss1.png',
  },
  {
    label: 'Progress Tracking',
    title: 'See exactly where you stand',
    description:
      "Weeks completed, tasks finished, skills gained — all in one view. Delta tracks what you've actually done, not just what you planned. The progress report shows your real momentum so you always know if you're on track.",
    image: '/ss2.png',
  },
  {
    label: 'Resume Enhancer',
    title: 'A resume that evolves with you',
    description:
      "Delta reads market signals and your completed work, then tells you exactly which skills to add to your resume and which ones to replace. No guessing — every suggestion is backed by what recruiters are actually looking for right now.",
    image: '/ss3.png',
  },
];

const Showcase = () => {
  return (
    <section id="showcase" style={{ background: '#000', padding: '5rem 1.5rem 4rem' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          style={{ maxWidth: 660, marginBottom: 52 }}
        >
          <p style={{
            color: 'rgba(255,255,255,0.48)',
            fontSize: 13,
            fontWeight: 600,
            margin: '0 0 12px',
          }}>
            See it in action
          </p>
          <h2 style={{
            color: '#fff',
            fontSize: 'clamp(2rem, 4vw, 3rem)',
            lineHeight: 1.12,
            fontWeight: 700,
            letterSpacing: 0,
            margin: 0,
          }}>
            Everything you need, one screen at a time.
          </h2>
        </motion.div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 72 }}>
          {features.map((feature, index) => {
            const reversed = index % 2 === 1;
            return (
              <motion.div
                key={feature.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.5, delay: 0.08 }}
                style={{
                  display: 'flex',
                  flexDirection: reversed ? 'row-reverse' : 'row',
                  alignItems: 'center',
                  gap: 48,
                  flexWrap: 'wrap',
                }}
                className="showcase-row"
              >
                {/* Screenshot */}
                <div style={{ flex: '1 1 480px', minWidth: 280 }}>
                  <div style={{
                    borderRadius: 12,
                    border: '1px solid rgba(255,255,255,0.1)',
                    overflow: 'hidden',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                    background: '#0a0a0a',
                  }}>
                    <img
                      src={feature.image}
                      alt={feature.label}
                      style={{
                        width: '100%',
                        height: 'auto',
                        display: 'block',
                      }}
                    />
                  </div>
                </div>

                {/* Text */}
                <div style={{ flex: '1 1 340px', minWidth: 260 }}>
                  <span style={{
                    color: 'rgba(255,255,255,0.4)',
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    display: 'block',
                    marginBottom: 12,
                  }}>
                    {feature.label}
                  </span>
                  <h3 style={{
                    color: '#fff',
                    fontSize: 'clamp(1.4rem, 2.8vw, 1.9rem)',
                    lineHeight: 1.2,
                    fontWeight: 680,
                    letterSpacing: 0,
                    margin: '0 0 16px',
                  }}>
                    {feature.title}
                  </h3>
                  <p style={{
                    color: 'rgba(255,255,255,0.5)',
                    fontSize: 15,
                    lineHeight: 1.7,
                    margin: 0,
                  }}>
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .showcase-row {
            flex-direction: column !important;
          }
        }
      `}</style>
    </section>
  );
};

export default Showcase;
