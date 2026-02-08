import React from 'react';
import { motion } from 'motion/react';

const FloatingShapes = () => {
  const shapes = [
    { id: 1, size: 80, color: 'rgba(252, 202, 199, 0.4)', duration: 20, delay: 0, x: '10%', y: '20%' },
    { id: 2, size: 60, color: 'rgba(253, 215, 197, 0.3)', duration: 25, delay: 2, x: '80%', y: '15%' },
    { id: 3, size: 100, color: 'rgba(254, 241, 229, 0.35)', duration: 30, delay: 4, x: '15%', y: '70%' },
    { id: 4, size: 70, color: 'rgba(252, 202, 199, 0.3)', duration: 22, delay: 1, x: '85%', y: '75%' },
    { id: 5, size: 90, color: 'rgba(253, 215, 197, 0.25)', duration: 28, delay: 3, x: '50%', y: '50%' },
  ];

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      {shapes.map((shape) => (
        <motion.div
          key={shape.id}
          style={{
            position: 'absolute',
            left: shape.x,
            top: shape.y,
            width: shape.size,
            height: shape.size,
            borderRadius: '30% 70% 70% 30% / 30% 30% 70% 70%',
            background: shape.color,
            filter: 'blur(40px)',
          }}
          animate={{
            y: [0, -30, 0],
            x: [0, 20, 0],
            rotate: [0, 180, 360],
            borderRadius: [
              '30% 70% 70% 30% / 30% 30% 70% 70%',
              '70% 30% 30% 70% / 70% 70% 30% 30%',
              '30% 70% 70% 30% / 30% 30% 70% 70%',
            ],
          }}
          transition={{
            duration: shape.duration,
            delay: shape.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
};

export default FloatingShapes;
