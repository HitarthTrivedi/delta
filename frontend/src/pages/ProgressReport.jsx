import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Circle, Loader2, Minus, RefreshCw, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { getTaskProgress } from '../lib/taskProgress';
import { useAuthStore } from '../store/authStore';
import { fetchCareerContext } from '../hooks/useCareerOS';

const panel = {
  background: 'var(--paper)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
};

const serif = "'Cormorant Garamond', Georgia, serif";
const mono = "'IBM Plex Mono', ui-monospace, monospace";

const monoLabel = {
  fontFamily: mono,
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--ink-soft)',
};

const TONES = {
  todo: { label: 'To do', icon: Circle },
  reopened: { label: 'Reopened', icon: RotateCcw },
  done: { label: 'Done', icon: Check },
  skipped: { label: 'Skipped', icon: Minus },
};

function Stat({ label, value, note }) {
  return (
    <div style={{ background: 'var(--paper)', padding: '18px 20px' }}>
      <p style={{ ...monoLabel, margin: '0 0 10px' }}>{label}</p>
      <p style={{ margin: 0, fontFamily: serif, fontSize: 36, fontWeight: 600, lineHeight: 1, color: 'var(--ink)' }}>
        {value}
      </p>
      {note && <p style={{ margin: '9px 0 0', color: 'var(--ink-soft)', fontSize: 12, lineHeight: 1.4 }}>{note}</p>}
    </div>
  );
}

function SectionHead({ title, meta }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
      <h2 style={{ margin: 0, fontFamily: serif, fontSize: 21, fontWeight: 600, lineHeight: 1.2 }}>{title}</h2>
      {meta && <span style={{ ...monoLabel, fontSize: 10, flexShrink: 0 }}>{meta}</span>}
    </div>
  );
}

function ProgressRing({ done, total }) {
  const percent = total ? Math.round((done / total) * 100) : 0;
  return (
    <div
      role="img"
      aria-label={`${percent}% of this week's tasks completed`}
      style={{
        width: 112,
        height: 112,
        borderRadius: '50%',
        background: `conic-gradient(var(--oxblood) ${percent * 3.6}deg, var(--rule) 0deg)`,
        display: 'grid',
        placeItems: 'center',
        flexShrink: 0,
      }}
    >
      <div style={{
        width: 82,
        height: 82,
        borderRadius: '50%',
        background: 'var(--paper)',
        display: 'grid',
        placeItems: 'center',
        color: 'var(--ink)',
        fontSize: 23,
        fontWeight: 800,
      }}>
        {percent}%
      </div>
    </div>
  );
}

function BarRow({ label, value, total }) {
  const percent = total ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, marginBottom: 6 }}>
        <span style={{ color: 'var(--ink)', fontSize: 13, minWidth: 0 }}>{label}</span>
        <span style={{ fontFamily: mono, color: 'var(--ink)', fontSize: 12, fontWeight: 600, flexShrink: 0 }}>{value}</span>
      </div>
      <div style={{ height: 7, background: 'var(--rule)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${percent}%`, background: 'var(--ink)' }} />
      </div>
    </div>
  );
}

function TaskLine({ task, tone, first }) {
  const { label, icon: Icon } = TONES[tone] || TONES.todo;
  const done = tone === 'done';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '22px minmax(0, 1fr) auto',
      gap: 14,
      alignItems: 'start',
      padding: '14px 0',
      borderTop: first ? 'none' : '1px solid var(--rule)',
    }}>
      <span
        aria-hidden="true"
        style={{
          width: 22,
          height: 22,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: 1,
          border: done ? 'none' : '1px solid var(--ink-soft)',
          background: done ? 'var(--ink)' : 'transparent',
          color: done ? 'var(--bone)' : 'var(--ink-soft)',
        }}
      >
        <Icon size={13} />
      </span>
      <div style={{ minWidth: 0 }}>
        <p style={{
          margin: 0,
          color: done ? 'var(--ink-soft)' : 'var(--ink)',
          fontSize: 14.5,
          fontWeight: 650,
          lineHeight: 1.4,
        }}>
          {task.title}
        </p>
        {task.detail && (
          <p style={{ margin: '4px 0 0', color: 'var(--ink-soft)', fontSize: 13, lineHeight: 1.5, maxWidth: '68ch' }}>
            {task.detail}
          </p>
        )}
      </div>
      <span style={{ ...monoLabel, fontSize: 10, marginTop: 4 }}>{label}</span>
    </div>
  );
}

export default function ProgressReport() {
  const userId = useAuthStore((state) => state.userId);
  const queryClient = useQueryClient();
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadContext = useCallback(async () => {
    setLoading(true);
    try {
      setContext(await fetchCareerContext(queryClient, userId));
    } catch (err) {
      console.error(err);
      toast.error('Could not load your progress.');
    } finally {
      setLoading(false);
    }
  }, [userId, queryClient]);

  useEffect(() => {
    loadContext();
  }, [loadContext]);

  const memory = context?.memory || {};
  const market = context?.market || {};

  const studentName = memory.identity_context?.name || memory.identity?.name || 'Student';
  const weekNumber = context?.week_number || 1;
  const progress = useMemo(() => getTaskProgress(context), [context]);
  const summary = context?.progress_summary || {};
  const totalCurrent = progress.totalCurrent;
  const doneCount = progress.done.length;
  const leftCount = progress.left.length;
  const skippedCount = progress.skipped.length;
  const changedCount = progress.changed.length;
  const weeksCompleted = summary.weeks_completed ?? Math.max(weekNumber - 1, 0);
  const totalCompleted = summary.total_tasks_completed ?? doneCount;
  const totalSkipped = summary.total_tasks_skipped ?? skippedCount;
  const knowledgeGained = (summary.knowledge_gained?.length ? summary.knowledge_gained : progress.done.map(task => ({
    skill: task.skill || task.title,
    completed_tasks: 1,
  }))).slice(0, 6);
  const chartTotal = Math.max(totalCurrent, doneCount + leftCount + skippedCount, 1);
  const fieldSignals = [
    ...(market.demanded_skills || []).slice(0, 3).map(skill => ({ title: skill, source: 'Useful skill' })),
    ...(market.emerging_skills || []).slice(0, 3).map(skill => ({ title: skill, source: 'New trend' })),
  ].slice(0, 4);

  // One ledger instead of four separate panels: actionable work first.
  // Reopened tasks also appear in `left`, so filter them out of the to-do group.
  const changedIds = new Set(progress.changed.map(task => task.id));
  const ledger = [
    ...progress.left.filter(task => !changedIds.has(task.id)).map(task => ({ task, tone: 'todo' })),
    ...progress.changed.map(task => ({ task, tone: 'reopened' })),
    ...progress.done.map(task => ({ task, tone: 'done' })),
    ...progress.skipped.map(task => ({ task, tone: 'skipped' })),
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3.5rem' }}>
      <div style={{ maxWidth: 1140, margin: '0 auto' }}>
        <header style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, marginBottom: 26 }}>
          <div>
            <h1 style={{ fontFamily: serif, fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(1.9rem, 3.5vw, 2.6rem)', lineHeight: 1.1, letterSpacing: 0, margin: 0 }}>
              {studentName}'s progress
            </h1>
            <p style={{ margin: '8px 0 0', color: 'var(--ink-soft)', fontSize: 14.5, lineHeight: 1.5 }}>
              Week {weekNumber} — tasks finished, skipped work, and knowledge gained so far.
            </p>
          </div>
          <button className="pr-btn pr-btn-primary" onClick={loadContext} disabled={loading}>
            {loading
              ? <Loader2 size={14} className="pr-spin" style={{ animation: 'spin 1s linear infinite' }} />
              : <RefreshCw size={14} />}
            Refresh
          </button>
        </header>

        <section style={{
          ...panel,
          marginBottom: 20,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 1,
          background: 'var(--rule)',
          overflow: 'hidden',
        }}>
          <Stat label="Weeks complete" value={weeksCompleted} note={`You are currently on week ${weekNumber}.`} />
          <Stat label="Tasks done" value={totalCompleted} note="Across all saved weeks." />
          <Stat label="This week" value={totalCurrent} note={`${doneCount} done, ${leftCount} left.`} />
          <Stat label="Skipped" value={skippedCount} note={`${totalSkipped} skipped in total.`} />
        </section>

        <div className="pr-main" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.62fr) minmax(0, 1fr)', gap: 20, alignItems: 'start' }}>
          {/* Left column: this week's picture, then the task ledger */}
          <div style={{ display: 'grid', gap: 20 }}>
            <section style={{ ...panel, padding: '20px 22px' }}>
              <SectionHead title="This week" meta={`${doneCount} of ${totalCurrent || 0} done`} />
              <div className="pr-week" style={{ display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr)', gap: 28, alignItems: 'center' }}>
                <ProgressRing done={doneCount} total={totalCurrent} />
                <div style={{ display: 'grid', gap: 13 }}>
                  <BarRow label="Done" value={doneCount} total={chartTotal} />
                  <BarRow label="Still left" value={leftCount} total={chartTotal} />
                  <BarRow label="Skipped" value={skippedCount} total={chartTotal} />
                  <BarRow label="Reopened" value={changedCount} total={chartTotal} />
                </div>
              </div>
            </section>

            <section style={{ ...panel, padding: '20px 22px' }}>
              <SectionHead title={`Tasks · Week ${weekNumber}`} meta={leftCount ? `${leftCount} still open` : 'all settled'} />
              {ledger.length ? (
                <div>
                  {ledger.map(({ task, tone }, index) => (
                    <TaskLine key={task.id ?? `${tone}-${index}`} task={task} tone={tone} first={index === 0} />
                  ))}
                </div>
              ) : (
                <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.55 }}>
                  No tasks saved for this week yet. Ask Agent 2 for your weekly plan and they will show up here.
                </p>
              )}
            </section>
          </div>

          {/* Right rail: what the work added up to, and where the field is going */}
          <div style={{ display: 'grid', gap: 20 }}>
            <section style={{ ...panel, padding: '20px 22px' }}>
              <SectionHead title="Knowledge gained" />
              {knowledgeGained.length ? (
                <div style={{ display: 'grid', gap: 13 }}>
                  {knowledgeGained.map((item, index) => (
                    <BarRow
                      key={`${item.skill}-${index}`}
                      label={item.skill}
                      value={item.completed_tasks || 1}
                      total={Math.max(...knowledgeGained.map(entry => entry.completed_tasks || 1), 1)}
                    />
                  ))}
                </div>
              ) : (
                <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 13.5, lineHeight: 1.55 }}>
                  Complete a task and Delta will show what knowledge it added.
                </p>
              )}
            </section>

            <section style={{ ...panel, padding: '20px 22px' }}>
              <SectionHead title="Skills in demand" />
              <div>
                {(fieldSignals.length ? fieldSignals : [{ title: 'No field updates yet.', source: 'Delta' }]).map((item, index) => (
                  <div key={`${item.title}-${index}`} style={{ borderTop: index ? '1px solid var(--rule)' : 'none', padding: index ? '11px 0' : '0 0 11px' }}>
                    <p style={{ margin: '0 0 3px', fontSize: 13.5, fontWeight: 650, lineHeight: 1.4 }}>{item.title}</p>
                    <p style={{ ...monoLabel, fontSize: 10, margin: 0 }}>{item.source}</p>
                  </div>
                ))}
              </div>
              <div style={{ borderTop: '1px solid var(--rule)', marginTop: 4, paddingTop: 13, display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--ink)' }}>Completed lifetime</span>
                  <span aria-hidden="true" style={{ flex: 1, borderBottom: '1px dotted var(--rule)' }} />
                  <span style={{ fontFamily: mono, fontSize: 12, fontWeight: 600 }}>{totalCompleted}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--ink)' }}>Skipped lifetime</span>
                  <span aria-hidden="true" style={{ flex: 1, borderBottom: '1px dotted var(--rule)' }} />
                  <span style={{ fontFamily: mono, fontSize: 12, fontWeight: 600 }}>{totalSkipped}</span>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .pr-btn {
          font-family: 'IBM Plex Mono', ui-monospace, monospace;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          border-radius: 0;
          padding: 12px 20px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
        }
        .pr-btn:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .pr-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .pr-btn-primary { background: var(--oxblood); color: var(--bone); border: 1px solid var(--oxblood); }
        .pr-btn-primary:hover:not(:disabled) { background: var(--ink); border-color: var(--ink); }
        @media (max-width: 940px) {
          .pr-main { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 540px) {
          .pr-week { grid-template-columns: 1fr !important; justify-items: start; }
        }
        @media (prefers-reduced-motion: reduce) {
          .pr-spin { animation: none !important; }
          .pr-btn { transition: none; }
        }
      `}</style>
    </main>
  );
}
