import React from 'react';
import { motion } from 'framer-motion';

export default function GlassPanel({ children, className = '', hover = true, ...props }) {
  return (
    <motion.div
      className={`rounded-2xl border border-rule bg-paper p-6 ${className}`}
      whileHover={hover ? { borderColor: 'var(--ink-soft)', scale: 1.002 } : {}}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
