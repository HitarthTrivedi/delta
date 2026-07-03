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
    cyan:    'border-oxblood/20 bg-oxblood/10 text-oxblood',
    emerald: 'border-ink/20 bg-ink/5 text-ink',
    rose:    'border-oxblood/20 bg-oxblood/10 text-oxblood',
    amber:   'border-rule bg-accent-surface text-ink-soft',
    slate:   'border-rule bg-paper text-ink',
  };
  return (
    <span className={cx('inline-flex items-center border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider', tones[tone])}>
      {children}
    </span>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.22em] text-oxblood">
      {children}
    </p>
  );
}

function ResumeBlock({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-rule pt-4 first:border-t-0 first:pt-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <p className="text-[11px] font-bold uppercase tracking-widest text-ink-soft">{title}</p>
        {open ? <ChevronUp size={13} className="text-ink-soft" /> : <ChevronDown size={13} className="text-ink-soft" />}
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
      <div className="flex h-20 w-20 items-center justify-center border border-oxblood/20 bg-oxblood/5">
        <FileText size={36} className="text-oxblood" />
      </div>
      <div>
        <h2 className="text-2xl font-black text-ink">No resume yet</h2>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-soft">
          Delta can generate an ATS-friendly resume from your profile, or you can upload your existing one.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-4">
        <button
          onClick={onGenerate}
          disabled={generating}
          id="resume-generate-btn"
          className="inline-flex items-center gap-2 border border-oxblood/30 bg-oxblood/10 px-5 py-3 text-sm font-bold text-oxblood transition hover:border-oxblood/60 hover:bg-oxblood/20 disabled:opacity-50"
        >
          {generating
            ? <Loader2 size={15} className="animate-spin" />
            : <Sparkles size={15} />}
          Generate from my Delta profile
        </button>

        <button
          onClick={() => fileRef.current?.click()}
          id="resume-upload-btn"
          className="inline-flex items-center gap-2 border border-rule bg-paper px-5 py-3 text-sm font-bold text-ink transition hover:border-rule hover:text-ink"
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
          <div key={item} className="border border-rule bg-paper px-3 py-3">
            <p className="text-xs text-ink-soft">{item}</p>
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
      <div className="flex flex-wrap items-center justify-between gap-3 border border-rule bg-paper p-3">
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
              'relative inline-flex items-center gap-2 border px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition',
              suggestionsBadge
                ? 'border-oxblood/40 bg-oxblood/10 text-oxblood'
                : 'border-rule bg-paper text-ink-soft hover:text-ink'
            )}
          >
            {suggestionsLoading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Check for updates
            {suggestionsBadge && (
              <span className="absolute -right-1.5 -top-1.5 flex h-3 w-3 items-center justify-center bg-oxblood text-[8px] font-black text-bone">
                !
              </span>
            )}
          </button>

          <button
            onClick={onAts}
            disabled={atsLoading}
            id="resume-ats-btn"
            className="inline-flex items-center gap-2 border border-rule bg-paper px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-ink transition hover:border-oxblood/40 hover:text-oxblood disabled:opacity-50"
          >
            {atsLoading ? <Loader2 size={12} className="animate-spin" /> : <ShieldCheck size={12} />}
            ATS Mode
          </button>

          <button
            onClick={onDownload}
            disabled={downloading}
            id="resume-download-btn"
            className="inline-flex items-center gap-2 border border-oxblood/30 bg-oxblood/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-oxblood transition hover:border-oxblood/60 disabled:opacity-50"
          >
            {downloading ? <Loader2 size={12} className="animate-spin" /> : <ArrowDownToLine size={12} />}
            Download .docx
          </button>
        </div>
      </div>

      {/* Resume card */}
      <div className="border border-rule bg-paper p-6 space-y-5">
        {/* Header */}
        <div className="border-b border-rule pb-4">
          <h2 className="text-2xl font-black text-ink">{contact.name || 'Your Name'}</h2>
          <p className="mt-1 text-sm font-semibold text-oxblood">{contact.role || 'Target Role'}</p>
          {contact.email && <p className="mt-1 text-xs text-ink-soft">{contact.email}</p>}
        </div>

        {/* Summary */}
        {data.summary && (
          <ResumeBlock title="Summary">
            <p className="text-sm leading-relaxed text-ink">{data.summary}</p>
          </ResumeBlock>
        )}

        {/* Skills */}
        {(data.skills || []).length > 0 && (
          <ResumeBlock title={`Skills (${(data.skills || []).length})`}>
            <div className="flex flex-wrap gap-2">
              {(data.skills || []).map(skill => (
                <span key={skill} className="border border-rule bg-paper px-2 py-1 text-xs text-ink">
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
                <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink">
                  <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-ink" />
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
                  <p className="font-bold text-ink">{proj.title}</p>
                  {proj.description && <p className="mt-1 text-xs leading-relaxed text-ink-soft">{proj.description}</p>}
                  {proj.tech && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(Array.isArray(proj.tech) ? proj.tech : [proj.tech]).map(t => (
                        <span key={t} className="bg-paper px-1.5 py-0.5 text-[10px] text-ink-soft">{t}</span>
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
              <div key={i} className="text-sm text-ink">
                <span className="font-bold">{edu.degree}</span>
                {edu.institution && <span className="text-ink-soft"> · {edu.institution}</span>}
                {edu.year && <span className="text-ink-soft"> · {edu.year}</span>}
              </div>
            ))}
          </ResumeBlock>
        )}

        {/* ATS keywords (shown when optimized) */}
        {data._ats_keywords?.length > 0 && (
          <ResumeBlock title="ATS Keywords Applied" defaultOpen={false}>
            <div className="flex flex-wrap gap-2">
              {data._ats_keywords.map(kw => (
                <span key={kw} className="border border-rule bg-accent-surface px-2 py-0.5 text-[10px] text-ink-soft">{kw}</span>
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
      <div className="flex items-start justify-between gap-4 border border-oxblood/20 bg-oxblood/5 p-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-oxblood">
            Bi-weekly Resume Update
          </p>
          <h3 className="mt-1 text-lg font-black text-ink">
            Delta found {to_add.length + to_remove.length} updates for your resume
          </h3>
          <p className="mt-1 text-xs text-ink-soft">
            Review each suggestion. Select what to keep, then click "Apply selected".
          </p>
        </div>
        <button onClick={onClose} aria-label="Close" className="border border-rule p-1.5 text-ink-soft hover:text-ink">
          <X size={14} />
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Additions */}
        <div>
          <SectionLabel>
            <span className="flex items-center gap-1.5">
              <Plus size={11} className="text-ink" />
              To add ({to_add.length})
            </span>
          </SectionLabel>
          {to_add.length === 0 ? (
            <p className="py-4 text-xs text-ink-soft">No new additions detected.</p>
          ) : (
            <div className="space-y-2">
              {to_add.map((item, i) => {
                const accepted = acceptedAdds.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggleAdd(i)}
                    className={cx(
                      'w-full border p-3 text-left transition',
                      accepted
                        ? 'border-ink/40 bg-ink/5'
                        : 'border-rule bg-paper hover:border-rule'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={cx(
                        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border transition',
                        accepted
                          ? 'border-ink bg-ink text-bone'
                          : 'border-rule'
                      )}>
                        {accepted && <CheckCircle2 size={11} />}
                      </span>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold leading-relaxed text-ink">
                          {item.value}
                        </p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className={cx(
                            'px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider',
                            item.type === 'skill'
                              ? 'bg-oxblood/10 text-oxblood'
                              : 'bg-accent-surface text-ink-soft'
                          )}>
                            {item.type}
                          </span>
                          {item.date && <span className="text-[9px] text-ink-soft">{item.date}</span>}
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
              <Trash2 size={11} className="text-oxblood" />
              To remove / update ({to_remove.length})
            </span>
          </SectionLabel>
          {to_remove.length === 0 ? (
            <p className="py-4 text-xs text-ink-soft">No outdated items detected.</p>
          ) : (
            <div className="space-y-2">
              {to_remove.map((item, i) => {
                const accepted = acceptedRemoves.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggleRemove(i)}
                    className={cx(
                      'w-full border p-3 text-left transition',
                      accepted
                        ? 'border-oxblood/40 bg-oxblood/10'
                        : 'border-rule bg-paper hover:border-rule'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={cx(
                        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border transition',
                        accepted
                          ? 'border-oxblood bg-oxblood text-bone'
                          : 'border-rule'
                      )}>
                        {accepted && <XCircle size={11} />}
                      </span>
                      <div className="min-w-0">
                        <p className={cx('text-xs font-semibold leading-relaxed line-through', accepted ? 'text-oxblood' : 'text-ink')}>
                          {item.value}
                        </p>
                        {item.reason && (
                          <p className="mt-1 text-[10px] leading-relaxed text-ink-soft">{item.reason}</p>
                        )}
                        <span className="mt-1 bg-oxblood/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-oxblood">
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
      <div className="flex flex-wrap items-center justify-between gap-4 border border-rule bg-paper p-4">
        <p className="text-xs text-ink-soft">
          {acceptedAdds.size} addition{acceptedAdds.size !== 1 ? 's' : ''} · {acceptedRemoves.size} removal{acceptedRemoves.size !== 1 ? 's' : ''} selected
        </p>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="border border-rule px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-ink-soft hover:text-ink"
          >
            Skip for now
          </button>
          <button
            onClick={handleApply}
            disabled={applying || (acceptedAdds.size === 0 && acceptedRemoves.size === 0)}
            id="resume-apply-suggestions-btn"
            className="inline-flex items-center gap-2 border border-oxblood/30 bg-oxblood/10 px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-oxblood transition hover:border-oxblood/60 disabled:opacity-40"
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
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-ink-soft">
        <Loader2 size={24} className="animate-spin text-oxblood" />
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
        <div className="mt-4 flex items-center gap-2 border-t border-rule pt-4">
          <p className="text-[10px] text-ink-soft">Replace resume:</p>
          <button
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-1.5 border border-rule px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-ink-soft hover:text-ink"
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
            <p className="ml-auto text-[10px] text-ink-soft">
              Updated {new Date(resumeData.resume.updated_at).toLocaleDateString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
