import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { faqData } from '../mockData';
import { ChevronDown } from 'lucide-react';

const FAQItem = ({ faq, index, isOpen, onToggle }) => {
  return (
    <motion.div
      style={{
        background: 'var(--bg-card)',
        borderRadius: '0.75rem',
        marginBottom: '1rem',
        border: '1px solid var(--border-light)',
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.03)',
        overflow: 'hidden'
      }}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.05 }}
    >
      {/* Question */}
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1.5rem',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          gap: '1rem'
        }}
      >
        <h3 className="heading-3" style={{ fontWeight: '500', color: 'var(--text-primary)', margin: 0 }}>
          {faq.question}
        </h3>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ flexShrink: 0 }}
        >
          <ChevronDown size={20} color="var(--text-muted)" />
        </motion.div>
      </button>

      {/* Answer */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <p 
              className="body-medium" 
              style={{ 
                color: 'var(--text-secondary)', 
                padding: '0 1.5rem 1.5rem',
                lineHeight: '1.6',
                margin: 0
              }}
            >
              {faq.answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const FAQ = () => {
  const [openIndex, setOpenIndex] = useState(null);

  const handleToggle = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section id="faq" style={{ padding: '5rem 1.2rem', background: 'var(--bg-section)' }}>
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
            Frequently Asked Questions
          </h2>
          <p className="body-large" style={{ color: 'var(--text-secondary)' }}>
            Everything you need to know about Delta and how it works.
          </p>
        </motion.div>

        {/* FAQ List */}
        <div style={{ maxWidth: '800px', marginLeft: 'auto', marginRight: 'auto' }}>
          {faqData.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              index={index}
              isOpen={openIndex === index}
              onToggle={() => handleToggle(index)}
            />
          ))}
        </div>

        {/* Contact CTA */}
        <motion.div
          style={{ textAlign: 'center', marginTop: '3rem' }}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <p className="body-medium" style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Still have questions? We're here to help.
          </p>
          <button className="btn-secondary">
            Contact Support
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default FAQ;
