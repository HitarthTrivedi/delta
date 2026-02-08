import React from 'react';
import { motion } from 'motion/react';
import { benefitsData } from '../mockData';
import { Check } from 'lucide-react';

const Benefits = () => {
  return (
    <section style={{ padding: '5rem 1.2rem', background: 'var(--bg-page)' }}>
      <div className="container">
        {/* Section Header */}
        <motion.div
          style={{ textAlign: 'center', marginBottom: '3rem', maxWidth: '700px', marginLeft: 'auto', marginRight: 'auto' }}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="heading-1" style={{ marginBottom: '1rem' }}>
            Tailored for Every Career Stage
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            Whether you're starting out, switching careers, or leveling up—we've got you covered.
          </p>
        </motion.div>

        {/* Benefits Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
        }}>
          {benefitsData.map((benefit, index) => (
            <motion.div
              key={index}
              style={{
                background: 'var(--bg-card)',
                borderRadius: '0.75rem',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
              }}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ transform: 'translateY(-4px)', boxShadow: '0 8px 24px rgba(0, 0, 0, 0.08)' }}
            >
              <h3 className="heading-2" style={{ marginBottom: '0.75rem' }}>
                {benefit.title}
              </h3>
              <p className="body-medium" style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                {benefit.description}
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {benefit.points.map((point, idx) => (
                  <li key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                      width: '1.5rem',
                      height: '1.5rem',
                      borderRadius: '50%',
                      background: 'var(--text-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      <Check size={14} color="white" strokeWidth={3} />
                    </div>
                    <span className="body-small" style={{ color: 'var(--text-primary)' }}>
                      {point}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Benefits;
