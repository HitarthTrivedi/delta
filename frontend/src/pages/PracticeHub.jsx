import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Code2, Briefcase, ListChecks, ArrowRight, Loader2, Target, Table2, LineChart as LineIcon, Zap } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuthStore } from '../store/authStore';
import { useSandboxReport } from '../hooks/useSandboxReport';

const panelStyle = { background: 'var(--paper)', border: '1px solid rgb(var(--ink-rgb) / 0.1)', borderRadius: 10 };
const muted = 'rgb(var(--ink-rgb) / 0.5)';

// Categorical slots 1-3 (dark), validated on var(--paper): worst CVD ΔE 9.4, all >= 3:1.
const SERIES = {
  theory: { color: '#3987e5', label: 'Tests' },
  coding: { color: '#d95926', label: 'Coding' },
  interview: { color: '#199e70', label: 'Interview' },
};
const INK_MUTED = '#898781';
const GRID = '#d9d6cf';
const STATUS = { 'Interview-ready': '#0ca30c', 'Almost there': '#c98500', 'Building up': '#d95926', 'Just starting': INK_MUTED, 'Not started': INK_MUTED };

const TOOLS = [
  { key: 'theory', icon: ListChecks, title: 'Knowledge & Aptitude Tests', description: 'Timed tests on any subject in your field, or an aptitude area, scored per skill.', path: '/practice/theory' },
  { key: 'coding', icon: Code2, title: 'Coding Sandbox', description: 'Write and run real code against hidden test cases.', path: '/practice/coding' },
  { key: 'interview', icon: Briefcase, title: 'AI Video Interview', description: 'Aria interviews you out loud on a video call; answer by voice or text.', path: '/practice/interview' },
];

function shortDate(iso) {
  if (!iso) return '';
  return new Date(`${iso}Z`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{ background: 'var(--paper)', border: '1px solid rgb(var(--ink-rgb) / 0.15)', borderRadius: 8, padding: '8px 12px', fontSize: 12.5 }}>
      <div style={{ color: muted, marginBottom: 4 }}>{shortDate(row.date)}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ink)' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: SERIES[row.type].color }} aria-hidden="true" />
        {row.title}: <strong>{row.score}</strong>
      </div>
    </div>
  );
}

// One click into practice: last-used settings, or sensible defaults for the field.
function QuickStart({ navigate }) {
  const btn = { display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 8, padding: '12px 18px', fontWeight: 800, fontSize: 14, cursor: 'pointer' };
  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 18 }}>
      <button onClick={() => navigate('/practice/interview?quick=1')} style={{ ...btn, background: 'var(--ink)', color: 'var(--paper)', border: 'none' }}>
        <Zap size={15} /> Start an interview now
      </button>
      <button onClick={() => navigate('/practice/theory?quick=1')} style={{ ...btn, background: 'rgb(var(--ink-rgb) / 0.08)', color: 'var(--ink)', border: '1px solid rgb(var(--ink-rgb) / 0.18)' }}>
        <ListChecks size={15} /> Take a quick test
      </button>
    </div>
  );
}

export default function PracticeHub() {
  const userId = useAuthStore((state) => state.userId);
  const navigate = useNavigate();
  const { data: report, isError: error } = useSandboxReport(userId);
  const [asTable, setAsTable] = useState(false);

  // One row per graded session; each type is its own series (nulls bridged).
  const chartRows = useMemo(() => (report?.timeline || []).map((t, i) => ({
    ...t, idx: i, [t.type]: t.score,
  })), [report]);

  // The header and quick-start buttons don't need the report: show them right away.
  if (error || !report) {
    return (
      <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3rem' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 16 }}>
        <header style={{ marginBottom: 8 }}>
          <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>Test Center</p>
          <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3rem)', lineHeight: 1.08, margin: 0 }}>Practice, at your own pace.</h1>
          <p style={{ margin: '12px 0 0', color: muted, fontSize: 15, lineHeight: 1.55, maxWidth: 680 }}>
            Short tests, mock interviews and coding problems. Every session shows you what you already know and what to practise next.
          </p>
          <QuickStart navigate={navigate} />
        </header>
          <section style={{ ...panelStyle, padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, color: muted, fontSize: 14 }}>
            {error ? "Couldn't load your scores. Refresh to try again." : <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Loading your scores…</>}
          </section>
        </div>
        <style>{'@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }'}</style>
      </main>
    );
  }

  const score = report.readiness;
  const ringColor = STATUS[report.label] || INK_MUTED;
  const strongest = report.skills.slice(0, 5);
  const weakest = [...report.skills].reverse().filter((s) => !strongest.includes(s)).slice(0, 5);
  const seriesPresent = Object.keys(SERIES).filter((k) => report.by_type[k].count > 0);

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 16 }}>
        <header style={{ marginBottom: 8 }}>
          <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>Test Center</p>
          <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3rem)', lineHeight: 1.08, margin: 0 }}>Practice, at your own pace.</h1>
          <p style={{ margin: '12px 0 0', color: muted, fontSize: 15, lineHeight: 1.55, maxWidth: 680 }}>
            Short tests, mock interviews and coding problems. Every session shows you what you already know and what to practise next.
          </p>
          <QuickStart navigate={navigate} />
        </header>

        {/* Readiness + next steps */}
        <section style={{ ...panelStyle, padding: 24, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(300px, 100%), 1fr))', gap: 24, alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
            <div style={{ position: 'relative', width: 132, height: 132, flexShrink: 0 }}>
              <svg viewBox="0 0 36 36" width="132" height="132" aria-hidden="true">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(var(--ink-rgb) / 0.08)" strokeWidth="3" />
                {score != null && (
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke={ringColor} strokeWidth="3" strokeLinecap="round"
                    strokeDasharray={`${score} ${100 - score}`} strokeDashoffset="25" />
                )}
              </svg>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 38, fontWeight: 800, lineHeight: 1 }}>{score ?? '—'}</span>
                <span style={{ fontSize: 11, color: muted }}>readiness</span>
              </div>
            </div>
            <div>
              <p style={{ margin: 0, fontSize: 20, fontWeight: 800 }}>{report.label}</p>
              <p style={{ margin: '6px 0 0', color: muted, fontSize: 13, lineHeight: 1.5 }}>
                {report.coverage} of {report.coverage_total} test types taken.
                {report.coverage < report.coverage_total && ' Try every test type for a complete score.'}
              </p>
              <p style={{ margin: '6px 0 0', color: INK_MUTED, fontSize: 12 }}>
                {Object.entries(report.weights || {}).map(([k, w]) => `${SERIES[k]?.label || k} ${Math.round(w * 100)}%`).join(' · ')}, latest 5 of each
              </p>
              {report.field_label && <p style={{ margin: '4px 0 0', color: INK_MUTED, fontSize: 12 }}>Field: {report.field_label}</p>}
            </div>
          </div>
          <div>
            <h2 style={{ margin: '0 0 10px', fontSize: 13, color: muted, display: 'flex', alignItems: 'center', gap: 6 }}><Target size={14} /> Next up</h2>
            {report.next_steps.length === 0 ? (
              <p style={{ margin: 0, color: muted, fontSize: 13.5 }}>Nothing urgent. Keep practising to hold your score.</p>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {report.next_steps.map((s) => (
                  <button key={s.title} onClick={() => navigate(s.link)} style={{ ...panelStyle, background: 'var(--paper)', padding: '12px 14px', textAlign: 'left', color: 'var(--ink)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ flex: 1 }}>
                      <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{s.title}</span>
                      <span style={{ display: 'block', fontSize: 12.5, color: muted, marginTop: 2 }}>{s.reason}</span>
                    </span>
                    <ArrowRight size={15} style={{ color: muted }} />
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Tools */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          {TOOLS.filter((t) => (report.applicable_types || Object.keys(SERIES)).includes(t.key)).map((tool) => {
            const Icon = tool.icon;
            const stats = report.by_type[tool.key];
            return (
              <button
                key={tool.key}
                onClick={() => navigate(tool.path)}
                style={{ ...panelStyle, padding: 22, textAlign: 'left', cursor: 'pointer', color: 'var(--ink)', display: 'flex', flexDirection: 'column', gap: 12 }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgb(var(--ink-rgb) / 0.28)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgb(var(--ink-rgb) / 0.1)'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: SERIES[tool.key].color }} aria-hidden="true" />
                  <Icon size={18} />
                  <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{tool.title}</h2>
                </div>
                <p style={{ margin: 0, color: muted, fontSize: 13.5, lineHeight: 1.55 }}>{tool.description}</p>
                <div style={{ display: 'flex', gap: 18, marginTop: 'auto', paddingTop: 4, alignItems: 'flex-end' }}>
                  {stats.count > 0 ? (
                    <>
                      <span><span style={{ display: 'block', fontSize: 24, fontWeight: 800 }}>{stats.average}</span><span style={{ fontSize: 11.5, color: muted }}>recent avg</span></span>
                      <span><span style={{ display: 'block', fontSize: 16, fontWeight: 700 }}>{stats.best}</span><span style={{ fontSize: 11.5, color: muted }}>best</span></span>
                      <span><span style={{ display: 'block', fontSize: 16, fontWeight: 700 }}>{stats.count}</span><span style={{ fontSize: 11.5, color: muted }}>done</span></span>
                    </>
                  ) : (
                    <span style={{ fontSize: 13, color: muted }}>Not tried yet</span>
                  )}
                  <span style={{ flex: 1 }} />
                  <ArrowRight size={16} style={{ color: muted }} />
                </div>
              </button>
            );
          })}
        </div>

        {report.applicable_types && !report.applicable_types.includes('coding') && (
          <p style={{ margin: '-4px 0 0', fontSize: 12.5, color: muted }}>
            Coding isn't part of your field's readiness score.{' '}
            <button onClick={() => navigate('/practice/coding')} style={{ background: 'none', border: 'none', padding: 0, color: 'var(--ink)', textDecoration: 'underline', cursor: 'pointer', fontSize: 12.5 }}>
              Coding sandbox (for tech roles)
            </button>
          </p>
        )}

        {/* Scores over time */}
        <section style={{ ...panelStyle, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Scores over time</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              {seriesPresent.length > 1 && seriesPresent.map((k) => (
                <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, color: 'rgb(var(--ink-rgb) / 0.75)' }}>
                  <span style={{ width: 14, height: 2, background: SERIES[k].color, borderRadius: 1 }} aria-hidden="true" />{SERIES[k].label}
                </span>
              ))}
              {chartRows.length > 0 && (
                <button onClick={() => setAsTable((v) => !v)} aria-pressed={asTable} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: 'none', border: '1px solid rgb(var(--ink-rgb) / 0.15)', borderRadius: 6, padding: '4px 9px', color: muted, fontSize: 12, cursor: 'pointer' }}>
                  {asTable ? <LineIcon size={13} /> : <Table2 size={13} />} {asTable ? 'Chart' : 'Table'}
                </button>
              )}
            </div>
          </div>
          {chartRows.length < 2 ? (
            <p style={{ margin: 0, padding: '28px 0', textAlign: 'center', color: muted, fontSize: 13.5 }}>
              Complete a couple of sessions and your progress line appears here.
            </p>
          ) : asTable ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead><tr>{['Date', 'Type', 'Session', 'Score'].map((h) => <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: muted, borderBottom: `1px solid ${GRID}`, fontWeight: 600 }}>{h}</th>)}</tr></thead>
                <tbody>{chartRows.map((r) => (
                  <tr key={r.id}><td style={{ padding: '6px 8px' }}>{shortDate(r.date)}</td><td style={{ padding: '6px 8px' }}>{SERIES[r.type].label}</td><td style={{ padding: '6px 8px' }}>{r.title}</td><td style={{ padding: '6px 8px', fontWeight: 700 }}>{r.score}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : (
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartRows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis dataKey="idx" tickFormatter={(i) => shortDate(chartRows[i]?.date)} stroke={GRID} tick={{ fill: INK_MUTED, fontSize: 11 }} tickLine={false} minTickGap={24} />
                  <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} stroke={GRID} tick={{ fill: INK_MUTED, fontSize: 11 }} tickLine={false} axisLine={false} />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgb(var(--ink-rgb) / 0.25)', strokeWidth: 1 }} />
                  {seriesPresent.map((k) => (
                    <Line key={k} type="monotone" dataKey={k} name={SERIES[k].label} stroke={SERIES[k].color} strokeWidth={2} connectNulls
                      dot={{ r: 4, fill: SERIES[k].color, stroke: 'var(--paper)', strokeWidth: 2 }} activeDot={{ r: 6, stroke: 'var(--paper)', strokeWidth: 2 }} isAnimationActive={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        {/* Skills + interview areas */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(300px, 100%), 1fr))', gap: 16 }}>
          <SkillList title="Strongest skills" items={strongest} empty="Take a knowledge test to see your skills here." />
          <SkillList title="Needs work" items={weakest} empty="Not enough data yet." />
          <section style={{ ...panelStyle, padding: 20 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700 }}>Interview skills</h2>
            {report.rubric.length === 0 ? <p style={{ margin: 0, color: muted, fontSize: 13.5 }}>Finish an AI interview to see communication, depth, problem solving and clarity scores.</p> : (
              <div style={{ display: 'grid', gap: 12 }}>
                {report.rubric.map((r) => <Bar key={r.key} label={r.label} value={r.score * 10} display={`${r.score}/10`} />)}
              </div>
            )}
          </section>
        </div>

        {/* Recent */}
        {report.recent.length > 0 && (
          <section style={{ ...panelStyle, padding: 20 }}>
            <h2 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 700 }}>Recent sessions</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)' }}>
              {report.recent.map((s) => {
                const link = s.type === 'interview' ? `/practice/interview/report/${s.id}` : null;
                return (
                  <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderTop: `1px solid ${GRID}` }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: SERIES[s.type].color, flexShrink: 0 }} aria-hidden="true" />
                    <span style={{ fontSize: 12, color: muted, width: 70, flexShrink: 0 }}>{SERIES[s.type].label}</span>
                    <span style={{ flex: 1, fontSize: 13.5, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</span>
                    <span style={{ fontSize: 12, color: muted }}>{shortDate(s.date)}</span>
                    <span style={{ fontSize: 14, fontWeight: 800, width: 36, textAlign: 'right' }}>{s.score}</span>
                    {link ? (
                      <button onClick={() => navigate(link)} style={{ background: 'none', border: '1px solid rgb(var(--ink-rgb) / 0.15)', borderRadius: 6, padding: '4px 10px', color: 'var(--ink)', fontSize: 12, cursor: 'pointer' }}>Report</button>
                    ) : <span style={{ width: 62 }} />}
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
      <style>{'@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }'}</style>
    </main>
  );
}

function Bar({ label, value, display, sub }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 5, gap: 10 }}>
        <span style={{ color: 'rgb(var(--ink-rgb) / 0.85)' }}>{label}{sub && <span style={{ color: INK_MUTED }}> · {sub}</span>}</span>
        <span style={{ color: muted }}>{display}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'rgb(var(--ink-rgb) / 0.08)' }}>
        <div style={{ width: `${Math.max(2, value)}%`, height: '100%', borderRadius: 3, background: 'rgb(var(--ink-rgb) / 0.75)' }} />
      </div>
    </div>
  );
}

function SkillList({ title, items, empty }) {
  return (
    <section style={{ ...panelStyle, padding: 20 }}>
      <h2 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700 }}>{title}</h2>
      {items.length === 0 ? <p style={{ margin: 0, color: muted, fontSize: 13.5 }}>{empty}</p> : (
        <div style={{ display: 'grid', gap: 12 }}>
          {items.map((s) => (
            <Bar key={s.skill} label={s.skill} value={s.score} display={`${s.score}%`}
              sub={[s.questions && `${s.questions} Qs`, s.coding_problems && `${s.coding_problems} coding`].filter(Boolean).join(', ')} />
          ))}
        </div>
      )}
    </section>
  );
}
