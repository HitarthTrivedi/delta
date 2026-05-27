import React from 'react';
import { motion } from 'framer-motion';

const FloatingShapes = () => {
  const glows = [
    { id: 1, size: 450, color: 'rgba(99, 102, 241, 0.08)', duration: 15, delay: 0, x: '5%', y: '10%' },
    { id: 2, size: 350, color: 'rgba(139, 92, 246, 0.08)', duration: 18, delay: 2, x: '75%', y: '15%' },
    { id: 3, size: 500, color: 'rgba(6, 182, 212, 0.05)', duration: 25, delay: 4, x: '10%', y: '60%' },
    { id: 4, size: 300, color: 'rgba(236, 72, 153, 0.04)', duration: 20, delay: 1, x: '80%', y: '70%' },
    { id: 5, size: 400, color: 'rgba(16, 185, 129, 0.04)', duration: 22, delay: 3, x: '45%', y: '40%' },
  ];

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      {glows.map((glow) => (
        <motion.div
          key={glow.id}
          style={{
            position: 'absolute',
            left: glow.x,
            top: glow.y,
            width: glow.size,
            height: glow.size,
            borderRadius: '50%',
            background: glow.color,
            filter: 'blur(100px)',
          }}
          animate={{
            y: [0, -40, 0],
            x: [0, 30, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: glow.duration,
            delay: glow.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
      
      {/* Sleek Cybersecurity Scanline and Tech Grids */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.005)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.005)_1px,transparent_1px)] bg-[size:30px_30px] opacity-40 pointer-events-none" />
    </div>
  );
};

export default FloatingShapes;
