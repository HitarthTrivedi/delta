import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, BookOpen, Check, Circle, Loader2, RefreshCw, RotateCcw, Signal, Trophy } from 'lucide-react';
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

const emptyText = {
  done: 'Nothing is marked done yet.',
  left: 'No tasks left right now.',
  changed: 'No mistakes or reopened tasks.',
  skipped: 'No skipped tasks.',
};

function StatCard({ label, value, note, icon: Icon }) {
  return (
    <div style={{ padding: 16, minHeight: 104, background: 'var(--paper)' }}>
      {Icon && <Icon size={17} style={{ color: 'var(--ink)', marginBottom: 12 }} />}
      <p style={{ margin: '0 0 7px', color: 'var(--ink-soft)', fontSize: 13 }}>{label}</p>
      <p style={{ margin: 0, color: 'var(--ink)', fontSize: 34, fontWeight: 850, lineHeight: 1 }}>{value}</p>
      {note && <p style={{ margin: '8px 0 0', color: 'var(--ink-soft)', fontSize: 12, lineHeight: 1.35 }}>{note}</p>}
    </div>
  );
}

function ProgressRing({ done, total }) {
  const percent = total ? Math.round((done / total) * 100) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
      <div style={{
        width: 108,
        height: 108,
        borderRadius: '50%',
        background: `conic-gradient(var(--ink) ${percent * 3.6}deg, var(--rule) 0deg)`,
        display: 'grid',
        placeItems: 'center',
        flexShrink: 0,
      }}>
        <div style={{
          width: 78,
          height: 78,
          borderRadius: '50%',
          background: 'var(--paper)',
          display: 'grid',
          placeItems: 'center',
          color: 'var(--ink)',
          fontSize: 24,
          fontWeight: 850,
        }}>
          {percent}%
        </div>
      </div>
      <div>
        <p style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 800 }}>This week</p>
        <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.5 }}>
          {done} of {total} tasks completed.
        </p>
      </div>
    </div>
  );
}

function BarRow({ label, value, total }) {
  const percent = total ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 7 }}>
        <span style={{ color: 'var(--ink)', fontSize: 13 }}>{label}</span>
        <span style={{ color: 'var(--ink)', fontSize: 13, fontWeight: 750 }}>{value}</span>
      </div>
      <div style={{ height: 9, background: 'var(--rule)', borderRadius: 0, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${percent}%`, background: 'var(--ink)', borderRadius: 0 }} />
      </div>
    </div>
  );
}

function TaskRow({ task, tone = 'left' }) {
  const done = tone === 'done';
  const changed = tone === 'changed';
  const Icon = done ? Check : changed ? RotateCcw : Circle;
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '30px minmax(0, 1fr)',
      gap: 12,
      alignItems: 'start',
      background: done ? 'var(--accent-surface)' : 'var(--paper)',
      border: '1px solid var(--rule)',
      borderRadius: 0,
      padding: 14,
    }}>
      <span style={{
        width: 24,
        height: 24,
        borderRadius: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: done ? 'none' : '1px solid var(--ink-soft)',
        background: done ? 'var(--ink)' : 'transparent',
        color: done ? 'var(--bone)' : 'var(--ink)',
      }}>
        <Icon size={15} />
      </span>
      <div>
        <p style={{ margin: '0 0 5px', color: 'var(--ink)', fontSize: 15, fontWeight: 750, lineHeight: 1.35 }}>
          {task.title}
        </p>
        {task.detail && (
          <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 13, lineHeight: 1.45 }}>
            {task.detail}
          </p>
        )}
      </div>
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
  const lifetimeChartTotal = Math.max(totalCompleted + totalSkipped + changedCount, 1);
  const fieldSignals = [
    ...(market.demanded_skills || []).slice(0, 3).map(skill => ({ title: skill, source: 'Useful skill' })),
    ...(market.emerging_skills || []).slice(0, 3).map(skill => ({ title: skill, source: 'New trend' })),
  ].slice(0, 4);

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1rem 3rem' }}>
      <div style={{ maxWidth: 1050, margin: '0 auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 22 }}>
          <div>
            <p style={{ color: 'var(--ink-soft)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
              Progress report · Week {weekNumber}
            </p>
            <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(2rem, 5vw, 3rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0 }}>
              {studentName}'s progress
            </h1>
            <p style={{ margin: '10px 0 0', color: 'var(--ink-soft)', fontSize: 15 }}>
              A simple view of weeks completed, tasks finished, skipped work, and knowledge gained.
            </p>
          </div>
          <button
            onClick={loadContext}
            disabled={loading}
            style={{
              background: 'var(--ink)',
              color: 'var(--bone)',
              border: 'none',
              borderRadius: 0,
              padding: '10px 16px',
              fontWeight: 750,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              cursor: loading ? 'not-allowed' : 'pointer',
              flexShrink: 0,
            }}
          >
            {loading ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={15} />}
            Refresh
          </button>
        </header>

        <section style={{
          ...panel,
          padding: 1,
          marginBottom: 18,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: 1,
        }} className="simple-stats">
          <StatCard icon={Trophy} label="Weeks complete" value={weeksCompleted} note={`You are currently on week ${weekNumber}.`} />
          <StatCard icon={Check} label="Total tasks done" value={totalCompleted} note="Across all saved weeks." />
          <StatCard icon={BookOpen} label="This week given" value={totalCurrent} note={`${doneCount} done, ${leftCount} left.`} />
          <StatCard icon={RotateCcw} label="Skipped" value={skippedCount} note={`${totalSkipped} skipped in total.`} />
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.1fr)', gap: 18, marginBottom: 18 }} className="progress-grid">
          <section style={{ ...panel, padding: 18 }}>
            <ProgressRing done={doneCount} total={totalCurrent} />
          </section>

          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart3 size={18} /> Task chart
            </h2>
            <div style={{ display: 'grid', gap: 14 }}>
              <BarRow label="Done this week" value={doneCount} total={chartTotal} />
              <BarRow label="Still left this week" value={leftCount} total={chartTotal} />
              <BarRow label="Skipped this week" value={skippedCount} total={chartTotal} />
              <BarRow label="Reopened" value={changedCount} total={chartTotal} />
            </div>
          </section>
        </div>

        <section style={{ ...panel, padding: 18, marginBottom: 18 }}>
          <h2 style={{ margin: '0 0 14px', fontSize: 22 }}>Knowledge gained</h2>
          <div style={{ display: 'grid', gap: 12 }}>
            {knowledgeGained.length ? knowledgeGained.map((item, index) => (
              <BarRow
                key={`${item.skill}-${index}`}
                label={item.skill}
                value={item.completed_tasks || 1}
                total={Math.max(...knowledgeGained.map(entry => entry.completed_tasks || 1), 1)}
              />
            )) : (
              <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>
                Complete a task and Delta will show what knowledge it added.
              </p>
            )}
          </div>
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 18 }} className="progress-grid">
          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 22 }}>Done</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {progress.done.length ? progress.done.map(task => (
                <TaskRow key={task.id} task={task} tone="done" />
              )) : <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>{emptyText.done}</p>}
            </div>
          </section>

          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 22 }}>Still left</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {progress.left.length ? progress.left.map(task => (
                <TaskRow key={task.id} task={task} tone="left" />
              )) : <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>{emptyText.left}</p>}
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 18, marginTop: 18 }} className="progress-grid">
          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 22 }}>Skipped</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {progress.skipped.length ? progress.skipped.map(task => (
                <TaskRow key={task.id} task={task} tone="changed" />
              )) : <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>{emptyText.skipped}</p>}
            </div>
          </section>

          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 22 }}>Reopened tasks</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {progress.changed.length ? progress.changed.map(task => (
                <TaskRow key={task.id} task={task} tone="changed" />
              )) : <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>{emptyText.changed}</p>}
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 18, marginTop: 18 }} className="progress-grid">
          <section style={{ ...panel, padding: 18 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 22, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Signal size={18} /> Skills in demand
            </h2>
            <div style={{ display: 'grid', gap: 14, marginBottom: fieldSignals.length ? 18 : 0 }}>
              <BarRow label="Completed lifetime" value={totalCompleted} total={lifetimeChartTotal} />
              <BarRow label="Skipped lifetime" value={totalSkipped} total={lifetimeChartTotal} />
            </div>
            <div style={{ display: 'grid', gap: 10 }}>
              {(fieldSignals.length ? fieldSignals : [{ title: 'No field updates yet.', source: 'Delta' }]).map((item, index) => (
                <div key={`${item.title}-${index}`} style={{ borderTop: index ? '1px solid var(--rule)' : 'none', paddingTop: index ? 10 : 0 }}>
                  <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 750 }}>{item.title}</p>
                  <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 12 }}>{item.source}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @media (max-width: 820px) {
          .progress-grid, .simple-stats { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </main>
  );
}
