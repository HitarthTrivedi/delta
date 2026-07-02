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
    <div className="bg-bone min-h-screen">
      <Header />
      <main className="pt-[5.5rem] pb-12">
        <div className="max-w-[620px] mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-9"
          >
            <p className="kicker mb-3">
              Contact
            </p>
            <h1 className="font-display text-oxblood font-medium leading-[1.12] m-0 mb-3.5" style={{ fontSize: 'clamp(2rem, 4.5vw, 3.2rem)' }}>
              Get in touch.
            </h1>
            <p className="text-ink-soft text-[15px] leading-[1.7] m-0">
              Questions, partnership inquiries, or just want to say hi?
            </p>
          </motion.div>

          <div className="flex flex-col border-t border-rule">
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
                  className="flex items-center gap-3.5 py-[18px] border-b border-rule no-underline text-ink hover:text-oxblood text-[15px] transition-colors"
                >
                  <div className="w-[38px] h-[38px] border border-rule bg-accent-surface flex items-center justify-center shrink-0 text-oxblood">
                    <Icon size={17} strokeWidth={1.8} />
                  </div>
                  <span className="font-medium">{item.label}</span>
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
