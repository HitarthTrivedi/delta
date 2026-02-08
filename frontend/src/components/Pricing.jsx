import React from 'react';
import { motion } from 'motion/react';
import { pricingData } from '../mockData';
import { Check, ArrowRight } from 'lucide-react';

const Pricing = () => {
  return (
    <section id="pricing" style={{ padding: '5rem 1.2rem', background: 'var(--bg-page)' }}>
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
            Simple, Transparent Pricing
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            Choose the plan that fits your career goals. All plans include core AI features.
          </p>
        </motion.div>

        {/* Pricing Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
          maxWidth: '1100px',
          marginLeft: 'auto',
          marginRight: 'auto'
        }}>
          {pricingData.map((plan, index) => (
            <motion.div
              key={index}
              style={{
                background: 'var(--bg-card)',
                borderRadius: '0.75rem',
                padding: '2rem',
                boxShadow: plan.popular ? '0 8px 24px rgba(0, 0, 0, 0.12)' : '0 2px 8px rgba(0, 0, 0, 0.04)',
                border: plan.popular ? '2px solid var(--text-primary)' : '2px solid transparent',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
              }}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ 
                transform: 'translateY(-8px)', 
                boxShadow: plan.popular ? '0 12px 32px rgba(0, 0, 0, 0.16)' : '0 8px 24px rgba(0, 0, 0, 0.08)' 
              }}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div style={{
                  position: 'absolute',
                  top: '-12px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--text-primary)',
                  color: 'white',
                  padding: '0.25rem 1rem',
                  borderRadius: '2rem',
                  fontFamily: "'SF Mono', monospace",
                  fontSize: '0.75rem',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.025em'
                }}>
                  Most Popular
                </div>
              )}

              {/* Plan Name */}
              <h3 className="heading-2" style={{ marginBottom: '0.5rem' }}>
                {plan.name}
              </h3>

              {/* Price */}
              <div style={{ marginBottom: '1rem' }}>
                <span className="heading-hero" style={{ fontSize: 'clamp(2rem, 4vw, 2.5rem)' }}>
                  {plan.price === 'Custom' ? plan.price : `$${plan.price}`}
                </span>
                {plan.price !== 'Custom' && (
                  <span className="body-small" style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                    /{plan.period}
                  </span>
                )}
              </div>

              {/* Description */}
              <p className="body-medium" style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                {plan.description}
              </p>

              {/* Features */}
              <ul style={{ 
                listStyle: 'none', 
                padding: 0, 
                margin: 0, 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '0.75rem',
                marginBottom: '2rem',
                flex: 1
              }}>
                {plan.features.map((feature, idx) => (
                  <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <div style={{
                      width: '1.25rem',
                      height: '1.25rem',
                      borderRadius: '50%',
                      background: 'var(--text-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: '0.125rem'
                    }}>
                      <Check size={12} color="white" strokeWidth={3} />
                    </div>
                    <span className="body-small" style={{ color: 'var(--text-primary)' }}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <button 
                className={plan.popular ? 'btn-primary' : 'btn-secondary'} 
                style={{ 
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                {plan.cta}
                <ArrowRight size={16} />
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;
