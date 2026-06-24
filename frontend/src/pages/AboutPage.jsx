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
    <div style={{ background: '#000', minHeight: '100vh' }}>
      <Header />
      <main style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: 920, margin: '0 auto', padding: '0 1.5rem' }}>
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 36 }}
          >
            <p style={{
              color: 'rgba(255,255,255,0.48)',
              fontSize: 13,
              fontWeight: 600,
              margin: '0 0 12px',
            }}>
              About Delta
            </p>
            <h1 style={{
              color: '#fff',
              fontSize: 'clamp(2rem, 4.5vw, 3.2rem)',
              lineHeight: 1.12,
              fontWeight: 700,
              margin: '0 0 20px',
            }}>
              Built by students, for students.
            </h1>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.06 }}
            style={{ maxWidth: 660, marginBottom: 56 }}
          >
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.7, margin: '0 0 16px' }}>
              Delta was born from a simple frustration: the career advice available to students is either generic, outdated, or locked behind expensive counselors who don't track the market. Students don't fail because they lack motivation — they fail because the future is invisible to them.
            </p>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.7, margin: '0 0 16px' }}>
              Delta makes the invisible visible. It is an AI career operating system that builds a living model of who you are, watches the job market every week, and turns the gap between the two into a personalized roadmap, weekly plan, and portfolio of real proof.
            </p>
            <p style={{ color: 'rgba(255,255,255,0.52)', fontSize: 15, lineHeight: 1.7, margin: 0 }}>
              No generic checklists. No forgotten plans. One system that remembers your story, adapts to your pace, and holds you to honest progress — week after week, for years.
            </p>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.12 }}
            style={{
              color: '#fff',
              fontSize: 22,
              fontWeight: 680,
              margin: '0 0 24px',
            }}
          >
            Our values
          </motion.h2>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 1,
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.1)',
          }}>
            {values.map((value, index) => {
              const Icon = value.icon;
              return (
                <motion.div
                  key={value.title}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.16 + index * 0.06 }}
                  style={{ background: '#050505', padding: 28 }}
                >
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.14)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    marginBottom: 20,
                    background: 'rgba(255,255,255,0.04)',
                  }}>
                    <Icon size={18} strokeWidth={1.8} />
                  </div>
                  <h3 style={{ color: '#fff', fontSize: 18, fontWeight: 650, margin: '0 0 10px' }}>
                    {value.title}
                  </h3>
                  <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1.65, margin: 0 }}>
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
