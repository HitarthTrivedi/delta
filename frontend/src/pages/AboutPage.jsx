import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, RefreshCw, Award } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const values = [
  {
    icon: ShieldCheck,
    title: 'Honest Progress',
    description: 'We never pretend you are progressing if the evidence says you are not. Every metric, every weekly brief, every portfolio assessment tells you the truth.',
  },
  {
    icon: RefreshCw,
    title: 'Adaptive, Not Rigid',
    description: 'Your plan changes when you change. New interest, new exam, new deadline — Delta replans without losing memory of where you started.',
  },
  {
    icon: Award,
    title: 'Proof Over Claims',
    description: 'Build career weight, not cosmetic completion. Fewer strong projects beat ten weak ones. Delta optimizes for proof recruiters can verify.',
  },
];

export default function AboutPage() {
  return (
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[920px] mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-9"
          >
            <p className="kicker mb-3">
              About Delta
            </p>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-5" style={{ fontSize: 'clamp(2rem, 4.5vw, 3.2rem)' }}>
              Built by students, for students.
            </h1>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.06 }}
            className="max-w-[660px] mb-14"
          >
            <p className="text-ink-soft text-[15px] leading-[1.7] m-0 mb-4">
              Delta was born from a simple frustration: the career advice available to students is either generic, outdated, or locked behind expensive counselors who don't track the market. Students don't fail because they lack motivation — they fail because the future is invisible to them.
            </p>
            <p className="text-ink-soft text-[15px] leading-[1.7] m-0 mb-4">
              Delta makes the invisible visible. It is an AI career operating system that builds a living model of who you are, watches the job market every week, and turns the gap between the two into a personalized roadmap, weekly plan, and portfolio of real proof.
            </p>
            <p className="text-ink-soft text-[15px] leading-[1.7] m-0">
              No generic checklists. No forgotten plans. One system that remembers your story, adapts to your pace, and holds you to honest progress — week after week, for years.
            </p>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.12 }}
            className="font-display text-oxblood text-2xl font-semibold m-0 mb-6"
          >
            Our values
          </motion.h2>

          <div
            className="grid gap-px bg-rule border border-rule"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
          >
            {values.map((value, index) => {
              const Icon = value.icon;
              return (
                <motion.div
                  key={value.title}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.16 + index * 0.06 }}
                  className="bg-paper p-7"
                >
                  <div className="w-10 h-10 border border-rule bg-accent-surface flex items-center justify-center text-oxblood mb-5">
                    <Icon size={18} strokeWidth={1.8} />
                  </div>
                  <h3 className="font-display text-ink text-xl font-semibold m-0 mb-2.5">
                    {value.title}
                  </h3>
                  <p className="text-ink-soft text-sm leading-[1.65] m-0">
                    {value.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
