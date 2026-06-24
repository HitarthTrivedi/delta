import React from 'react';
import { motion } from 'framer-motion';
import { Mail, Github, Linkedin } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const socials = [
  {
    icon: Mail,
    label: 'hitartht318@gmail.com',
    href: 'mailto:hitartht318@gmail.com',
  },
  {
    icon: Github,
    label: 'github.com/HitarthTrivedi',
    href: 'https://github.com/HitarthTrivedi',
  },
  {
    icon: Linkedin,
    label: 'LinkedIn',
    href: 'https://linkedin.com/in/hitarth-trivedi-ba1986300',
  },
];

export default function ContactPage() {
  return (
    <div style={{ background: '#000', minHeight: '100vh' }}>
      <Header />
      <main style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: 620, margin: '0 auto', padding: '0 1.5rem' }}>
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
              Contact
            </p>
            <h1 style={{
              color: '#fff',
              fontSize: 'clamp(2rem, 4.5vw, 3.2rem)',
              lineHeight: 1.12,
              fontWeight: 700,
              margin: '0 0 14px',
            }}>
              Get in touch.
            </h1>
            <p style={{
              color: 'rgba(255,255,255,0.52)',
              fontSize: 15,
              lineHeight: 1.7,
              margin: 0,
            }}>
              Questions, partnership inquiries, or just want to say hi?
            </p>
          </motion.div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {socials.map((item, index) => {
              const Icon = item.icon;
              return (
                <motion.a
                  key={item.label}
                  href={item.href}
                  target={item.href.startsWith('http') ? '_blank' : undefined}
                  rel={item.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.38, delay: 0.08 + index * 0.05 }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '18px 0',
                    borderBottom: '1px solid rgba(255,255,255,0.08)',
                    textDecoration: 'none',
                    color: 'rgba(255,255,255,0.65)',
                    fontSize: 15,
                    transition: 'color 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = '#fff'}
                  onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.65)'}
                >
                  <div style={{
                    width: 38,
                    height: 38,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(255,255,255,0.04)',
                    flexShrink: 0,
                  }}>
                    <Icon size={17} strokeWidth={1.8} />
                  </div>
                  <span style={{ fontWeight: 450 }}>{item.label}</span>
                </motion.a>
              );
            })}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
