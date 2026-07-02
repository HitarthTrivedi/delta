import React from 'react';
import { motion } from 'framer-motion';
import { Code2, Brain, Palette } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const roles = [
  {
    icon: Code2,
    title: 'Full-Stack Engineer',
    description: 'Build the platform that powers weekly career intelligence for thousands of students.',
  },
  {
    icon: Brain,
    title: 'AI/ML Engineer',
    description: 'Design the multi-agent system that understands students, reads the market, and plans their weeks.',
  },
  {
    icon: Palette,
    title: 'Product Designer',
    description: 'Shape how students interact with their career data — making complexity feel simple and personal.',
  },
];

export default function CareersPage() {
  return (
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[920px] mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-3.5"
          >
            <p className="kicker mb-3">
              Careers
            </p>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-3.5" style={{ fontSize: 'clamp(2rem, 4.5vw, 3.2rem)' }}>
              Join the mission.
            </h1>
            <p className="text-ink-soft text-[15px] leading-[1.7] max-w-[580px] m-0 mb-10">
              Delta is built by a small, fast-moving team. We are looking for people who care about making career guidance honest and accessible.
            </p>
          </motion.div>

          <div
            className="grid gap-px bg-rule border border-rule mb-9"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}
          >
            {roles.map((role, index) => {
              const Icon = role.icon;
              return (
                <motion.div
                  key={role.title}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.08 + index * 0.06 }}
                  className="bg-paper p-7 flex flex-col gap-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 border border-rule bg-accent-surface flex items-center justify-center text-oxblood">
                      <Icon size={18} strokeWidth={1.8} />
                    </div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-soft border border-rule px-2.5 py-1">
                      Coming Soon
                    </span>
                  </div>
                  <div>
                    <h3 className="font-display text-ink text-xl font-semibold m-0 mb-2">
                      {role.title}
                    </h3>
                    <p className="text-ink-soft text-sm leading-[1.65] m-0">
                      {role.description}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="text-ink-soft text-sm m-0"
          >
            Interested? Reach out at{' '}
            <a
              href="mailto:hitartht318@gmail.com"
              className="text-oxblood underline underline-offset-4"
            >
              hitartht318@gmail.com
            </a>
          </motion.p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
