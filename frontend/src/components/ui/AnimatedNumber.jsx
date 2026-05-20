import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AnimatedNumber({ value, className = '' }) {
  const display = typeof value === 'number' ? value.toFixed(1) : value;
  return (
    <AnimatePresence mode="wait">
      <motion.span
        key={display}
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -10, opacity: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={className}
      >
        {display}
      </motion.span>
    </AnimatePresence>
  );
}
