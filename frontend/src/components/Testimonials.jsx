import React from 'react';
import { motion } from 'motion/react';
import { testimonialsData } from '../mockData';
import { Star, Quote } from 'lucide-react';

const Testimonials = () => {
  return (
    <section style={{ padding: '5rem 1.2rem', background: 'var(--bg-section)' }}>
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
            Success Stories from Our Community
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            Real people achieving real career transformations with SkillPath.AI.
          </p>
        </motion.div>

        {/* Testimonials Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
        }}>
          {testimonialsData.map((testimonial, index) => (
            <motion.div
              key={testimonial.id}
              style={{
                background: 'var(--bg-card)',
                borderRadius: '0.75rem',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
                display: 'flex',
                flexDirection: 'column',
              }}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ transform: 'translateY(-4px)', boxShadow: '0 8px 24px rgba(0, 0, 0, 0.08)' }}
            >
              {/* Quote Icon */}
              <div style={{ marginBottom: '1rem' }}>
                <Quote size={32} color="var(--text-primary)" style={{ opacity: 0.2 }} />
              </div>

              {/* Rating */}
              <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1rem' }}>
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star key={i} size={16} fill="var(--text-primary)" color="var(--text-primary)" />
                ))}
              </div>

              {/* Quote */}
              <p className="body-medium" style={{ color: 'var(--text-primary)', marginBottom: '1.5rem', flex: 1 }}>
                "{testimonial.quote}"
              </p>

              {/* Author */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <img
                  src={testimonial.image}
                  alt={testimonial.name}
                  style={{
                    width: '3rem',
                    height: '3rem',
                    borderRadius: '50%',
                    objectFit: 'cover'
                  }}
                />
                <div>
                  <div className="body-medium" style={{ fontWeight: '500', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                    {testimonial.name}
                  </div>
                  <div className="body-small" style={{ color: 'var(--text-muted)' }}>
                    {testimonial.role} at {testimonial.company}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
