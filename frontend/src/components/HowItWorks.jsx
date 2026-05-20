import React from 'react';
import { motion } from 'motion/react';
import { howItWorksData } from '../mockData';
import { ArrowRight } from 'lucide-react';

const HowItWorks = () => {
  return (
    <section id="how-it-works" style={{ padding: '5rem 1.2rem', background: 'var(--bg-section)' }}>
      <div className="container">
        {/* Section Header */}
        <motion.div
          style={{ textAlign: 'center', marginBottom: '4rem', maxWidth: '700px', marginLeft: 'auto', marginRight: 'auto' }}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="heading-1" style={{ marginBottom: '1rem' }}>
            Your Journey in Four Simple Steps
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            From ambition to achievement—here's how SkillPath.AI guides you every step of the way.
          </p>
        </motion.div>

        {/* Steps */}
        <div style={{ maxWidth: '900px', marginLeft: 'auto', marginRight: 'auto' }}>
          {howItWorksData.map((step, index) => (
            <motion.div
              key={step.step}
              style={{ position: 'relative', paddingLeft: '0' }}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.15 }}
            >
              <div style={{
                display: 'grid',
                gridTemplateColumns: '80px 1fr',
                gap: '2rem',
                alignItems: 'center',
                marginBottom: index < howItWorksData.length - 1 ? '3rem' : '0',
              }}>
                {/* Step Number */}
                <div style={{
                  width: '80px',
                  height: '80px',
                  borderRadius: '50%',
                  background: 'var(--bg-card)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'SF Mono', monospace",
                  fontSize: '1.5rem',
                  fontWeight: '600',
                  color: 'var(--text-primary)',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.06)',
                  position: 'relative',
                  zIndex: 2
                }}>
                  {step.step}
                </div>

                {/* Step Content */}
                <div style={{
                  background: 'var(--bg-card)',
                  borderRadius: '0.75rem',
                  padding: '1.5rem',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
                }}>
                  <h3 className="heading-3" style={{ marginBottom: '0.5rem' }}>
                    {step.title}
                  </h3>
                  <p className="body-medium" style={{ color: 'var(--text-secondary)' }}>
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Connecting Line */}
              {index < howItWorksData.length - 1 && (
                <div style={{
                  position: 'absolute',
                  left: '40px',
                  top: '80px',
                  width: '2px',
                  height: 'calc(100% - 30px)',
                  background: 'var(--border-light)',
                  zIndex: 1
                }} />
              )}
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          style={{ textAlign: 'center', marginTop: '4rem' }}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <button
            className="btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            onClick={() => window.location.href = '/onboarding'}
          >
            Start Your Journey Today
            <ArrowRight size={16} />
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default HowItWorks;
