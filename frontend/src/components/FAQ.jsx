import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { faqData } from '../mockData';
import { ChevronDown, HelpCircle } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const FAQItem = ({ faq, index, isOpen, onToggle }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="mb-4 group select-none"
    >
      <GlassPanel className={`border transition-all duration-300 font-mono ${
        isOpen ? 'border-indigo-500/30 bg-slate-950/60' : 'border-white/5 bg-slate-950/40 hover:border-indigo-500/20'
      }`}>
        {/* Question Button */}
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-between p-5 bg-transparent border-none cursor-pointer text-left gap-4 focus:outline-none"
        >
          <span className="text-xs font-bold uppercase tracking-wider text-white group-hover:text-indigo-300 transition-colors">
            {faq.question}
          </span>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="shrink-0 text-slate-500 group-hover:text-indigo-400 transition-colors"
          >
            <ChevronDown size={16} />
          </motion.div>
        </button>

        {/* Answer Box */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="px-5 pb-5 text-slate-400 text-xs leading-relaxed uppercase tracking-wider border-t border-white/5 pt-4 text-justify">
                {faq.answer.replaceAll("Delta", "Delta OS")}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassPanel>
    </motion.div>
  );
};

const FAQ = () => {
  const [openIndex, setOpenIndex] = useState(null);

  const handleToggle = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section id="faq" style={{ padding: '7rem 1.5rem 6rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none" />

      <div className="container max-w-4xl mx-auto">
        {/* Section Header */}
        <motion.div
          style={{ textAlign: 'center', marginBottom: '4rem', maxWidth: '700px', marginLeft: 'auto', marginRight: 'auto' }}
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="font-mono text-center"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-[10px] uppercase font-bold tracking-widest text-indigo-400 mb-4 select-none">
            <HelpCircle size={10} className="animate-pulse" /> FAQ DATABASE
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            Everything you need to know about Delta and how it works.
          </p>
        </motion.div>

        {/* FAQ List */}
        <div className="max-w-3xl mx-auto">
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
          className="text-center mt-12 font-mono"
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-4">
            Still have questions? Awaiting neural ping.
          </p>
          <button className="btn-secondary px-6 py-2.5 text-xs uppercase tracking-widest font-bold font-mono border border-white/5 hover:border-indigo-500/30 transition-all rounded-lg">
            Contact Support Protocols
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default FAQ;
