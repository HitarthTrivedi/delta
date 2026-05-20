import React from 'react';
import { motion } from 'framer-motion';

export default function GlassPanel({ children, className = '', hover = true, ...props }) {
  return (
    <motion.div
      className={`rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6 ${className}`}
      whileHover={hover ? { borderColor: 'rgba(255,255,255,0.1)', scale: 1.002 } : {}}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
