import React from 'react';
import { motion } from 'motion/react';
import { featuresData } from '../mockData';
import { Target, TrendingUp, FileText, Linkedin, BarChart3, Brain } from 'lucide-react';

const iconMap = {
  1: Target,
  2: TrendingUp,
  3: FileText,
  4: Linkedin,
  5: BarChart3,
  6: Brain
};

const Features = () => {
  return (
    <section id="features" style={{ padding: '5rem 1.2rem', background: 'var(--bg-page)' }}>
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
            Intelligent Features for Your Success
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            AI-powered tools that adapt to your unique career journey and accelerate your growth.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="voice-grid">
          {featuresData.map((feature, index) => {
            const Icon = iconMap[feature.id];
            return (
              <motion.div
                key={feature.id}
                className={`voice-card ${feature.color}`}
                style={{ display: 'flex', flexDirection: 'column', minHeight: '220px' }}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <div style={{
                  width: '3rem',
                  height: '3rem',
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem'
                }}>
                  <Icon size={20} strokeWidth={2} color="var(--text-primary)" />
                </div>
                <h3 className="voice-card-title">{feature.title}</h3>
                <p className="voice-card-description">{feature.description}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;
