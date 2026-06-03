import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const steps = [
  {
    label: 'Profile',
    title: 'The intake agent learns the student properly.',
    detail:
      'It collects identity, place, qualification, college, resume evidence, interests, future goals, constraints, available hours, exams, preferred learning style, and anything unusual that can change the plan.',
  },
  {
    label: 'Week',
    title: 'The planner chooses the next useful week.',
    detail:
      'It does not dump a full-year checklist. Every week it decides whether to assign a course, paper, project, language class, revision block, internship prep, or a complete exam pause.',
  },
  {
    label: 'Proof',
    title: 'The progress report turns work into momentum.',
    detail:
      'Progress, completed tasks, project depth, resume improvements, internship signals, news, and visual summaries are maintained by the progress agent.',
  },
  {
    label: 'Adjust',
    title: 'The system keeps listening.',
    detail:
      'The weekly chat asks whether the pace is right and whether exams, deadlines, health, placement drives, or new goals should shift the next week.',
  },
];

const HowItWorks = () => {
  return (
    <section id="how-it-works" style={{ background: '#000', padding: '4rem 1.5rem 6rem' }}>
      <div style={{ maxWidth: 920, margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          style={{
            borderTop: '1px solid rgba(255,255,255,0.12)',
            paddingTop: 36,
            marginBottom: 22,
          }}
        >
          <h2 style={{
            color: '#fff',
            fontSize: 'clamp(1.8rem, 3.6vw, 2.7rem)',
            lineHeight: 1.15,
            fontWeight: 700,
            letterSpacing: 0,
            margin: '0 0 14px',
          }}>
            Built for years of guidance, but planned one week at a time.
          </h2>
          <p style={{
            color: 'rgba(255,255,255,0.52)',
            fontSize: 16,
            lineHeight: 1.7,
            maxWidth: 660,
            margin: 0,
          }}>
            Delta should understand long timelines like masters abroad, fourth-year deadlines, German classes, placements, and exam seasons without forcing the student into a rigid template.
          </p>
        </motion.div>

        <div style={{ display: 'grid', gap: 0, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          {steps.map((step, index) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -12 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.38, delay: index * 0.05 }}
              style={{
                display: 'grid',
                gridTemplateColumns: '110px minmax(0, 1fr)',
                gap: 24,
                padding: '26px 0',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
              }}
              className="delta-workflow-row"
            >
              <span style={{
                color: 'rgba(255,255,255,0.42)',
                fontSize: 13,
                fontWeight: 700,
              }}>
                {step.label}
              </span>
              <div>
                <h3 style={{
                  color: '#fff',
                  fontSize: 20,
                  lineHeight: 1.3,
                  fontWeight: 650,
                  letterSpacing: 0,
                  margin: '0 0 8px',
                }}>
                  {step.title}
                </h3>
                <p style={{
                  color: 'rgba(255,255,255,0.5)',
                  fontSize: 15,
                  lineHeight: 1.65,
                  margin: 0,
                }}>
                  {step.detail}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          style={{ marginTop: 32 }}
        >
          <button
            onClick={() => window.location.href = '/intake'}
            style={{
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: 999,
              padding: '12px 22px',
              fontSize: 15,
              fontWeight: 650,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            Start intake
            <ArrowRight size={15} />
          </button>
        </motion.div>
      </div>

      <style>{`
        @media (max-width: 640px) {
          .delta-workflow-row {
            grid-template-columns: 1fr !important;
            gap: 8px !important;
          }
        }
      `}</style>
    </section>
  );
};

export default HowItWorks;
