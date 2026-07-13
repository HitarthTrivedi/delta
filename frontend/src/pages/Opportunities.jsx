import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  MapPin, RefreshCw, Loader2, ExternalLink,
  SlidersHorizontal, Check, TrendingUp, AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { opportunitiesAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: 'var(--paper)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
};

const serif = "'Cormorant Garamond', Georgia, serif";
const mono = "'IBM Plex Mono', ui-monospace, monospace";

const monoLabel = {
  fontFamily: mono,
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--ink-soft)',
};

const ROLE_TYPE_OPTIONS = [
  { key: 'internship', label: 'Internships' },
  { key: 'full_time', label: 'Full-time' },
  { key: 'part_time', label: 'Part-time' },
];

const WORK_MODES = ['any', 'remote', 'hybrid', 'onsite'];

const ROLE_TYPE_LABEL = { internship: 'Internship', full_time: 'Full-time', part_time: 'Part-time' };

const DEFAULT_PREFS = { location: '', role_types: ['internship', 'full_time'], work_mode: 'any', industries: '', notes: '' };

function SkillsLine({ label, skills, tone = 'var(--ink)' }) {
  if (!skills?.length) return null;
  return (
    <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.7 }}>
      <span style={{ ...monoLabel, marginRight: 10 }}>{label}</span>
      <span style={{ color: tone }}>{skills.join('  ·  ')}</span>
    </p>
  );
}

export default function Opportunities() {
  const userId = useAuthStore((state) => state.userId);
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [opportunities, setOpportunities] = useState([]);
  const [generatedAt, setGeneratedAt] = useState(null);
  const [stale, setStale] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [prefsOpen, setPrefsOpen] = useState(false);

  const applyBoard = useCallback((data) => {
    setPrefs({ ...DEFAULT_PREFS, ...(data?.preferences || {}) });
    setOpportunities(data?.opportunities || []);
    setGeneratedAt(data?.generated_at || null);
    setStale(!!data?.stale);
  }, []);

  const loadBoard = useCallback(async () => {
    setLoading(true);
    try {
      const data = await opportunitiesAPI.get(userId);
      applyBoard(data);
    } catch (err) {
      console.error(err);
      toast.error('Could not load your opportunities.');
    } finally {
      setLoading(false);
    }
  }, [userId, applyBoard]);

  useEffect(() => {
    if (userId) loadBoard();
  }, [userId, loadBoard]);

  const generate = async () => {
    setGenerating(true);
    try {
      const data = await opportunitiesAPI.generate(userId);
      applyBoard(data);
      if ((data?.opportunities || []).length === 0) {
        toast.message('No matches yet — try adding more detail to your profile or preferences.');
      } else {
        toast.success('Opportunities updated to match your profile.');
      }
    } catch (err) {
      console.error(err);
      toast.error('Could not generate opportunities right now. Try again shortly.');
    } finally {
      setGenerating(false);
    }
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const data = await opportunitiesAPI.updatePreferences(userId, prefs);
      applyBoard(data);
      setPrefsOpen(false);
      toast.success('Preferences saved. Refresh suggestions to apply them.');
    } catch (err) {
      console.error(err);
      toast.error('Could not save preferences.');
    } finally {
      setSavingPrefs(false);
    }
  };

  const toggleRoleType = (key) => {
    setPrefs((p) => {
      const has = p.role_types.includes(key);
      const next = has ? p.role_types.filter((k) => k !== key) : [...p.role_types, key];
      return { ...p, role_types: next.length ? next : p.role_types };
    });
  };

  const prefsSummary = useMemo(() => {
    const parts = [];
    parts.push(prefs.location ? prefs.location : 'Any location');
    parts.push(prefs.work_mode && prefs.work_mode !== 'any' ? prefs.work_mode : 'Any mode');
    const rt = (prefs.role_types || []).map((k) => ROLE_TYPE_LABEL[k] || k).join(', ');
    if (rt) parts.push(rt);
    return parts.join(' · ');
  }, [prefs]);

  const ranked = useMemo(
    () => [...opportunities].sort((a, b) => (b.match_score || 0) - (a.match_score || 0)),
    [opportunities],
  );

  const isEmpty = !loading && opportunities.length === 0;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3.5rem' }}>
      <div style={{ maxWidth: 1040, margin: '0 auto' }}>

        {/* Header */}
        <header style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 18, alignItems: 'flex-end', marginBottom: 18 }}>
          <div>
            <h1 style={{ fontFamily: serif, fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(1.9rem, 3.5vw, 2.6rem)', lineHeight: 1.1, letterSpacing: 0, margin: 0, maxWidth: 640 }}>
              Roles matched to where you are now.
            </h1>
            <p style={{ margin: '10px 0 0', color: 'var(--ink-soft)', fontSize: 14.5, lineHeight: 1.55, maxWidth: '58ch' }}>
              Suggested jobs and internships based on your profile. As your skills grow, your matches sharpen.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            <button className="opp-btn opp-btn-ghost" onClick={() => setPrefsOpen((o) => !o)}>
              <SlidersHorizontal size={13} /> Preferences
            </button>
            <button className="opp-btn opp-btn-primary" onClick={generate} disabled={generating}>
              {generating
                ? <Loader2 size={13} className="opp-spin" style={{ animation: 'spin 1s linear infinite' }} />
                : <RefreshCw size={13} />}
              {opportunities.length ? 'Refresh' : 'Find opportunities'}
            </button>
          </div>
        </header>

        {/* Preferences summary line */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, color: 'var(--ink-soft)', fontSize: 13, marginBottom: 18 }}>
          <MapPin size={13} /> {prefsSummary}
          {generatedAt && (
            <span style={{ ...monoLabel, marginLeft: 'auto' }}>
              Updated {new Date(generatedAt).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Preferences panel */}
        {prefsOpen && (
          <section style={{ ...panelStyle, padding: 22, marginBottom: 20 }}>
            <h2 style={{ margin: '0 0 16px', fontFamily: serif, fontSize: 20, fontWeight: 600 }}>Your preferences</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
              <div>
                <label style={labelStyle}>Preferred location</label>
                <input
                  className="opp-input"
                  value={prefs.location}
                  onChange={(e) => setPrefs((p) => ({ ...p, location: e.target.value }))}
                  placeholder="e.g. Bangalore, Remote, Europe"
                />
              </div>
              <div>
                <label style={labelStyle}>Work mode</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {WORK_MODES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      className={`opp-chip${prefs.work_mode === m ? ' opp-chip-active' : ''}`}
                      onClick={() => setPrefs((p) => ({ ...p, work_mode: m }))}
                    >
                      {m === 'any' ? 'Any' : m.charAt(0).toUpperCase() + m.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label style={labelStyle}>Opportunity types</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {ROLE_TYPE_OPTIONS.map((rt) => {
                    const active = prefs.role_types.includes(rt.key);
                    return (
                      <button
                        key={rt.key}
                        type="button"
                        className={`opp-chip${active ? ' opp-chip-active' : ''}`}
                        onClick={() => toggleRoleType(rt.key)}
                      >
                        {active && <Check size={12} style={{ marginRight: 4 }} />}{rt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label style={labelStyle}>Preferred industries</label>
                <input
                  className="opp-input"
                  value={prefs.industries}
                  onChange={(e) => setPrefs((p) => ({ ...p, industries: e.target.value }))}
                  placeholder="e.g. Fintech, AI, Healthcare"
                />
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <label style={labelStyle}>Anything else to steer your matches?</label>
              <textarea
                className="opp-input"
                value={prefs.notes}
                onChange={(e) => setPrefs((p) => ({ ...p, notes: e.target.value }))}
                placeholder="e.g. Prefer startups over big tech, open to relocation, want mentorship..."
                rows={2}
                style={{ resize: 'vertical' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button className="opp-btn opp-btn-ghost" onClick={() => setPrefsOpen(false)}>
                Cancel
              </button>
              <button className="opp-btn opp-btn-primary" onClick={savePreferences} disabled={savingPrefs}>
                {savingPrefs
                  ? <Loader2 size={13} className="opp-spin" style={{ animation: 'spin 1s linear infinite' }} />
                  : <Check size={13} />}
                Save preferences
              </button>
            </div>
          </section>
        )}

        {/* Stale banner */}
        {stale && !generating && (
          <div style={{ ...panelStyle, padding: '12px 16px', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--accent-surface)' }}>
            <TrendingUp size={15} style={{ color: 'var(--oxblood)', flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: 'var(--ink)', flex: 1 }}>
              Your profile has improved since these were generated. Refresh for sharper matches.
            </span>
            <button className="opp-btn opp-btn-primary" style={{ padding: '8px 14px' }} onClick={generate}>
              Refresh
            </button>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-soft)', padding: '40px 0', fontSize: 14 }}>
            <Loader2 size={17} className="opp-spin" style={{ animation: 'spin 1s linear infinite' }} /> Loading your board...
          </div>
        ) : generating ? (
          <section style={{ ...panelStyle, padding: '30px 26px' }}>
            <h2 style={{ margin: '0 0 8px', fontFamily: serif, fontSize: 21, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10 }}>
              <Loader2 size={17} className="opp-spin" style={{ animation: 'spin 1s linear infinite', color: 'var(--oxblood)' }} />
              Matching roles to your profile...
            </h2>
            <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.55, maxWidth: '58ch' }}>
              Reading your skills, experience, and preferences. This takes a few seconds.
            </p>
          </section>
        ) : isEmpty ? (
          <section style={{ ...panelStyle, padding: '30px 26px' }}>
            <h2 style={{ margin: '0 0 8px', fontFamily: serif, fontSize: 22, fontWeight: 600 }}>No suggestions yet</h2>
            <p style={{ margin: '0 0 20px', color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.6, maxWidth: '58ch' }}>
              Delta reads your profile — skills, projects, preferences — and matches roles to it, ranked by fit.
              Set your preferences to steer the search, then generate your first board.
            </p>
            <button className="opp-btn opp-btn-primary" onClick={generate}>
              <RefreshCw size={13} /> Find my opportunities
            </button>
          </section>
        ) : (
          <section style={{ ...panelStyle }}>
            {ranked.map((op, i) => (
              <article
                key={i}
                className="opp-row"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '72px minmax(0, 1fr) auto',
                  gap: 22,
                  padding: '20px 22px',
                  borderTop: i ? '1px solid var(--rule)' : 'none',
                  alignItems: 'start',
                }}
              >
                <div className="opp-score" style={{ paddingTop: 2 }}>
                  <span style={{
                    display: 'block',
                    fontSize: 27,
                    fontWeight: 800,
                    lineHeight: 1,
                    color: (op.match_score || 0) >= 75 ? 'var(--oxblood)' : 'var(--ink)',
                  }}>
                    {op.match_score}
                  </span>
                  <span style={{ ...monoLabel, display: 'block', marginTop: 5 }}>match</span>
                </div>

                <div style={{ minWidth: 0 }}>
                  <h3 style={{ margin: 0, fontSize: 16.5, fontWeight: 700, lineHeight: 1.35 }}>{op.title}</h3>
                  <p style={{ margin: '5px 0 0', color: 'var(--ink-soft)', fontSize: 12.5, lineHeight: 1.55 }}>
                    {[
                      ROLE_TYPE_LABEL[op.role_type] || op.role_type,
                      op.target_companies,
                      op.location ? `${op.location}${op.work_mode ? ` (${op.work_mode})` : ''}` : null,
                    ].filter(Boolean).join('  ·  ')}
                  </p>

                  {op.why_it_fits && (
                    <p style={{ margin: '9px 0 0', color: 'var(--ink)', fontSize: 13.5, lineHeight: 1.6, maxWidth: '68ch' }}>
                      {op.why_it_fits}
                    </p>
                  )}

                  {(op.skills_matched?.length > 0 || op.skills_to_build?.length > 0) && (
                    <div style={{ display: 'grid', gap: 3, marginTop: 10 }}>
                      <SkillsLine label="You have" skills={op.skills_matched} />
                      <SkillsLine label="Worth building" skills={op.skills_to_build} tone="var(--ink-soft)" />
                    </div>
                  )}
                </div>

                {op.search_url && (
                  <a className="opp-link" style={{ marginTop: 4 }} href={op.search_url} target="_blank" rel="noreferrer">
                    View live openings <ExternalLink size={12} />
                  </a>
                )}
              </article>
            ))}
          </section>
        )}

        {/* Honest note about how suggestions work */}
        {!loading && !generating && opportunities.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginTop: 18, color: 'var(--ink-soft)', fontSize: 12, lineHeight: 1.5, maxWidth: '80ch' }}>
            <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>These are AI role matches for your current profile, each linking to live job-board search results. They aren't specific verified postings — always confirm details on the employer's page.</span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .opp-btn {
          font-family: 'IBM Plex Mono', ui-monospace, monospace;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          border-radius: 0;
          padding: 11px 18px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
        }
        .opp-btn:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .opp-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .opp-btn-primary { background: var(--oxblood); color: var(--bone); border: 1px solid var(--oxblood); }
        .opp-btn-primary:hover:not(:disabled) { background: var(--ink); border-color: var(--ink); }
        .opp-btn-ghost { background: transparent; color: var(--ink); border: 1px solid var(--ink); }
        .opp-btn-ghost:hover:not(:disabled) { background: var(--ink); color: var(--bone); }
        .opp-chip {
          background: var(--accent-surface);
          color: var(--ink);
          border: 1px solid var(--rule);
          border-radius: 0;
          padding: 7px 12px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          transition: background-color 0.15s ease, color 0.15s ease;
        }
        .opp-chip:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .opp-chip-active { background: var(--ink); color: var(--bone); border-color: var(--ink); }
        .opp-input {
          width: 100%;
          background: var(--paper);
          border: 1px solid var(--rule);
          border-radius: 0;
          padding: 10px 12px;
          color: var(--ink);
          font-size: 14px;
          font-family: inherit;
          outline: none;
          box-sizing: border-box;
          transition: border-color 0.15s ease;
        }
        .opp-input::placeholder { color: var(--ink-soft); }
        .opp-input:focus { border-color: var(--oxblood); }
        .opp-link {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          white-space: nowrap;
          color: var(--ink);
          font-size: 13px;
          font-weight: 600;
          text-decoration: underline;
          text-underline-offset: 3px;
          transition: color 0.15s ease;
        }
        .opp-link:hover { color: var(--oxblood); }
        .opp-link:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        @media (max-width: 680px) {
          .opp-row { grid-template-columns: 1fr !important; gap: 10px !important; }
          .opp-score { display: flex; align-items: baseline; gap: 8px; padding-top: 0 !important; }
          .opp-score span { margin-top: 0 !important; }
          .opp-row .opp-link { margin-top: 0 !important; justify-self: start; }
        }
        @media (prefers-reduced-motion: reduce) {
          .opp-spin { animation: none !important; }
          .opp-btn, .opp-chip, .opp-input, .opp-link { transition: none; }
        }
      `}</style>
    </main>
  );
}

const labelStyle = {
  display: 'block',
  fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--ink-soft)',
  marginBottom: 7,
};
