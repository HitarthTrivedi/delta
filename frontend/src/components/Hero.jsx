import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const facts = [
  { label: 'Intake', value: 'One conversation' },
  { label: 'Planner', value: 'Adaptive, weekly' },
  { label: 'Progress', value: 'Honest, for years' },
];

const Hero = () => {
  return (
    <section id="cover" className="relative min-h-screen bg-bone flex flex-col justify-center px-6 pt-28 pb-8">
      <div className="max-w-[1140px] mx-auto w-full grid md:grid-cols-12 gap-12 items-center">

        {/* Left — headline block */}
        <div className="md:col-span-7">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="font-mono text-[11px] uppercase tracking-[0.22em] mb-8"
          >
            <span className="text-oxblood">00</span>
            <span className="text-ink-soft"> / The AI Career Operating System</span>
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.08 }}
            className="font-display text-ink font-normal leading-[0.98] m-0 mb-8"
            style={{ fontSize: 'clamp(3.5rem, 9vw, 7rem)' }}
          >
            F#CK COLLEGE!<br />
            <em className="font-medium">Delta is here.</em>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.16 }}
            className="text-ink-soft text-[1.05rem] leading-[1.7] max-w-[480px] m-0"
          >
            One intake conversation, one adaptive weekly planner, and one progress
            report page that keeps your roadmap honest for years.
          </motion.p>
        </div>

        {/* Right — facts column, vertical rule */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.24 }}
          className="md:col-span-4 md:col-start-9 md:border-l md:border-rule md:pl-10 flex flex-col gap-7"
        >
          {facts.map((f) => (
            <div key={f.label}>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft m-0 mb-1.5">
                {f.label}
              </p>
              <p className="font-display text-ink text-[1.45rem] font-medium m-0">
                {f.value}
              </p>
            </div>
          ))}

          <div className="flex flex-col gap-3 mt-2">
            <button
              onClick={() => window.location.href = '/intake'}
              id="hero-get-started"
              className="bg-oxblood text-bone border border-oxblood font-mono text-[11px] uppercase tracking-[0.18em] px-7 py-[15px] cursor-pointer flex items-center justify-center gap-2 hover:bg-ink hover:border-ink transition-colors"
            >
              Get Started <ArrowRight size={13} />
            </button>
            <button
              onClick={() => window.location.href = '/roadmap'}
              id="hero-watch-demo"
              className="bg-transparent text-ink border border-ink font-mono text-[11px] uppercase tracking-[0.18em] px-7 py-[14px] cursor-pointer flex items-center justify-center gap-2 hover:bg-ink hover:text-bone transition-colors"
            >
              View Roadmap
            </button>
          </div>
        </motion.div>
      </div>

      {/* Bottom meta bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="max-w-[1140px] mx-auto w-full border-t border-rule mt-20 pt-4 flex items-center justify-between gap-4 flex-wrap"
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          Delta &mdash; Career OS &nbsp;&#8470;&nbsp; 00 &mdash; Cover
        </span>
        <span className="hidden sm:inline font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          Made with purpose for students everywhere.
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          Scroll &darr;
        </span>
      </motion.div>
    </section>
  );
};

export default Hero;
