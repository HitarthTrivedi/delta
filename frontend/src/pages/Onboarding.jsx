import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Paperclip, CheckCircle2, Loader2, ClipboardList,
  Edit3, Save, ChevronLeft, ChevronRight
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useUserWithSkills } from '../hooks/useUser';
import { useQueryClient } from '@tanstack/react-query';
import { ingestionAPI } from '../lib/api';
import { toast } from 'sonner';

/* ─── PDF / DOCX / TXT parser ─── */
const parseFile = async (file) => {
  if (file.type === 'text/plain' || file.name.endsWith('.txt') || file.name.endsWith('.md')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  }

  if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const typedarray = new Uint8Array(e.target.result);
          if (!window.pdfjsLib) {
            await new Promise((res, rej) => {
              const s = document.createElement('script');
              s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js';
              s.onload = () => {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc =
                  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
                res();
              };
              s.onerror = rej;
              document.head.appendChild(s);
            });
          }
          const pdf = await window.pdfjsLib.getDocument(typedarray).promise;
          let text = '';
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const content = await page.getTextContent();
            text += content.items.map(it => it.str).join(' ') + '\n';
          }
          resolve(text);
        } catch (err) {
          reject(new Error('Failed to parse PDF. Make sure it is a text-based PDF.'));
        }
      };
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  }

  if (
    file.name.endsWith('.docx') ||
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          if (!window.mammoth) {
            await new Promise((res, rej) => {
              const s = document.createElement('script');
              s.src = 'https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js';
              s.onload = res;
              s.onerror = rej;
              document.head.appendChild(s);
            });
          }
          const result = await window.mammoth.extractRawText({ arrayBuffer: e.target.result });
          resolve(result.value);
        } catch (err) {
          reject(new Error('Failed to parse DOCX file.'));
        }
      };
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  }

  throw new Error('Unsupported file type. Use .pdf, .docx, .txt, or .md');
};

const REQUIRED_FIELDS_METADATA = [
  { key: 'name', label: 'Name' },
  { key: 'current_status', label: 'Status' },
  { key: 'education_stage', label: 'Stage' },
  { key: 'target_role', label: 'Direction' },
  { key: 'goal_direction', label: 'Goal' },
  { key: 'learning_style', label: 'Style' },
  { key: 'hours_per_week', label: 'Hours' },
  { key: 'skills', label: 'Skills' },
  { key: 'past_experience', label: 'Experience' },
  { key: 'career_goals', label: 'Goals' },
];

/* Helper conversions for arrays */
const arrayToString = (val) => {
  if (Array.isArray(val)) return val.join(', ');
  return val || '';
};

const stringToArray = (str) => {
  if (typeof str !== 'string') return str || [];
  return str.split(',').map(s => s.trim()).filter(Boolean);
};

/* ─── Main Onboarding Page ─── */
export default function Onboarding() {
  const navigate  = useNavigate();
  const queryClient = useQueryClient();
  const userId    = useAuthStore(state => state.userId);
  const { data: user, isLoading: isUserLoading } = useUserWithSkills(userId);

  const [sessionId,  setSessionId]  = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isDone,     setIsDone]     = useState(false);
  const [reviewMode, setReviewMode] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [parsing,    setParsing]    = useState(false);

  // Wizard state: one question per screen, resume-first, with go-back editing
  const [phase,  setPhase]  = useState('resume');   // 'resume' | 'questions'
  const [steps,  setSteps]  = useState([]);          // [{ question, answer, round }]
  const [cursor, setCursor] = useState(0);
  const [draft,  setDraft]  = useState('');

  const [progress, setProgress] = useState(0);
  const [filledFields, setFilledFields] = useState([]);
  const [profile, setProfile] = useState({});
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const fileRef = useRef(null);

  /* load profile data on complete */
  const loadProfileData = useCallback(async () => {
    try {
      const data = await ingestionAPI.getProfile(userId);
      setProfile(data);
    } catch (e) {
      console.error("Could not load profile:", e);
    }
  }, [userId]);

  /* load state & start session */
  useEffect(() => {
    (async () => {
      try {
        setIsThinking(true);
        // Load latest ingestion state first to populate progress
        const state = await ingestionAPI.getState(userId);
        setProgress(Math.round((state.confidence_score || 0) * 100));
        setFilledFields(state.filled_fields || []);
        if (state.profile) {
          setProfile(state.profile);
        }
        
        if (state.onboarding_complete || state.profile_review_pending) {
          setIsDone(true);
          setReviewMode(!!state.profile_review_pending && !state.onboarding_complete);
          await loadProfileData();
          return;
        }

        const res = await ingestionAPI.start(userId, 'general');
        setSessionId(res.session_id);
        const firstQ = res.initial_question || res.message ||
          "Let's start with the basics: your name, what you're currently doing (school, college, or working), and the role or field you want to build toward.";
        setSteps([{ question: firstQ, answer: '', round: null }]);
        setCursor(0);
        setDraft('');
        // phase stays 'resume' — the user uploads or skips a resume before questions
      } catch (e) {
        console.error(e);
        setSteps([{ question: "Let's start with the basics: your name, what you're currently doing, and the role or field you want to build toward.", answer: '', round: null }]);
      } finally {
        setIsThinking(false);
      }
    })();
  }, [userId, loadProfileData]);

  const applyProgress = useCallback((res) => {
    if (res.confidence_score !== undefined) setProgress(Math.round(res.confidence_score * 100));
    if (res.filled_fields) setFilledFields(res.filled_fields);
    if (res.profile) setProfile(res.profile);
  }, []);

  /* submit the current answer, or save an edited earlier answer, then advance */
  const handleNext = useCallback(async () => {
    const text = draft.trim();
    if (!text || isThinking) return;
    const step = steps[cursor];
    const isCurrent = cursor === steps.length - 1 && !step.round;

    setIsThinking(true);
    try {
      if (isCurrent) {
        const res = await ingestionAPI.submitAnswer(userId, sessionId, text);
        applyProgress(res);
        const goReview = res.review_required || res.status === 'review_required';
        setSteps(prev => {
          const next = [...prev];
          next[cursor] = { ...next[cursor], answer: text, round: res.round ?? (cursor + 1) };
          if (!goReview) {
            const q = res.next_question || res.message;
            if (q) next.push({ question: q, answer: '', round: null });
          }
          return next;
        });
        if (goReview) {
          setIsDone(true);
          setReviewMode(true);
          await loadProfileData();
          queryClient.invalidateQueries({ queryKey: ['user', userId] });
        } else {
          setCursor(c => c + 1);
          setDraft('');
        }
      } else {
        // Revisiting an already-answered question
        if (text !== step.answer && step.round != null) {
          const res = await ingestionAPI.editAnswer(userId, sessionId, step.round, text);
          applyProgress(res);
          setSteps(prev => {
            const next = [...prev];
            next[cursor] = { ...next[cursor], answer: text };
            return next;
          });
        }
        const nextCursor = cursor + 1;
        setCursor(nextCursor);
        setDraft(steps[nextCursor]?.answer || '');
      }
    } catch (e) {
      console.error(e);
      toast.error('Something went wrong. Please try again.');
    } finally {
      setIsThinking(false);
    }
  }, [draft, isThinking, steps, cursor, userId, sessionId, applyProgress, queryClient, loadProfileData]);

  const handleBack = () => {
    if (cursor === 0 || isThinking) return;
    const prev = cursor - 1;
    setCursor(prev);
    setDraft(steps[prev]?.answer || '');
  };

  const skipResume = () => setPhase('questions');

  /* resume upload — pre-fills the profile via the dedicated extraction endpoint */
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    setParsing(true);
    try {
      const text = await parseFile(file);
      setUploadFile({ name: file.name });
      const res = await ingestionAPI.ingestResume(userId, sessionId, text);

      if (res.success) {
        applyProgress(res);
        toast.success('Resume analyzed — details pre-filled.');
        if (res.review_required || res.status === 'review_required') {
          setIsDone(true);
          setReviewMode(true);
          await loadProfileData();
          queryClient.invalidateQueries({ queryKey: ['user', userId] });
          return;
        }
        const q = res.follow_up || res.message;
        if (q) {
          setSteps([{ question: q, answer: '', round: null }]);
          setCursor(0);
          setDraft('');
        }
        setPhase('questions');
      } else {
        toast.error(res.message || 'Could not read that resume. You can continue by answering the questions.');
        setUploadFile(null);
      }
    } catch (err) {
      toast.error(err.message || 'Failed to parse file.');
      setUploadFile(null);
    } finally {
      setParsing(false);
    }
  };

  const handleProfileFieldChange = (key, value) => {
    setProfile(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const updates = {
        ...profile,
        skills: Array.isArray(profile.skills) ? profile.skills : stringToArray(profile.skills),
        career_goals: Array.isArray(profile.career_goals) ? profile.career_goals : stringToArray(profile.career_goals),
        target_industries: Array.isArray(profile.target_industries) ? profile.target_industries : stringToArray(profile.target_industries),
        preferred_content_types: Array.isArray(profile.preferred_content_types) ? profile.preferred_content_types : stringToArray(profile.preferred_content_types),
        extracurricular_interests: Array.isArray(profile.extracurricular_interests) ? profile.extracurricular_interests : stringToArray(profile.extracurricular_interests),
        projects: Array.isArray(profile.projects) ? profile.projects : stringToArray(profile.projects),
        constraints: Array.isArray(profile.constraints) ? profile.constraints : stringToArray(profile.constraints),
        has_resume: profile.has_resume === true || profile.has_resume === 'true',
        no_experience_yet: profile.no_experience_yet === true || profile.no_experience_yet === 'true',
        hours_per_week: Number(profile.hours_per_week) || 10,
        planning_horizon_years: Number(profile.planning_horizon_years) || 1,
        planning_horizon_months: Number(profile.planning_horizon_months) || undefined,
      };

      await ingestionAPI.updateProfile(userId, updates);
      toast.success("Profile details updated successfully.");
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      setIsEditing(false);
      // Reload profile data back to state
      await loadProfileData();
    } catch (e) {
      console.error(e);
      toast.error("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmProfile = async () => {
    if (isEditing) return;
    try {
      if (reviewMode) {
        await ingestionAPI.forceComplete(userId);
        setReviewMode(false);
        queryClient.invalidateQueries({ queryKey: ['user', userId] });
        queryClient.invalidateQueries({ queryKey: ['user-with-skills', userId] });
      }
      navigate('/roadmap?from=intake');
    } catch (e) {
      console.error(e);
      toast.error("Could not finalize your profile yet.");
    }
  };

  // If profile is ready/complete, show review dashboard before roadmap
  if (user?.onboarding_complete || isDone) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'var(--bone)',
        color: 'var(--ink)',
        fontFamily: "'Manrope', sans-serif",
        paddingTop: '5rem',
        paddingBottom: '3rem',
        paddingLeft: 'clamp(1rem, 4vw, 2rem)',
        paddingRight: 'clamp(1rem, 4vw, 2rem)',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <div style={{ maxWidth: 880, width: '100%', minWidth: 0 }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 35 }}>
            <div style={{
              width: 54, height: 54, borderRadius: 0, background: 'var(--ink)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
            }}>
              <CheckCircle2 size={26} style={{ color: 'var(--bone)' }} />
            </div>
            <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", color: 'var(--oxblood)', fontSize: 'clamp(1.4rem, 5vw, 2rem)', fontWeight: 600, letterSpacing: 0, marginBottom: 8 }}>
              {reviewMode ? 'Review Your Delta Profile' : 'Onboarding Profile Sync'}
            </h1>
            <p style={{ color: 'var(--ink-soft)', fontSize: '0.9rem', lineHeight: 1.6, maxWidth: 500, margin: '0 auto' }}>
              {reviewMode
                ? 'Check the details Delta collected. Edit anything that feels wrong or incomplete before the roadmap is created.'
                : 'Your details are gathered. You can modify any parsed fields below to fine-tune your profile.'}
            </p>
          </div>

          {/* Form / Snapshot Container */}
          <div style={{
            background: 'var(--accent-surface)',
            border: '1px solid var(--accent-surface)',
            borderRadius: 0,
            padding: 'clamp(14px, 3vw, 30px) clamp(14px, 4vw, 30px)',
            marginBottom: 30,
          }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, borderBottom: '1px solid var(--rule)', paddingBottom: 10 }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>
                {isEditing ? 'Modify Intake Details' : 'Active Profile Snapshot'}
              </h2>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  style={{
                    background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer',
                    fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, opacity: 0.6,
                    transition: 'opacity 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                  onMouseLeave={e => e.currentTarget.style.opacity = '0.6'}
                >
                  <Edit3 size={13} /> Edit Profile
                </button>
              ) : (
                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    onClick={handleSaveProfile}
                    disabled={saving}
                    style={{
                      background: 'var(--ink)', border: 'none', color: 'var(--bone)', cursor: 'pointer',
                      fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700,
                      padding: '4px 12px', borderRadius: 0,
                    }}
                  >
                    {saving ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={12} />}
                    Save Changes
                  </button>
                  <button
                    onClick={() => { setIsEditing(false); loadProfileData(); }}
                    style={{
                      background: 'none', border: '1px solid var(--rule)', color: 'var(--ink-soft)',
                      cursor: 'pointer', fontSize: '0.8rem', padding: '4px 12px', borderRadius: 0,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            {/* Profile Fields Editor Grid — Tailwind's compiled breakpoints,
                not a hand-rolled media query, so the collapse to one column
                on mobile is guaranteed rather than inferred. */}
            <div className="grid grid-cols-1 sm:grid-cols-2 onboarding-field-grid" style={{ gap: 20 }}>
              {/* Field Block Helper */}
              {[{ key: 'name', label: 'Full Name', type: 'text' },
                { key: 'email', label: 'Email Address', type: 'text' },
                { key: 'current_status', label: 'Current Status', type: 'select', options: ['school', 'dropped_out', 'undergrad', 'graduate', 'working', 'career_switcher', 'exam_aspirant', 'other'] },
                { key: 'education_stage', label: 'Education / Life Stage', type: 'text' },
                { key: 'target_role', label: 'Target Career Role', type: 'text' },
                { key: 'goal_direction', label: 'Goal Direction if Role is Unclear', type: 'text' },
                { key: 'major', label: 'Degree Major / School Stream', type: 'text' },
                { key: 'university', label: 'School / College / University', type: 'text' },
                { key: 'study_year', label: 'Class / Year / Status', type: 'text' },
                { key: 'gpa', label: 'GPA', type: 'text' },
                { key: 'phone_number', label: 'Phone Number', type: 'text' },
                { key: 'linkedin_url', label: 'LinkedIn Profile URL', type: 'text' },
                { key: 'github_url', label: 'GitHub Profile URL', type: 'text' },
                { key: 'portfolio_url', label: 'Portfolio URL', type: 'text' },
                { key: 'experience_level', label: 'Experience Level', type: 'select', options: ['beginner', 'intermediate', 'advanced'] },
                { key: 'learning_style', label: 'Learning Style', type: 'select', options: ['practical', 'theoretical', 'mixed'] },
                { key: 'relocation', label: 'Relocation Openness', type: 'select', options: ['yes', 'no', 'maybe'] },
                { key: 'has_resume', label: 'Has Resume?', type: 'select', options: ['true', 'false'] },
                { key: 'no_experience_yet', label: 'No Experience Yet?', type: 'select', options: ['true', 'false'] },
                { key: 'hours_per_week', label: 'Weekly Hours Commitment', type: 'number' },
                { key: 'planning_horizon_years', label: 'Inferred Planning Horizon (Years)', type: 'number' },
                { key: 'planning_horizon_months', label: 'Inferred Planning Horizon (Months)', type: 'number' },
                { key: 'target_exam', label: 'Target Exam / Track', type: 'text' },
                { key: 'target_attempt', label: 'Target Attempt / Intake', type: 'text' },
                { key: 'exam_goal_detail', label: 'Exam / Goal Detail', type: 'text' },
              ].map(f => (
                <div key={f.key} style={{ minWidth: 0, overflow: 'hidden' }}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                    {f.label}
                  </label>
                  {isEditing ? (
                    f.type === 'select' ? (
                      <select
                        value={profile[f.key] || ''}
                        onChange={e => handleProfileFieldChange(f.key, e.target.value)}
                        style={{
                          width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                          borderRadius: 0, color: 'var(--ink)', padding: '6px 8px', fontSize: '0.85rem', outline: 'none',
                        }}
                      >
                        <option value="">Select...</option>
                        {f.options.map(o => <option key={o} value={o}>{o.toUpperCase()}</option>)}
                      </select>
                    ) : (
                      <input
                        type={f.type}
                        value={profile[f.key] || ''}
                        onChange={e => handleProfileFieldChange(f.key, e.target.value)}
                        style={{
                          width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                          borderRadius: 0, color: 'var(--ink)', padding: '6px 8px', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box',
                        }}
                      />
                    )
                  ) : (
                    <span style={{ fontSize: '0.88rem', fontWeight: 600, overflowWrap: 'break-word', wordBreak: 'break-word', display: 'block', minWidth: 0 }}>{profile[f.key] || 'Not specified'}</span>
                  )}
                </div>
              ))}

              {/* List Fields */}
              {[{ key: 'skills', label: 'Skills Inventory (comma-separated)' },
                { key: 'career_goals', label: 'Career Goals / Aspirations (comma-separated)' },
                { key: 'target_industries', label: 'Target Industries (comma-separated)' },
                { key: 'preferred_content_types', label: 'Preferred content (comma-separated)' },
                { key: 'extracurricular_interests', label: 'Extracurricular Interests (comma-separated)' },
              ].map(f => (
                <div key={f.key} className="col-span-full" style={{ minWidth: 0, overflow: 'hidden' }}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                    {f.label}
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={Array.isArray(profile[f.key]) ? arrayToString(profile[f.key]) : profile[f.key] || ''}
                      onChange={e => handleProfileFieldChange(f.key, e.target.value)}
                      style={{
                        width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                        borderRadius: 0, color: 'var(--ink)', padding: '6px 8px', fontSize: '0.85rem', outline: 'none',
                      }}
                    />
                  ) : (
                    <span style={{ fontSize: '0.88rem', fontWeight: 600, overflowWrap: 'break-word', wordBreak: 'break-word', display: 'block', minWidth: 0 }}>
                      {Array.isArray(profile[f.key]) ? arrayToString(profile[f.key]) : profile[f.key] || 'None specified'}
                    </span>
                  )}
                </div>
              ))}

              {/* Past Experience Description */}
              <div className="col-span-full" style={{ minWidth: 0, overflow: 'hidden' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Personal Introduction / Backstory
                </label>
                {isEditing ? (
                  <textarea
                    rows={4}
                    value={profile.personal_introduction || profile.backstory || ''}
                    onChange={e => handleProfileFieldChange('personal_introduction', e.target.value)}
                    style={{
                      width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                      borderRadius: 0, color: 'var(--ink)', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'var(--ink)', lineHeight: 1.5, margin: 0, overflowWrap: 'break-word' }}>
                    {profile.personal_introduction || profile.backstory || 'No backstory captured yet.'}
                  </p>
                )}
              </div>

              <div className="col-span-full" style={{ minWidth: 0, overflow: 'hidden' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Inferred Timeline Reason
                </label>
                {isEditing ? (
                  <textarea
                    rows={3}
                    value={profile.inferred_planning_reason || ''}
                    onChange={e => handleProfileFieldChange('inferred_planning_reason', e.target.value)}
                    style={{
                      width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                      borderRadius: 0, color: 'var(--ink)', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'var(--ink)', lineHeight: 1.5, margin: 0, overflowWrap: 'break-word' }}>
                    {profile.inferred_planning_reason || 'Delta has not inferred a timeline reason yet.'}
                  </p>
                )}
              </div>

              <div className="col-span-full" style={{ minWidth: 0, overflow: 'hidden' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Work Experience / Academic Projects Summary
                </label>
                {isEditing ? (
                  <textarea
                    rows={4}
                    value={profile.past_experience || ''}
                    onChange={e => handleProfileFieldChange('past_experience', e.target.value)}
                    style={{
                      width: '100%', background: 'var(--paper)', border: '1px solid var(--rule)',
                      borderRadius: 0, color: 'var(--ink)', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'var(--ink)', lineHeight: 1.5, margin: 0, overflowWrap: 'break-word' }}>
                    {profile.past_experience || 'No experience summary compiled.'}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div className="onboarding-action-row" style={{ display: 'flex', justifyContent: 'center', gap: 16 }}>
            <button
              onClick={handleConfirmProfile}
              disabled={isEditing}
              style={{
                background: isEditing ? 'var(--rule)' : 'var(--ink)',
                color: isEditing ? 'var(--ink-soft)' : 'var(--bone)',
                border: 'none',
                padding: '12px 28px',
                borderRadius: 0,
                fontSize: '0.9rem',
                fontWeight: 700,
                cursor: isEditing ? 'not-allowed' : 'pointer',
                transition: 'opacity 0.2s',
              }}
              onMouseEnter={e => { if(!isEditing) e.currentTarget.style.opacity = '0.9' }}
              onMouseLeave={e => { if(!isEditing) e.currentTarget.style.opacity = '1' }}
            >
              {reviewMode ? 'Confirm Profile & Build Roadmap' : 'Go to Part 2 Roadmap'}
            </button>
            
            <button
              onClick={() => {
                toast('This will clear all your profile data and start over. Are you sure?', {
                  action: {
                    label: 'Yes, reset',
                    onClick: async () => {
                      try {
                        await ingestionAPI.resetProfile(userId);
                        queryClient.invalidateQueries({ queryKey: ['user', userId] });
                        queryClient.invalidateQueries({ queryKey: ['user-with-skills', userId] });
                        window.location.reload();
                      } catch (e) {
                        console.error('Reset error:', e);
                        toast.error('Failed to reset profile. Please try again.');
                      }
                    },
                  },
                  cancel: { label: 'Cancel' },
                  duration: 8000,
                });
              }}
              style={{
                background: 'var(--accent-surface)',
                color: 'var(--ink-soft)',
                border: '1px solid var(--rule)',
                padding: '12px 28px',
                borderRadius: 0,
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'var(--rule)';
                e.currentTarget.style.color = 'var(--ink)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'var(--accent-surface)';
                e.currentTarget.style.color = 'var(--ink-soft)';
              }}
            >
              Reset & Retake
            </button>
          </div>
        </div>

        {/* Responsive styles injected in this return tree */}
        <style>{`
          .onboarding-review-root {
            padding: 5rem 1rem 3rem;
            box-sizing: border-box;
            width: 100%;
          }
          .onboarding-form-card {
            padding: 14px 14px;
            box-sizing: border-box;
          }
          .onboarding-action-row {
            flex-direction: column;
            align-items: stretch;
          }
          .onboarding-action-row button {
            width: 100%;
            justify-content: center;
          }
          .onboarding-field-grid {
            min-width: 0;
          }

          @media (min-width: 480px) {
            .onboarding-review-root {
              padding: 5.5rem 1.5rem 3rem;
            }
            .onboarding-form-card {
              padding: 18px 20px;
            }
            .onboarding-action-row {
              flex-direction: row;
              align-items: center;
            }
            .onboarding-action-row button {
              width: auto;
            }
          }

          @media (min-width: 640px) {
            .onboarding-review-root {
              padding: 6rem 2rem 4rem;
            }
            .onboarding-form-card {
              padding: 24px 30px;
            }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bone)',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: "'Manrope', sans-serif",
      paddingTop: '11rem',
    }}>
      {/* Progress Bar Header */}
      <div style={{
        background: 'rgb(var(--bone-rgb) / 0.92)',
        borderBottom: '1px solid var(--rule)',
        padding: '1.25rem 2rem',
        position: 'fixed',
        top: '4rem',
        left: 0,
        right: 0,
        zIndex: 40,
        backdropFilter: 'blur(10px)',
      }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '0.66rem', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.22em', fontWeight: 500 }}>
              Profile setup
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '0.66rem', color: 'var(--oxblood)', textTransform: 'uppercase', letterSpacing: '0.14em', fontWeight: 500 }}>
              {progress}% complete
            </span>
          </div>
          {/* Progress Bar track */}
          <div style={{
            width: '100%', height: 4, background: 'var(--accent-surface)',
            border: '1px solid var(--rule)', borderRadius: 0,
            overflow: 'hidden', marginBottom: 12,
          }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: 'var(--oxblood)',
              }}
            />
          </div>
          {/* Required Fields Pills — horizontally scrollable so this row never
              wraps to extra lines and grows the fixed header's height on
              narrow screens (which would push it into the chat below). */}
          <div style={{
            display: 'flex', flexWrap: 'nowrap', gap: 6,
            overflowX: 'auto', WebkitOverflowScrolling: 'touch', paddingBottom: 2,
          }}>
            {REQUIRED_FIELDS_METADATA.map(({ key, label }) => {
              const isFilled = filledFields.includes(key);
              return (
                <div
                  key={key}
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '0.6rem',
                    fontWeight: 500,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    padding: '3px 8px',
                    borderRadius: 0,
                    border: isFilled ? '1px solid var(--oxblood)' : '1px dashed var(--rule)',
                    background: isFilled ? 'var(--paper)' : 'transparent',
                    color: isFilled ? 'var(--ink)' : 'var(--ink-soft)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{
                    width: 4, height: 4, borderRadius: 0,
                    background: isFilled ? 'var(--oxblood)' : 'var(--rule)',
                  }} />
                  {label}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Wizard body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '2rem 0 3rem' }}>
        <div style={{ maxWidth: 620, margin: '0 auto', padding: '0 1.5rem' }}>

          {/* Intro header */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ textAlign: 'center', marginBottom: 32 }}
          >
            <div style={{
              width: 52, height: 52, borderRadius: 0, background: 'var(--ink)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
            }}>
              <ClipboardList size={22} style={{ color: 'var(--bone)' }} />
            </div>
            <h1 style={{ color: 'var(--oxblood)', fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: '1.6rem', fontWeight: 600, marginBottom: 8 }}>
              Part 1: Tell us about yourself
            </h1>
            <p style={{ color: 'var(--ink-soft)', fontSize: '0.9rem', lineHeight: 1.6 }}>
              {phase === 'resume'
                ? 'Start by uploading your resume if you have one — Delta pre-fills what it recognizes. No resume? Just skip and answer a few quick questions.'
                : 'Answer one question at a time. You can go back and change any earlier answer.'}
            </p>
          </motion.div>

          {/* Resume step */}
          {phase === 'resume' && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ background: 'var(--accent-surface)', border: '1px solid var(--rule)', padding: 'clamp(20px, 5vw, 36px)', textAlign: 'center' }}
            >
              {!uploadFile ? (
                <>
                  <div
                    onClick={() => !parsing && fileRef.current?.click()}
                    style={{
                      border: '1px dashed var(--rule)', padding: '28px 20px',
                      cursor: parsing ? 'wait' : 'pointer', marginBottom: 20,
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
                    }}
                  >
                    {parsing
                      ? <Loader2 size={26} style={{ color: 'var(--ink-soft)', animation: 'spin 1s linear infinite' }} />
                      : <Paperclip size={26} style={{ color: 'var(--ink-soft)' }} />}
                    <span style={{ color: 'var(--ink)', fontSize: '0.92rem', fontWeight: 600 }}>
                      {parsing ? 'Analyzing your resume…' : 'Upload your resume'}
                    </span>
                    <span style={{ color: 'var(--ink-soft)', fontSize: '0.78rem' }}>PDF, DOCX, TXT or MD</span>
                  </div>
                  <button
                    onClick={skipResume}
                    disabled={parsing}
                    style={{
                      background: 'none', border: 'none', color: 'var(--ink-soft)',
                      fontSize: '0.85rem', cursor: parsing ? 'not-allowed' : 'pointer',
                      textDecoration: 'underline', fontWeight: 600,
                    }}
                  >
                    I don&apos;t have a resume — skip
                  </button>
                </>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <CheckCircle2 size={16} style={{ color: 'var(--ink)' }} />
                  <span style={{ color: 'var(--ink)', fontSize: '0.9rem' }}>{uploadFile.name} — analyzed</span>
                </div>
              )}
            </motion.div>
          )}

          {/* Question step */}
          {phase === 'questions' && steps[cursor] && (
            <motion.div
              key={cursor}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ background: 'var(--accent-surface)', border: '1px solid var(--rule)', padding: 'clamp(20px, 5vw, 36px)' }}
            >
              <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '0.66rem', color: 'var(--oxblood)', textTransform: 'uppercase', letterSpacing: '0.18em', fontWeight: 500 }}>
                Question {cursor + 1}
              </span>
              <p style={{ color: 'var(--ink)', fontSize: '1.05rem', lineHeight: 1.55, fontWeight: 500, margin: '12px 0 20px' }}>
                {steps[cursor].question}
              </p>
              <textarea
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleNext(); } }}
                placeholder="Type your answer…"
                autoFocus
                rows={3}
                disabled={isThinking}
                style={{
                  width: '100%', boxSizing: 'border-box', background: 'var(--bone)',
                  border: '1px solid var(--rule)', outline: 'none', color: 'var(--ink)',
                  fontSize: '0.95rem', lineHeight: 1.5, resize: 'vertical',
                  fontFamily: 'inherit', padding: '12px 14px', minHeight: 84,
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, gap: 12 }}>
                <button
                  onClick={handleBack}
                  disabled={cursor === 0 || isThinking}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: 'none', border: 'none',
                    color: cursor === 0 ? 'var(--rule)' : 'var(--ink-soft)',
                    fontSize: '0.85rem', fontWeight: 600,
                    cursor: cursor === 0 || isThinking ? 'not-allowed' : 'pointer',
                  }}
                >
                  <ChevronLeft size={15} /> Back
                </button>
                <button
                  onClick={handleNext}
                  disabled={!draft.trim() || isThinking}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    background: draft.trim() && !isThinking ? 'var(--ink)' : 'var(--rule)',
                    color: draft.trim() && !isThinking ? 'var(--bone)' : 'var(--ink-soft)',
                    border: 'none', padding: '11px 24px', fontSize: '0.9rem', fontWeight: 700,
                    cursor: draft.trim() && !isThinking ? 'pointer' : 'not-allowed',
                  }}
                >
                  {isThinking
                    ? <><Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> Saving…</>
                    : <>Next <ChevronRight size={15} /></>}
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
        textarea::placeholder { color: var(--ink-soft); }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--rule); border-radius: 0; }

        /* ── Responsive: Onboarding Review Section ── */
        .onboarding-review-root {
          padding: 6rem 1.25rem 4rem;
        }
        .onboarding-form-card {
          padding: 16px 18px;
        }
        .onboarding-action-row {
          flex-direction: column;
          align-items: stretch;
        }
        .onboarding-action-row button {
          width: 100%;
          justify-content: center;
        }
        .onboarding-field-grid {
          min-width: 0;
        }

        @media (min-width: 480px) {
          .onboarding-form-card {
            padding: 20px 24px;
          }
          .onboarding-action-row {
            flex-direction: row;
            align-items: center;
          }
          .onboarding-action-row button {
            width: auto;
          }
        }

        @media (min-width: 640px) {
          .onboarding-review-root {
            padding: 6rem 2rem 4rem;
          }
          .onboarding-form-card {
            padding: 24px 30px;
          }
        }
      `}</style>
    </div>
  );
}
