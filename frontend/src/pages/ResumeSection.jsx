import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowDownToLine,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { resumeAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

// ── helpers ───────────────────────────────────────────────────────────────────
function cx(...parts) { return parts.filter(Boolean).join(' '); }

function Pill({ children, tone = 'slate' }) {
  const tones = {
    cyan:    'border-cyan-500/20 bg-cyan-500/10 text-cyan-300',
    emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    rose:    'border-rose-500/20 bg-rose-500/10 text-rose-300',
    amber:   'border-amber-500/20 bg-amber-500/10 text-amber-300',
    slate:   'border-white/10 bg-white/5 text-slate-300',
  };
  return (
    <span className={cx('inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider', tones[tone])}>
      {children}
    </span>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-400">
      {children}
    </p>
  );
}

function ResumeBlock({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-white/5 pt-4 first:border-t-0 first:pt-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{title}</p>
        {open ? <ChevronUp size={13} className="text-slate-500" /> : <ChevronDown size={13} className="text-slate-500" />}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

// ── State A: Empty ─────────────────────────────────────────────────────────────
function EmptyState({ onGenerate, onUpload, generating }) {
  const fileRef = useRef(null);

  return (
    <motion.div
      key="empty"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col items-center justify-center gap-8 py-16 text-center"
    >
      <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/5">
        <FileText size={36} className="text-cyan-400" />
      </div>
      <div>
        <h2 className="text-2xl font-black text-white">No resume yet</h2>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
          Delta can generate an ATS-friendly resume from your profile, or you can upload your existing one.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-4">
        <button
          onClick={onGenerate}
          disabled={generating}
          id="resume-generate-btn"
          className="inline-flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:border-cyan-400/60 hover:bg-cyan-400/20 disabled:opacity-50"
        >
          {generating
            ? <Loader2 size={15} className="animate-spin" />
            : <Sparkles size={15} />}
          Generate from my Delta profile
        </button>

        <button
          onClick={() => fileRef.current?.click()}
          id="resume-upload-btn"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-5 py-3 text-sm font-bold text-slate-300 transition hover:border-white/20 hover:text-white"
        >
          <Upload size={15} />
          Upload existing resume
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={e => onUpload(e.target.files?.[0])}
        />
      </div>

      <div className="mt-2 grid max-w-md grid-cols-3 gap-3 text-center">
        {['Skills & proficiency', 'Completed projects', 'Journey achievements'].map(item => (
          <div key={item} className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-3">
            <p className="text-xs text-slate-400">{item}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ── State B: Preview ───────────────────────────────────────────────────────────
function ResumePreview({ resume, onAts, atsLoading, onDownload, downloading, onRefreshSuggestions, suggestionsLoading, suggestionsBadge }) {
  const data = resume?.structured_data || {};
  const contact = data.contact || {};
  const atsScore = Math.round((resume?.ats_score || 0) * 100);
  const atsColor = atsScore >= 70 ? 'emerald' : atsScore >= 50 ? 'amber' : 'rose';

  return (
    <motion.div
      key="preview"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3">
        <div className="flex items-center gap-3">
          <Pill tone={atsColor}>ATS {atsScore}%</Pill>
          <Pill tone={resume?.source === 'uploaded' ? 'amber' : 'cyan'}>
            {resume?.source === 'uploaded' ? 'Uploaded' : 'Generated'}
          </Pill>
          {data._ats_optimized && <Pill tone="emerald">ATS optimized</Pill>}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={onRefreshSuggestions}
            disabled={suggestionsLoading}
            id="resume-suggestions-btn"
            className={cx(
              'relative inline-flex items-center gap-2 rounded-md border px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition',
              suggestionsBadge
                ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200'
                : 'border-white/10 bg-white/[0.03] text-slate-400 hover:text-white'
            )}
          >
            {suggestionsLoading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Check for updates
            {suggestionsBadge && (
              <span className="absolute -right-1.5 -top-1.5 flex h-3 w-3 items-center justify-center rounded-full bg-cyan-400 text-[8px] font-black text-slate-900">
                !
              </span>
            )}
          </button>

          <button
            onClick={onAts}
            disabled={atsLoading}
            id="resume-ats-btn"
            className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-300 transition hover:border-emerald-400/40 hover:text-emerald-200 disabled:opacity-50"
          >
            {atsLoading ? <Loader2 size={12} className="animate-spin" /> : <ShieldCheck size={12} />}
            ATS Mode
          </button>

          <button
            onClick={onDownload}
            disabled={downloading}
            id="resume-download-btn"
            className="inline-flex items-center gap-2 rounded-md border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-cyan-200 transition hover:border-cyan-400/60 disabled:opacity-50"
          >
            {downloading ? <Loader2 size={12} className="animate-spin" /> : <ArrowDownToLine size={12} />}
            Download .docx
          </button>
        </div>
      </div>

      {/* Resume card */}
      <div className="rounded-lg border border-white/5 bg-white/[0.015] p-6 space-y-5">
        {/* Header */}
        <div className="border-b border-white/5 pb-4">
          <h2 className="text-2xl font-black text-white">{contact.name || 'Your Name'}</h2>
          <p className="mt-1 text-sm font-semibold text-cyan-300">{contact.role || 'Target Role'}</p>
          {contact.email && <p className="mt-1 text-xs text-slate-500">{contact.email}</p>}
        </div>

        {/* Summary */}
        {data.summary && (
          <ResumeBlock title="Summary">
            <p className="text-sm leading-relaxed text-slate-300">{data.summary}</p>
          </ResumeBlock>
        )}

        {/* Skills */}
        {(data.skills || []).length > 0 && (
          <ResumeBlock title={`Skills (${(data.skills || []).length})`}>
            <div className="flex flex-wrap gap-2">
              {(data.skills || []).map(skill => (
                <span key={skill} className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300">
                  {skill}
                </span>
              ))}
            </div>
          </ResumeBlock>
        )}

        {/* Achievements */}
        {(data.achievements || []).length > 0 && (
          <ResumeBlock title={`Achievements (${(data.achievements || []).length})`}>
            <ul className="space-y-2">
              {(data.achievements || []).map((ach, i) => (
                <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-slate-300">
                  <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-400" />
                  {ach}
                </li>
              ))}
            </ul>
          </ResumeBlock>
        )}

        {/* Projects */}
        {(data.projects || []).length > 0 && (
          <ResumeBlock title={`Projects (${(data.projects || []).length})`}>
            <div className="space-y-4">
              {(data.projects || []).map((proj, i) => (
                <div key={i}>
                  <p className="font-bold text-white">{proj.title}</p>
                  {proj.description && <p className="mt-1 text-xs leading-relaxed text-slate-400">{proj.description}</p>}
                  {proj.tech && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(Array.isArray(proj.tech) ? proj.tech : [proj.tech]).map(t => (
                        <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-400">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ResumeBlock>
        )}

        {/* Education */}
        {(data.education || []).filter(e => e.degree).length > 0 && (
          <ResumeBlock title="Education">
            {(data.education || []).filter(e => e.degree).map((edu, i) => (
              <div key={i} className="text-sm text-slate-300">
                <span className="font-bold">{edu.degree}</span>
                {edu.institution && <span className="text-slate-500"> · {edu.institution}</span>}
                {edu.year && <span className="text-slate-600"> · {edu.year}</span>}
              </div>
            ))}
          </ResumeBlock>
        )}

        {/* ATS keywords (shown when optimized) */}
        {data._ats_keywords?.length > 0 && (
          <ResumeBlock title="ATS Keywords Applied" defaultOpen={false}>
            <div className="flex flex-wrap gap-2">
              {data._ats_keywords.map(kw => (
                <span key={kw} className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300">{kw}</span>
              ))}
            </div>
          </ResumeBlock>
        )}
      </div>
    </motion.div>
  );
}

// ── State C: Suggestions Diff ─────────────────────────────────────────────────
function SuggestionsDiff({ suggestions, onClose, onApply, applying }) {
  const { to_add = [], to_remove = [] } = suggestions;
  const [acceptedAdds, setAcceptedAdds] = useState(() => new Set(to_add.map((_, i) => i)));
  const [acceptedRemoves, setAcceptedRemoves] = useState(() => new Set());

  const toggleAdd = (i) => setAcceptedAdds(prev => {
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    return next;
  });

  const toggleRemove = (i) => setAcceptedRemoves(prev => {
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    return next;
  });

  const handleApply = () => {
    const adds = to_add.filter((_, i) => acceptedAdds.has(i));
    const removes = to_remove.filter((_, i) => acceptedRemoves.has(i)).map(r => r.value);
    onApply({ accepted_adds: adds, accepted_removes: removes });
  };

  return (
    <motion.div
      key="suggestions"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-cyan-400">
            Bi-weekly Resume Update
          </p>
          <h3 className="mt-1 text-lg font-black text-white">
            Delta found {to_add.length + to_remove.length} updates for your resume
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            Review each suggestion. Select what to keep, then click "Apply selected".
          </p>
        </div>
        <button onClick={onClose} className="rounded-md border border-white/10 p-1.5 text-slate-400 hover:text-white">
          <X size={14} />
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Additions */}
        <div>
          <SectionLabel>
            <span className="flex items-center gap-1.5">
              <Plus size={11} className="text-emerald-400" />
              To add ({to_add.length})
            </span>
          </SectionLabel>
          {to_add.length === 0 ? (
            <p className="py-4 text-xs text-slate-500">No new additions detected.</p>
          ) : (
            <div className="space-y-2">
              {to_add.map((item, i) => {
                const accepted = acceptedAdds.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggleAdd(i)}
                    className={cx(
                      'w-full rounded-lg border p-3 text-left transition',
                      accepted
                        ? 'border-emerald-500/40 bg-emerald-500/10'
                        : 'border-white/5 bg-white/[0.02] hover:border-white/10'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={cx(
                        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition',
                        accepted
                          ? 'border-emerald-400 bg-emerald-400 text-slate-950'
                          : 'border-slate-600'
                      )}>
                        {accepted && <CheckCircle2 size={11} />}
                      </span>
                      <div className="min-w-0">
                        <p className={cx('text-xs font-semibold leading-relaxed', accepted ? 'text-emerald-200' : 'text-slate-300')}>
                          {item.value}
                        </p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className={cx(
                            'rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider',
                            item.type === 'skill'
                              ? 'bg-cyan-500/10 text-cyan-400'
                              : 'bg-emerald-500/10 text-emerald-400'
                          )}>
                            {item.type}
                          </span>
                          {item.date && <span className="text-[9px] text-slate-600">{item.date}</span>}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Removals */}
        <div>
          <SectionLabel>
            <span className="flex items-center gap-1.5">
              <Trash2 size={11} className="text-rose-400" />
              To remove / update ({to_remove.length})
            </span>
          </SectionLabel>
          {to_remove.length === 0 ? (
            <p className="py-4 text-xs text-slate-500">No outdated items detected.</p>
          ) : (
            <div className="space-y-2">
              {to_remove.map((item, i) => {
                const accepted = acceptedRemoves.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggleRemove(i)}
                    className={cx(
                      'w-full rounded-lg border p-3 text-left transition',
                      accepted
                        ? 'border-rose-500/40 bg-rose-500/10'
                        : 'border-white/5 bg-white/[0.02] hover:border-white/10'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={cx(
                        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition',
                        accepted
                          ? 'border-rose-400 bg-rose-400 text-white'
                          : 'border-slate-600'
                      )}>
                        {accepted && <XCircle size={11} />}
                      </span>
                      <div className="min-w-0">
                        <p className={cx('text-xs font-semibold leading-relaxed line-through', accepted ? 'text-rose-300' : 'text-slate-300')}>
                          {item.value}
                        </p>
                        {item.reason && (
                          <p className="mt-1 text-[10px] leading-relaxed text-slate-500">{item.reason}</p>
                        )}
                        <span className={cx(
                          'mt-1 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider',
                          item.type === 'skill'
                            ? 'bg-cyan-500/10 text-cyan-400'
                            : 'bg-rose-500/10 text-rose-400'
                        )}>
                          {item.type}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/[0.02] p-4">
        <p className="text-xs text-slate-400">
          {acceptedAdds.size} addition{acceptedAdds.size !== 1 ? 's' : ''} · {acceptedRemoves.size} removal{acceptedRemoves.size !== 1 ? 's' : ''} selected
        </p>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-white/10 px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 hover:text-white"
          >
            Skip for now
          </button>
          <button
            onClick={handleApply}
            disabled={applying || (acceptedAdds.size === 0 && acceptedRemoves.size === 0)}
            id="resume-apply-suggestions-btn"
            className="inline-flex items-center gap-2 rounded-md border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-cyan-200 transition hover:border-cyan-400/60 disabled:opacity-40"
          >
            {applying && <Loader2 size={12} className="animate-spin" />}
            Apply selected changes
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function ResumeSection() {
  const userId = useAuthStore(state => state.userId);

  const [resumeData, setResumeData] = useState(null);   // { exists, resume, suggestions_due }
  const [view, setView] = useState('preview');           // 'preview' | 'suggestions'
  const [suggestions, setSuggestions] = useState(null);

  // Loading states
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [atsLoading, setAtsLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const fileRef = useRef(null);

  // ── Load resume ──────────────────────────────────────────────────────────────
  const loadResume = useCallback(async () => {
    setLoading(true);
    try {
      const data = await resumeAPI.get(userId);
      setResumeData(data);
    } catch (err) {
      console.error(err);
      // 404 = no resume yet, that's fine
      setResumeData({ exists: false, resume: null, suggestions_due: false });
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { loadResume(); }, [loadResume]);

  // ── Generate ─────────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await resumeAPI.generate(userId);
      setResumeData({ exists: true, resume: result.resume, suggestions_due: false });
      toast.success('Resume generated from your Delta profile!');
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate resume. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  // ── Upload ───────────────────────────────────────────────────────────────────
  const handleUpload = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    try {
      const result = await resumeAPI.upload(userId, formData);
      setResumeData({ exists: true, resume: result.resume, suggestions_due: false });
      toast.success(`Resume uploaded! Detected ${result.parsed_skills_count} skills.`);
    } catch (err) {
      console.error(err);
      toast.error('Upload failed. Supported formats: PDF, DOCX.');
    } finally {
      setUploading(false);
    }
  };

  // ── Suggestions ──────────────────────────────────────────────────────────────
  const handleCheckSuggestions = async () => {
    setSuggestionsLoading(true);
    try {
      const data = await resumeAPI.getSuggestions(userId);
      setSuggestions(data);
      setView('suggestions');
    } catch (err) {
      console.error(err);
      toast.error('Could not fetch suggestions.');
    } finally {
      setSuggestionsLoading(false);
    }
  };

  const handleApplySuggestions = async (payload) => {
    setApplying(true);
    try {
      const result = await resumeAPI.applySuggestions(userId, payload);
      setResumeData(prev => ({ ...prev, resume: result.resume, suggestions_due: false }));
      setSuggestions(null);
      setView('preview');
      toast.success('Resume updated with selected changes!');
    } catch (err) {
      console.error(err);
      toast.error('Failed to apply suggestions.');
    } finally {
      setApplying(false);
    }
  };

  // ── ATS Optimize ─────────────────────────────────────────────────────────────
  const handleAtsOptimize = async () => {
    setAtsLoading(true);
    try {
      const result = await resumeAPI.atsOptimize(userId);
      setResumeData(prev => ({ ...prev, resume: result.resume }));
      toast.success('Resume optimized for ATS keywords!');
    } catch (err) {
      console.error(err);
      toast.error('ATS optimization failed.');
    } finally {
      setAtsLoading(false);
    }
  };

  // ── Download ─────────────────────────────────────────────────────────────────
  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await resumeAPI.download(userId);
      const name = resumeData?.resume?.structured_data?.contact?.name || 'resume';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name.replace(/\s+/g, '_')}_resume.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Resume downloaded!');
    } catch (err) {
      console.error(err);
      toast.error('Download failed.');
    } finally {
      setDownloading(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────
  if (loading || uploading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-slate-400">
        <Loader2 size={24} className="animate-spin text-cyan-400" />
        <p className="text-xs uppercase tracking-widest">
          {uploading ? 'Parsing resume…' : 'Loading resume…'}
        </p>
      </div>
    );
  }

  const hasResume = resumeData?.exists && resumeData?.resume;
  const suggestionsBadge = resumeData?.suggestions_due;

  return (
    <div className="space-y-0">
      <AnimatePresence mode="wait">
        {!hasResume && (
          <EmptyState
            key="empty"
            onGenerate={handleGenerate}
            onUpload={handleUpload}
            generating={generating}
          />
        )}

        {hasResume && view === 'suggestions' && suggestions && (
          <SuggestionsDiff
            key="suggestions"
            suggestions={suggestions}
            onClose={() => setView('preview')}
            onApply={handleApplySuggestions}
            applying={applying}
          />
        )}

        {hasResume && view === 'preview' && (
          <ResumePreview
            key="preview"
            resume={resumeData.resume}
            onAts={handleAtsOptimize}
            atsLoading={atsLoading}
            onDownload={handleDownload}
            downloading={downloading}
            onRefreshSuggestions={handleCheckSuggestions}
            suggestionsLoading={suggestionsLoading}
            suggestionsBadge={suggestionsBadge}
          />
        )}
      </AnimatePresence>

      {/* Hidden file input for toolbar upload */}
      {hasResume && (
        <div className="mt-4 flex items-center gap-2 border-t border-white/5 pt-4">
          <p className="text-[10px] text-slate-600">Replace resume:</p>
          <button
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-1.5 rounded border border-white/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-300"
          >
            <Upload size={10} /> Upload new
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.doc"
            className="hidden"
            onChange={e => handleUpload(e.target.files?.[0])}
          />
          {resumeData?.resume?.updated_at && (
            <p className="ml-auto text-[10px] text-slate-600">
              Updated {new Date(resumeData.resume.updated_at).toLocaleDateString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
