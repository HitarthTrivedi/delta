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
    <div style={{ background: '#000', minHeight: '100vh' }}>
      <Header />
      <main style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: 920, margin: '0 auto', padding: '0 1.5rem' }}>
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            style={{ marginBottom: 14 }}
          >
            <p style={{
              color: 'rgba(255,255,255,0.48)',
              fontSize: 13,
              fontWeight: 600,
              margin: '0 0 12px',
            }}>
              Careers
            </p>
            <h1 style={{
              color: '#fff',
              fontSize: 'clamp(2rem, 4.5vw, 3.2rem)',
              lineHeight: 1.12,
              fontWeight: 700,
              margin: '0 0 14px',
            }}>
              Join the mission.
            </h1>
            <p style={{
              color: 'rgba(255,255,255,0.52)',
              fontSize: 15,
              lineHeight: 1.7,
              maxWidth: 580,
              margin: '0 0 40px',
            }}>
              Delta is built by a small, fast-moving team. We are looking for people who care about making career guidance honest and accessible.
            </p>
          </motion.div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: 1,
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.1)',
            marginBottom: 36,
          }}>
            {roles.map((role, index) => {
              const Icon = role.icon;
              return (
                <motion.div
                  key={role.title}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.08 + index * 0.06 }}
                  style={{
                    background: '#050505',
                    padding: 28,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 16,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{
                      width: 40,
                      height: 40,
                      borderRadius: 8,
                      border: '1px solid rgba(255,255,255,0.14)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      background: 'rgba(255,255,255,0.04)',
                    }}>
                      <Icon size={18} strokeWidth={1.8} />
                    </div>
                    <span style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'rgba(255,255,255,0.4)',
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 999,
                      padding: '3px 10px',
                      letterSpacing: '0.04em',
                    }}>
                      Coming Soon
                    </span>
                  </div>
                  <div>
                    <h3 style={{ color: '#fff', fontSize: 18, fontWeight: 650, margin: '0 0 8px' }}>
                      {role.title}
                    </h3>
                    <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1.65, margin: 0 }}>
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
            style={{ color: 'rgba(255,255,255,0.44)', fontSize: 14, margin: 0 }}
          >
            Interested? Reach out at{' '}
            <a
              href="mailto:hitartht318@gmail.com"
              style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'underline', textUnderlineOffset: 3 }}
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
