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
    <section id="showcase" className="bg-bone px-6 pt-28 pb-20">
      <div className="max-w-[1140px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="max-w-[760px] mb-16"
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] m-0 mb-6">
            <span className="text-oxblood">01</span>
            <span className="text-ink-soft"> / See it in action</span>
          </p>
          <h2 className="font-display text-ink font-normal leading-[1.05] m-0 mb-5" style={{ fontSize: 'clamp(2.2rem, 5vw, 3.6rem)' }}>
            Everything you need, <em>one screen at a time.</em>
          </h2>
        </motion.div>

        <div className="flex flex-col gap-[72px]">
          {features.map((feature, index) => {
            const reversed = index % 2 === 1;
            return (
              <motion.div
                key={feature.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.5, delay: 0.08 }}
                className={`showcase-row flex items-center gap-12 flex-wrap ${reversed ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Screenshot */}
                <div className="min-w-[280px]" style={{ flex: '1 1 480px' }}>
                  <div className="border border-rule overflow-hidden bg-paper">
                    <img
                      src={feature.image}
                      alt={feature.label}
                      className="w-full h-auto block"
                    />
                  </div>
                </div>

                {/* Text */}
                <div className="min-w-[260px]" style={{ flex: '1 1 340px' }}>
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-oxblood block mb-4">
                    Feature &middot; 0{index + 1} &mdash; {feature.label}
                  </span>
                  <h3 className="font-display text-ink leading-[1.15] font-medium m-0 mb-4" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.1rem)' }}>
                    {feature.title}
                  </h3>
                  <p className="text-ink-soft text-[15px] leading-[1.7] m-0">
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
