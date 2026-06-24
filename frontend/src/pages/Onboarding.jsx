import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Paperclip, Send, CheckCircle2, X,
  FileText, Loader2, User, ClipboardList, Edit3, Save, Check
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useUserWithSkills } from '../hooks/useUser';
import { useQueryClient } from '@tanstack/react-query';
import { ingestionAPI } from '../lib/api';
import { toast } from 'sonner';

/* ─── PDF / TXT parser ─── */
const parseFile = async (file) => {
  if (file.type === 'text/plain' || file.name.endsWith('.txt') || file.name.endsWith('.md')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror  = reject;
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
            const page    = await pdf.getPage(i);
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
  throw new Error('Unsupported file type. Use .pdf, .txt, or .md');
};

/* ─── Typing indicator ─── */
const TypingDots = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0' }}>
    {[0, 1, 2].map(i => (
      <motion.span
        key={i}
        animate={{ opacity: [0.3, 1, 0.3] }}
        transition={{ repeat: Infinity, duration: 1.2, delay: i * 0.2 }}
        style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(255,255,255,0.5)', display: 'block' }}
      />
    ))}
  </div>
);

/* ─── Chat Bubble ─── */
const Bubble = ({ msg }) => {
  const isAssistant = msg.role === 'assistant';
  const isFile = msg.role === 'file';

  if (isFile) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}
      >
        <div style={{
          background: 'rgba(255,255,255,0.07)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: '16px 16px 4px 16px',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          maxWidth: '70%',
        }}>
          <FileText size={14} style={{ color: 'rgba(255,255,255,0.5)', flexShrink: 0 }} />
          <div>
            <p style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 500, margin: 0 }}>{msg.filename}</p>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', margin: 0 }}>Resume uploaded</p>
          </div>
          <CheckCircle2 size={14} style={{ color: 'rgba(255,255,255,0.72)', flexShrink: 0 }} />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        display: 'flex',
        justifyContent: isAssistant ? 'flex-start' : 'flex-end',
        marginBottom: 14,
        gap: 10,
      }}
    >
      {isAssistant && (
        <div style={{
          width: 30, height: 30, borderRadius: '50%',
          background: '#fff', flexShrink: 0, marginTop: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <ClipboardList size={14} style={{ color: '#000' }} />
        </div>
      )}

      <div style={{
        maxWidth: '72%',
        background: isAssistant ? 'rgba(255,255,255,0.05)' : '#fff',
        border: isAssistant ? '1px solid rgba(255,255,255,0.1)' : 'none',
        borderRadius: isAssistant ? '4px 16px 16px 16px' : '16px 16px 4px 16px',
        padding: '12px 16px',
        color: isAssistant ? 'rgba(255,255,255,0.88)' : '#000',
        fontSize: '0.9rem',
        lineHeight: 1.6,
      }}>
        {msg.content}
      </div>

      {!isAssistant && (
        <div style={{
          width: 30, height: 30, borderRadius: '50%',
          background: 'rgba(255,255,255,0.12)', flexShrink: 0, marginTop: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <User size={14} style={{ color: '#fff' }} />
        </div>
      )}
    </motion.div>
  );
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

  const [messages,   setMessages]   = useState([]);
  const [input,      setInput]      = useState('');
  const [sessionId,  setSessionId]  = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isDone,     setIsDone]     = useState(false);
  const [reviewMode, setReviewMode] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [parsing,    setParsing]    = useState(false);

  const [progress, setProgress] = useState(0);
  const [filledFields, setFilledFields] = useState([]);
  const [profile, setProfile] = useState({});
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const bottomRef   = useRef(null);
  const fileRef     = useRef(null);
  const inputRef    = useRef(null);

  /* auto-scroll */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

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
        
        if (res.conversation && res.conversation.length > 0) {
          setMessages(res.conversation);
        } else {
          const firstMsg = res.initial_question || res.message || "Hi, I am Delta's intake advisor. You can do this fully by conversation, even if you do not have a resume. Tell me who you are, your current stage, what you want to improve toward, and how much time you realistically have each week.";
          setMessages([{ role: 'assistant', content: firstMsg }]);
        }
      } catch (e) {
        console.error(e);
        setMessages([{
          role: 'assistant',
          content: "Hi, I am Delta's intake advisor. You can do this fully by conversation, even if you do not have a resume. Tell me who you are, your current stage, what you want to improve toward, and how much time you realistically have each week.",
        }]);
      } finally {
        setIsThinking(false);
      }
    })();
  }, [userId, loadProfileData]);

  /* send message */
  const handleSend = useCallback(async (overrideText = null) => {
    const text = (overrideText ?? input).trim();
    if (!text || isThinking) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsThinking(true);

    try {
      const res = await ingestionAPI.submitAnswer(userId, sessionId, text);

      const aiReply = res.next_question || res.message || res.response || '';
      if (aiReply) {
        setMessages(prev => [...prev, { role: 'assistant', content: aiReply }]);
      }

      if (res.confidence_score !== undefined) {
        setProgress(Math.round(res.confidence_score * 100));
      }
      if (res.filled_fields) {
        setFilledFields(res.filled_fields);
      }

      if (res.review_required || res.status === 'review_required') {
        setIsDone(true);
        setReviewMode(true);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "Your profile draft is ready. Please review and edit anything before Delta creates your roadmap.",
        }]);
        await loadProfileData();
        queryClient.invalidateQueries({ queryKey: ['user', userId] });
      } else if (res.completed || res.status === 'complete' || res.status === 'completed') {
        setIsDone(true);
        setReviewMode(false);
        await loadProfileData();
      }
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Got it. Could you tell me a bit more about your background and goals?",
      }]);
    } finally {
      setIsThinking(false);
    }
  }, [input, sessionId, userId, isThinking, queryClient, loadProfileData]);

  /* file upload — uses dedicated resume extraction endpoint */
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    setParsing(true);
    try {
      const text = await parseFile(file);
      setUploadFile({ name: file.name, text });
      toast.success('Resume parsed — extracting your profile...');

      // Show file bubble
      setMessages(prev => [...prev, { role: 'file', filename: file.name }]);
      setIsThinking(true);

      // Use the dedicated /ingestion/resume endpoint for proper AI extraction
      const res = await ingestionAPI.ingestResume(userId, sessionId, text);

      if (res.success) {
        const extracted = res.extracted_fields || [];
        const confirmMsg = extracted.length > 0
          ? `Resume analyzed. I extracted: ${extracted.slice(0, 5).join(', ')}${extracted.length > 5 ? ' and more' : ''}.`
          : 'Resume received.';
        setMessages(prev => [...prev, { role: 'assistant', content: confirmMsg }]);

        const followUp = res.follow_up || res.message;
        if (followUp && followUp !== confirmMsg) {
          setMessages(prev => [...prev, { role: 'assistant', content: followUp }]);
        }

        if (res.confidence_score !== undefined) {
          setProgress(Math.round(res.confidence_score * 100));
        }
        if (res.filled_fields) {
          setFilledFields(res.filled_fields);
        }
        if (res.review_required || res.status === 'review_required') {
          setIsDone(true);
          setReviewMode(true);
          await loadProfileData();
          queryClient.invalidateQueries({ queryKey: ['user', userId] });
        }
      } else {
        toast.error(res.message || 'Could not extract resume data.');
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "I had trouble reading that resume. Could you paste your key details as text instead?",
        }]);
      }
    } catch (err) {
      toast.error(err.message || 'Failed to parse file.');
    } finally {
      setParsing(false);
      setIsThinking(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
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
        background: '#000',
        color: '#fff',
        fontFamily: "'Inter', sans-serif",
        padding: '6rem 2rem 4rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <div style={{ maxWidth: 880, width: '100%' }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 35 }}>
            <div style={{
              width: 54, height: 54, borderRadius: '50%', background: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
            }}>
              <CheckCircle2 size={26} style={{ color: '#000' }} />
            </div>
            <h1 style={{ fontSize: '1.8rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 8 }}>
              {reviewMode ? 'Review Your Delta Profile' : 'Onboarding Profile Sync'}
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.9rem', lineHeight: 1.6, maxWidth: 500, margin: '0 auto' }}>
              {reviewMode
                ? 'Check the details Delta collected. Edit anything that feels wrong or incomplete before the roadmap is created.'
                : 'Your details are gathered. You can modify any parsed fields below to fine-tune your profile.'}
            </p>
          </div>

          {/* Form / Snapshot Container */}
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 14,
            padding: '24px 30px',
            marginBottom: 30,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 10 }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>
                {isEditing ? 'Modify Intake Details' : 'Active Profile Snapshot'}
              </h2>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  style={{
                    background: 'none', border: 'none', color: '#fff', cursor: 'pointer',
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
                      background: '#fff', border: 'none', color: '#000', cursor: 'pointer',
                      fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700,
                      padding: '4px 12px', borderRadius: 4,
                    }}
                  >
                    {saving ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={12} />}
                    Save Changes
                  </button>
                  <button
                    onClick={() => { setIsEditing(false); loadProfileData(); }}
                    style={{
                      background: 'none', border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.6)',
                      cursor: 'pointer', fontSize: '0.8rem', padding: '4px 12px', borderRadius: 4,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            {/* Profile Fields Editor Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: 20,
            }}>
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
                <div key={f.key}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                    {f.label}
                  </label>
                  {isEditing ? (
                    f.type === 'select' ? (
                      <select
                        value={profile[f.key] || ''}
                        onChange={e => handleProfileFieldChange(f.key, e.target.value)}
                        style={{
                          width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                          borderRadius: 6, color: '#fff', padding: '6px 8px', fontSize: '0.85rem', outline: 'none',
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
                          width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                          borderRadius: 6, color: '#fff', padding: '6px 8px', fontSize: '0.85rem', outline: 'none',
                        }}
                      />
                    )
                  ) : (
                    <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>{profile[f.key] || 'Not specified'}</span>
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
                <div key={f.key} style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                    {f.label}
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={Array.isArray(profile[f.key]) ? arrayToString(profile[f.key]) : profile[f.key] || ''}
                      onChange={e => handleProfileFieldChange(f.key, e.target.value)}
                      style={{
                        width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: 6, color: '#fff', padding: '6px 8px', fontSize: '0.85rem', outline: 'none',
                      }}
                    />
                  ) : (
                    <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>
                      {Array.isArray(profile[f.key]) ? arrayToString(profile[f.key]) : profile[f.key] || 'None specified'}
                    </span>
                  )}
                </div>
              ))}

              {/* Past Experience Description */}
              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Personal Introduction / Backstory
                </label>
                {isEditing ? (
                  <textarea
                    rows={4}
                    value={profile.personal_introduction || profile.backstory || ''}
                    onChange={e => handleProfileFieldChange('personal_introduction', e.target.value)}
                    style={{
                      width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: 6, color: '#fff', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'rgba(255,255,255,0.85)', lineHeight: 1.5, margin: 0 }}>
                    {profile.personal_introduction || profile.backstory || 'No backstory captured yet.'}
                  </p>
                )}
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Inferred Timeline Reason
                </label>
                {isEditing ? (
                  <textarea
                    rows={3}
                    value={profile.inferred_planning_reason || ''}
                    onChange={e => handleProfileFieldChange('inferred_planning_reason', e.target.value)}
                    style={{
                      width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: 6, color: '#fff', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'rgba(255,255,255,0.85)', lineHeight: 1.5, margin: 0 }}>
                    {profile.inferred_planning_reason || 'Delta has not inferred a timeline reason yet.'}
                  </p>
                )}
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                  Work Experience / Academic Projects Summary
                </label>
                {isEditing ? (
                  <textarea
                    rows={4}
                    value={profile.past_experience || ''}
                    onChange={e => handleProfileFieldChange('past_experience', e.target.value)}
                    style={{
                      width: '100%', background: '#0c0c0c', border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: 6, color: '#fff', padding: '8px 10px', fontSize: '0.85rem', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'rgba(255,255,255,0.85)', lineHeight: 1.5, margin: 0 }}>
                    {profile.past_experience || 'No experience summary compiled.'}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16 }}>
            <button
              onClick={handleConfirmProfile}
              disabled={isEditing}
              style={{
                background: isEditing ? 'rgba(255,255,255,0.2)' : '#fff',
                color: isEditing ? 'rgba(255,255,255,0.4)' : '#000',
                border: 'none',
                padding: '12px 28px',
                borderRadius: 8,
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
              onClick={async () => {
                if (window.confirm("Are you sure you want to reset your intake profile and start over? All collected data will be cleared.")) {
                  try {
                    await ingestionAPI.resetProfile(userId);
                    queryClient.invalidateQueries({ queryKey: ['user', userId] });
                    queryClient.invalidateQueries({ queryKey: ['user-with-skills', userId] });
                    window.location.reload();
                  } catch (e) {
                    console.error('Reset error:', e);
                    toast.error("Failed to reset profile. Please try again.");
                  }
                }
              }}
              style={{
                background: 'rgba(255,255,255,0.05)',
                color: 'rgba(255,255,255,0.6)',
                border: '1px solid rgba(255,255,255,0.1)',
                padding: '12px 28px',
                borderRadius: 8,
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
                e.currentTarget.style.color = '#fff';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                e.currentTarget.style.color = 'rgba(255,255,255,0.6)';
              }}
            >
              Reset & Retake
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: "'Inter', sans-serif",
      paddingTop: '11rem',
    }}>
      {/* Progress Bar Header */}
      <div style={{
        background: 'rgba(0,0,0,0.85)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
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
            <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
              PROFILE INGESTION SOCKET
            </span>
            <span style={{ fontSize: '0.72rem', color: '#fff', fontFamily: 'monospace', fontWeight: 700 }}>
              {progress}% COMPILING
            </span>
          </div>
          {/* Progress Bar track */}
          <div style={{
            width: '100%', height: 6, background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.08)', borderRadius: 3,
            overflow: 'hidden', marginBottom: 12,
          }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: 'linear-gradient(90deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.9) 100%)',
                boxShadow: '0 0 8px rgba(255,255,255,0.4)',
              }}
            />
          </div>
          {/* Required Fields Pills */}
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 6,
          }}>
            {REQUIRED_FIELDS_METADATA.map(({ key, label }) => {
              const isFilled = filledFields.includes(key);
              return (
                <div
                  key={key}
                  style={{
                    fontSize: '0.62rem',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: 4,
                    border: isFilled ? '1px solid rgba(255,255,255,0.2)' : '1px dashed rgba(255,255,255,0.08)',
                    background: isFilled ? 'rgba(255,255,255,0.06)' : 'transparent',
                    color: isFilled ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.22)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{
                    width: 4, height: 4, borderRadius: '50%',
                    background: isFilled ? '#fff' : 'rgba(255,255,255,0.2)',
                  }} />
                  {label}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 0 2rem' }}>
        <div style={{ maxWidth: 680, margin: '0 auto', padding: '0 1.5rem' }}>

          {/* Intro header */}
          {messages.length <= 1 && !isThinking && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ textAlign: 'center', marginBottom: 40 }}
            >
              <div style={{
                width: 52, height: 52, borderRadius: '50%', background: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <ClipboardList size={22} style={{ color: '#000' }} />
              </div>
              <h1 style={{ color: '#fff', fontSize: '1.4rem', fontWeight: 700, marginBottom: 8 }}>
                Part 1: Ingesting Ingestion Protocol
              </h1>
              <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                Upload your resume first if you have one. I will extract what I can,
                then ask only the missing questions Agent 2 needs for the roadmap.
              </p>
            </motion.div>
          )}

          {/* Messages */}
          <AnimatePresence>
            {messages.map((msg, i) => (
              <Bubble key={i} msg={msg} />
            ))}
          </AnimatePresence>

          {/* Thinking indicator */}
          {isThinking && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: 'flex', gap: 10, marginBottom: 14 }}
            >
              <div style={{
                width: 30, height: 30, borderRadius: '50%', background: '#fff',
                flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <ClipboardList size={14} style={{ color: '#000' }} />
              </div>
              <div style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px 16px 16px 16px',
                padding: '12px 18px',
              }}>
                <TypingDots />
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input Area */}
      {!isDone && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.07)',
          padding: '1rem 1.5rem',
          background: '#000',
        }}>
          <div style={{ maxWidth: 680, margin: '0 auto' }}>

            {/* Resume upload hint */}
            {!uploadFile && messages.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 10,
                  padding: '8px 14px',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 10,
                  cursor: 'pointer',
                }}
                onClick={() => fileRef.current?.click()}
              >
                <Paperclip size={13} style={{ color: 'rgba(255,255,255,0.4)' }} />
                <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem' }}>
                  {parsing ? 'Parsing resume...' : 'Attach your resume (PDF or TXT) — skip if you don\'t have one'}
                </span>
                {parsing && <Loader2 size={13} style={{ color: 'rgba(255,255,255,0.4)', animation: 'spin 1s linear infinite' }} />}
              </motion.div>
            )}

            {/* Uploaded file badge */}
            {uploadFile && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                marginBottom: 10, padding: '6px 12px',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.14)',
                borderRadius: 8,
              }}>
                <CheckCircle2 size={13} style={{ color: 'rgba(255,255,255,0.72)' }} />
                <span style={{ color: 'rgba(255,255,255,0.72)', fontSize: '0.8rem', flex: 1 }}>{uploadFile.name} — uploaded</span>
                <button onClick={() => setUploadFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.3)', padding: 0 }}>
                  <X size={13} />
                </button>
              </div>
            )}

            {/* Text input row */}
            <div style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 10,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 14,
              padding: '10px 12px',
            }}>
              <button
                onClick={() => fileRef.current?.click()}
                disabled={parsing}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'rgba(255,255,255,0.35)', padding: '4px', flexShrink: 0,
                  transition: 'color 0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'rgba(255,255,255,0.7)'}
                onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.35)'}
                title="Attach resume"
              >
                <Paperclip size={18} />
              </button>

              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your answer..."
                rows={1}
                disabled={isThinking}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#fff',
                  fontSize: '0.92rem',
                  lineHeight: 1.5,
                  resize: 'none',
                  fontFamily: 'inherit',
                  maxHeight: 140,
                  overflowY: 'auto',
                  padding: '2px 0',
                  placeholderColor: 'rgba(255,255,255,0.3)',
                }}
                onInput={e => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
                }}
              />

              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isThinking}
                style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: input.trim() && !isThinking ? '#fff' : 'rgba(255,255,255,0.1)',
                  border: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: input.trim() && !isThinking ? 'pointer' : 'not-allowed',
                  flexShrink: 0,
                  transition: 'background 0.2s',
                }}
              >
                {isThinking
                  ? <Loader2 size={16} style={{ color: 'rgba(255,255,255,0.4)', animation: 'spin 1s linear infinite' }} />
                  : <Send size={14} style={{ color: input.trim() ? '#000' : 'rgba(255,255,255,0.3)' }} />
                }
              </button>
            </div>

            <p style={{
              textAlign: 'center',
              color: 'rgba(255,255,255,0.2)',
              fontSize: '0.72rem',
              marginTop: 10,
            }}>
              Press Enter to send · Shift+Enter for new line · Your data is stored securely
            </p>
          </div>
        </div>
      )}

      {/* Complete state */}
      {isDone && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '1.5rem',
            textAlign: 'center',
            borderTop: '1px solid rgba(255,255,255,0.07)',
            background: '#000',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', background: '#fff',
              animation: 'ping 1s cubic-bezier(0,0,0.2,1) infinite',
            }} />
            <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: '0.88rem', fontWeight: 600 }}>
              Opening Agent 2 weekly plan...
            </span>
          </div>
        </motion.div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.txt,.md"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
        textarea::placeholder { color: rgba(255,255,255,0.3); }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
      `}</style>
    </div>
  );
}
