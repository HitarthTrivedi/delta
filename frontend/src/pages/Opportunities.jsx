import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Briefcase, MapPin, Sparkles, RefreshCw, Loader2, ExternalLink, Building2,
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

const ROLE_TYPE_OPTIONS = [
  { key: 'internship', label: 'Internships' },
  { key: 'full_time', label: 'Full-time' },
  { key: 'part_time', label: 'Part-time' },
];

const WORK_MODES = ['any', 'remote', 'hybrid', 'onsite'];

const ROLE_TYPE_LABEL = { internship: 'Internship', full_time: 'Full-time', part_time: 'Part-time' };

const DEFAULT_PREFS = { location: '', role_types: ['internship', 'full_time'], work_mode: 'any', industries: '', notes: '' };

function scoreColor(score) {
  if (score >= 75) return 'var(--oxblood)';
  return 'var(--ink-soft)';
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

  const isEmpty = !loading && opportunities.length === 0;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>

        {/* Header */}
        <header style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <p style={{ color: 'var(--ink-soft)', fontSize: 13, fontWeight: 650, margin: '0 0 10px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Briefcase size={15} style={{ color: 'var(--oxblood)' }} /> Opportunities
            </p>
            <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 720 }}>
              Roles matched to where you are now.
            </h1>
            <p style={{ margin: '14px 0 0', color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.55, maxWidth: 640 }}>
              AI-suggested jobs and internships based on your profile. As your skills grow, your matches sharpen. Set preferences to steer them.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            <button
              onClick={() => setPrefsOpen((o) => !o)}
              style={{
                background: 'var(--accent-surface)', color: 'var(--ink)',
                border: '1px solid var(--rule)', borderRadius: 0,
                padding: '11px 16px', fontWeight: 600, fontSize: 13,
                display: 'inline-flex', alignItems: 'center', gap: 7, cursor: 'pointer',
              }}
            >
              <SlidersHorizontal size={14} /> Preferences
            </button>
            <button
              onClick={generate}
              disabled={generating}
              style={{
                background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0,
                padding: '11px 18px', fontWeight: 700,
                display: 'inline-flex', alignItems: 'center', gap: 8,
                cursor: generating ? 'not-allowed' : 'pointer', flexShrink: 0,
              }}
            >
              {generating ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={15} />}
              {opportunities.length ? 'Refresh' : 'Find opportunities'}
            </button>
          </div>
        </header>

        {/* Preferences summary line */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ink-soft)', fontSize: 13, marginBottom: 18 }}>
          <MapPin size={13} /> {prefsSummary}
          {generatedAt && (
            <span style={{ marginLeft: 'auto', color: 'var(--ink-soft)' }}>
              Updated {new Date(generatedAt).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Preferences panel */}
        {prefsOpen && (
          <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
            <h2 style={{ margin: '0 0 16px', fontSize: 17 }}>Your preferences</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
              <div>
                <label style={labelStyle}>Preferred location</label>
                <input
                  value={prefs.location}
                  onChange={(e) => setPrefs((p) => ({ ...p, location: e.target.value }))}
                  placeholder="e.g. Bangalore, Remote, Europe"
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Work mode</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {WORK_MODES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setPrefs((p) => ({ ...p, work_mode: m }))}
                      style={chipStyle(prefs.work_mode === m)}
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
                      <button key={rt.key} type="button" onClick={() => toggleRoleType(rt.key)} style={chipStyle(active)}>
                        {active && <Check size={12} style={{ marginRight: 4 }} />}{rt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label style={labelStyle}>Preferred industries</label>
                <input
                  value={prefs.industries}
                  onChange={(e) => setPrefs((p) => ({ ...p, industries: e.target.value }))}
                  placeholder="e.g. Fintech, AI, Healthcare"
                  style={inputStyle}
                />
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <label style={labelStyle}>Anything else to steer your matches?</label>
              <textarea
                value={prefs.notes}
                onChange={(e) => setPrefs((p) => ({ ...p, notes: e.target.value }))}
                placeholder="e.g. Prefer startups over big tech, open to relocation, want mentorship..."
                rows={2}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button onClick={() => setPrefsOpen(false)} style={{ background: 'none', border: '1px solid var(--rule)', borderRadius: 0, padding: '9px 16px', color: 'var(--ink-soft)', fontSize: 13, cursor: 'pointer' }}>
                Cancel
              </button>
              <button onClick={savePreferences} disabled={savingPrefs} style={{ background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0, padding: '9px 18px', fontWeight: 700, fontSize: 13, cursor: savingPrefs ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                {savingPrefs ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={14} />}
                Save preferences
              </button>
            </div>
          </section>
        )}

        {/* Stale banner */}
        {stale && !generating && (
          <div style={{ ...panelStyle, padding: '12px 16px', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--accent-surface)' }}>
            <TrendingUp size={16} style={{ color: 'var(--oxblood)', flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: 'var(--ink)', flex: 1 }}>
              Your profile has improved since these were generated. Refresh for sharper matches.
            </span>
            <button onClick={generate} style={{ background: 'var(--oxblood)', color: 'var(--bone)', border: 'none', borderRadius: 0, padding: '7px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}>
              Refresh
            </button>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-soft)', padding: '40px 0' }}>
            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Loading your board...
          </div>
        ) : generating ? (
          <section style={{ ...panelStyle, padding: '48px 24px', textAlign: 'center' }}>
            <Loader2 size={26} style={{ animation: 'spin 1s linear infinite', color: 'var(--oxblood)', marginBottom: 14 }} />
            <h2 style={{ margin: '0 0 8px', fontSize: 19 }}>Matching roles to your profile...</h2>
            <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14 }}>Reading your skills, experience, and preferences. This takes a few seconds.</p>
          </section>
        ) : isEmpty ? (
          <section style={{ ...panelStyle, padding: '48px 24px', textAlign: 'center' }}>
            <div style={{
              width: 56, height: 56, borderRadius: 0, margin: '0 auto 16px',
              background: 'var(--accent-surface)', border: '1px solid var(--rule)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Sparkles size={24} style={{ color: 'var(--oxblood)' }} />
            </div>
            <h2 style={{ margin: '0 0 8px', fontSize: 20 }}>No suggestions yet</h2>
            <p style={{ margin: '0 0 20px', color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.55 }}>
              Set your preferences, then let Delta match jobs and internships to your current profile.
            </p>
            <button
              onClick={generate}
              style={{ background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0, padding: '11px 18px', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8 }}
            >
              <Sparkles size={16} /> Find my opportunities
            </button>
          </section>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
            {opportunities.map((op, i) => (
              <div key={i} style={{ ...panelStyle, padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                  <div>
                    <span style={{
                      display: 'inline-block', background: 'var(--accent-surface)', color: 'var(--oxblood)',
                      borderRadius: 0, padding: '3px 9px', fontSize: 10, fontWeight: 700,
                      textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8,
                    }}>
                      {ROLE_TYPE_LABEL[op.role_type] || op.role_type}
                    </span>
                    <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, lineHeight: 1.35 }}>{op.title}</h3>
                  </div>
                  <div style={{ textAlign: 'center', flexShrink: 0 }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(op.match_score), lineHeight: 1 }}>{op.match_score}</div>
                    <div style={{ fontSize: 9, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: 0.5 }}>match</div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, color: 'var(--ink-soft)', fontSize: 12 }}>
                  {op.target_companies && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      <Building2 size={12} /> {op.target_companies}
                    </span>
                  )}
                  {op.location && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      <MapPin size={12} /> {op.location}{op.work_mode ? ` · ${op.work_mode}` : ''}
                    </span>
                  )}
                </div>

                {op.why_it_fits && (
                  <p style={{ margin: 0, color: 'var(--ink)', fontSize: 13, lineHeight: 1.55 }}>{op.why_it_fits}</p>
                )}

                {op.skills_matched?.length > 0 && (
                  <div>
                    <p style={{ margin: '0 0 6px', fontSize: 11, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: 0.5 }}>You have</p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {op.skills_matched.map((s, j) => (
                        <span key={j} style={{ background: 'var(--accent-surface)', color: 'var(--ink)', borderRadius: 0, padding: '3px 8px', fontSize: 11, border: '1px solid var(--rule)' }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {op.skills_to_build?.length > 0 && (
                  <div>
                    <p style={{ margin: '0 0 6px', fontSize: 11, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Build to stand out</p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {op.skills_to_build.map((s, j) => (
                        <span key={j} style={{ background: 'var(--accent-surface)', color: 'var(--ink-soft)', borderRadius: 0, padding: '3px 8px', fontSize: 11, border: '1px solid var(--rule)' }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {op.search_url && (
                  <a
                    href={op.search_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      marginTop: 'auto', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                      background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0,
                      padding: '9px 12px', color: 'var(--ink)', fontSize: 13, fontWeight: 600, textDecoration: 'none',
                    }}
                  >
                    <ExternalLink size={13} /> View live openings
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Honest note about how suggestions work */}
        {!loading && !generating && opportunities.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginTop: 20, color: 'var(--ink-soft)', fontSize: 12, lineHeight: 1.5 }}>
            <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>These are AI role matches for your current profile, each linking to live job-board search results. They aren't specific verified postings — always confirm details on the employer's page.</span>
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}

const labelStyle = {
  display: 'block',
  fontSize: 12,
  color: 'var(--ink-soft)',
  marginBottom: 6,
  fontWeight: 600,
};

const inputStyle = {
  width: '100%',
  background: 'var(--accent-surface)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
  padding: '10px 12px',
  color: 'var(--ink)',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
};

const chipStyle = (active) => ({
  background: active ? 'var(--ink)' : 'var(--accent-surface)',
  color: active ? 'var(--bone)' : 'var(--ink)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
  padding: '7px 12px',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
});
