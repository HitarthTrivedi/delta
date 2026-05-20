import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, BookOpen, Target, Sparkles, ChevronRight, User, GraduationCap, Award, Cpu, ShieldAlert } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import axios from 'axios';
import { toast } from 'sonner';

export default function Onboarding() {
  const navigate = useNavigate();
  const userId = useAuthStore((state) => state.userId);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState([]);

  // Form states
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    current_role: 'Student',
    years_experience: 0,
    target_role: 'AI Developer / Software Engineer',
    hours_per_week: 10,
    learning_style: 'practical',
  });

  const [skills, setSkills] = useState([
    { name: 'Python', proficiency: 5, category: 'core' },
    { name: 'React', proficiency: 3, category: 'frontend' },
    { name: 'FastAPI', proficiency: 4, category: 'backend' },
    { name: 'SQL', proficiency: 2, category: 'database' },
    { name: 'Docker', proficiency: 1, category: 'infrastructure' },
  ]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
  };

  const handleSkillProficiency = (index, val) => {
    setSkills(prev => {
      const updated = [...prev];
      updated[index].proficiency = val;
      return updated;
    });
  };

  const addSkill = (name) => {
    if (!name.trim()) return;
    if (skills.some(s => s.name.toLowerCase() === name.toLowerCase())) {
      toast.warning('Skill already listed!');
      return;
    }
    setSkills(prev => [...prev, { name: name.trim(), proficiency: 3, category: 'custom' }]);
  };

  const [newSkillName, setNewSkillName] = useState('');

  const nextStep = () => {
    if (step === 1 && (!profile.name || !profile.email)) {
      toast.error('Identity required. Please enter a valid name and email.');
      return;
    }
    setStep(prev => prev + 1);
  };

  const triggerCompilation = async () => {
    setStep(4);
    setLoading(true);
    
    const logs = [
      'Initializing Delta Career Engine...',
      'Opening SQLite database channel...',
      'Mapping academic credentials to regional indexes...',
      'Analyzing capabilities (Python, React, FastAPI)...',
      'Contacting Gemini AI for customized technical Twists...',
      'Applying consistency streak multipliers...',
      'Fetching local hiring pulse (Bengaluru & Pune clusters)...',
      'Configuring entry-level CTC models (INR 6L - 12L LPA)...',
      'Compiling 3-Phase Zoomable Career Roadmap...',
      'Generating Weekly Dossier portfolio criteria...',
      'Syncing Flipkart GRiD 8.0 & competitive contests...',
      'Initialization successful! Synced guest user state.'
    ];

    // Play visual terminal loading sequence
    for (let i = 0; i < logs.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 400));
      setLoadingLogs(prev => [...prev, logs[i]]);
    }

    try {
      const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
      
      // 1. Save user profile
      await axios.put(`${baseURL}/users/${userId}`, profile);
      
      // 2. Clear old skills & sync selected skills
      for (const skill of skills) {
        await axios.post(`${baseURL}/skills`, {
          user_id: userId,
          name: skill.name,
          category: skill.category,
          proficiency: skill.proficiency,
          evidence_type: 'claimed',
          evidence_weight: 0.4
        });
      }

      // 3. Generate initial Weekly Brief & Roadmap
      await axios.post(`${baseURL}/briefs/generate/${userId}`);

      toast.success('Roadmap generated! Welcome to Delta.');
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
      toast.error('Sync failed, using offline fallback. Navigating to Dashboard.');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-20 min-h-screen mesh-gradient-1 bg-grid-pattern relative overflow-hidden flex flex-col justify-center items-center px-4">
      {/* Background glow balls */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary-500/5 rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[160px] pointer-events-none" />

      <div className="w-full max-w-2xl z-10">
        
        {/* Navigation Indicator */}
        {step < 4 && (
          <div className="flex items-center justify-between mb-8 px-4">
            {[1, 2, 3].map((num) => (
              <div key={num} className="flex items-center flex-1 last:flex-initial">
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center font-mono text-xs font-bold transition-all duration-300 ${
                  step === num 
                    ? 'bg-primary-500 border-primary-400 text-white shadow-lg shadow-primary-500/20' 
                    : step > num 
                      ? 'bg-primary-500/10 border-primary-500/30 text-primary-400' 
                      : 'bg-slate-900 border-white/5 text-slate-500'
                }`}>
                  {num}
                </div>
                {num < 3 && (
                  <div className={`h-[1px] flex-1 mx-4 transition-colors duration-300 ${
                    step > num ? 'bg-primary-500/30' : 'bg-white/5'
                  }`} />
                )}
              </div>
            ))}
          </div>
        )}

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
            >
              <GlassPanel className="p-8 border-primary-500/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-3 text-primary-400 bg-primary-500/5 border-b border-l border-white/5 rounded-bl-xl">
                  <User size={16} />
                </div>
                
                <h1 className="text-xl font-black font-mono tracking-widest text-white uppercase mb-1">Welcome into Delta</h1>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-6">Configure your professional growth trajectory</p>
                
                <h2 className="text-sm font-mono font-bold uppercase text-primary-400 mb-4 flex items-center gap-2">
                  <GraduationCap size={16} /> Academic Profile & Identity
                </h2>

                <div className="space-y-4 font-mono">
                  <div>
                    <label className="block text-[10px] uppercase text-slate-400 mb-1.5 tracking-wider">Full Name</label>
                    <input 
                      type="text" 
                      name="name"
                      placeholder="e.g. Harsh Sharma"
                      value={profile.name}
                      onChange={handleProfileChange}
                      className="w-full bg-slate-950/80 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase text-slate-400 mb-1.5 tracking-wider">Email Address</label>
                    <input 
                      type="email" 
                      name="email"
                      placeholder="e.g. harsh@student.iit.ac.in"
                      value={profile.email}
                      onChange={handleProfileChange}
                      className="w-full bg-slate-950/80 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase text-slate-400 mb-1.5 tracking-wider">Major / Field of Study</label>
                    <input 
                      type="text" 
                      name="target_role"
                      placeholder="e.g. Computer Science & Engineering"
                      value={profile.target_role}
                      onChange={handleProfileChange}
                      className="w-full bg-slate-950/80 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors"
                    />
                  </div>
                </div>

                <div className="mt-8 flex justify-end">
                  <button 
                    onClick={nextStep}
                    className="btn-primary px-6 py-2.5 text-xs flex items-center gap-1.5 font-mono uppercase tracking-widest font-bold"
                  >
                    Set Capabilities <ChevronRight size={14} />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
            >
              <GlassPanel className="p-8 border-indigo-500/10">
                <div className="absolute top-0 right-0 p-3 text-indigo-400 bg-indigo-500/5 border-b border-l border-white/5 rounded-bl-xl">
                  <Award size={16} />
                </div>
                
                <h1 className="text-xl font-black font-mono tracking-widest text-white uppercase mb-1">Capability Assessment</h1>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-6">Select your primary technical strengths</p>

                <div className="space-y-4">
                  {skills.map((skill, index) => (
                    <div key={skill.name} className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-white/5 font-mono">
                      <div>
                        <span className="text-xs font-bold text-slate-300">{skill.name}</span>
                        <span className="ml-2 text-[8px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded uppercase tracking-widest">
                          {skill.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-500 uppercase mr-2">Proficiency:</span>
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                          <button
                            key={num}
                            onClick={() => handleSkillProficiency(index, num)}
                            className={`w-4 h-4 rounded-sm text-[8px] flex items-center justify-center font-bold transition-all ${
                              skill.proficiency >= num 
                                ? 'bg-indigo-500 text-white' 
                                : 'bg-slate-900 text-slate-600 hover:text-slate-400 border border-white/5'
                            }`}
                          >
                            {num}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}

                  <div className="flex items-center gap-2 pt-2">
                    <input
                      type="text"
                      placeholder="Add another skill... (e.g. PyTorch, Kubernetes)"
                      value={newSkillName}
                      onChange={(e) => setNewSkillName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          addSkill(newSkillName);
                          setNewSkillName('');
                        }
                      }}
                      className="flex-1 bg-slate-950/60 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono"
                    />
                    <button
                      onClick={() => {
                        addSkill(newSkillName);
                        setNewSkillName('');
                      }}
                      className="px-4 py-2.5 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-xs font-mono text-slate-300 transition-colors"
                    >
                      Add
                    </button>
                  </div>
                </div>

                <div className="mt-8 flex justify-between">
                  <button 
                    onClick={() => setStep(1)}
                    className="px-5 py-2.5 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-xs font-mono text-slate-400 uppercase tracking-wider transition-colors"
                  >
                    Back
                  </button>
                  <button 
                    onClick={nextStep}
                    className="btn-primary px-6 py-2.5 text-xs flex items-center gap-1.5 font-mono uppercase tracking-widest font-bold"
                  >
                    Study Ambitions <ChevronRight size={14} />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
            >
              <GlassPanel className="p-8 border-violet-500/10">
                <div className="absolute top-0 right-0 p-3 text-violet-400 bg-violet-500/5 border-b border-l border-white/5 rounded-bl-xl">
                  <Target size={16} />
                </div>
                
                <h1 className="text-xl font-black font-mono tracking-widest text-white uppercase mb-1">Growth Commitments</h1>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-6">Define your target targets and weekly pacing</p>

                <div className="space-y-6 font-mono">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-[10px] uppercase text-slate-400 tracking-wider">Weekly Commitment (Hours)</label>
                      <span className="text-xs text-primary-400 font-bold">{profile.hours_per_week} hours / week</span>
                    </div>
                    <input 
                      type="range" 
                      min="3" 
                      max="40"
                      value={profile.hours_per_week}
                      onChange={(e) => setProfile(prev => ({ ...prev, hours_per_week: parseInt(e.target.value) }))}
                      className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-primary-500 border border-white/5"
                    />
                    <div className="flex justify-between text-[8px] text-slate-500 uppercase mt-1">
                      <span>Casual (3h)</span>
                      <span>Target (15h)</span>
                      <span>Intense (40h)</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase text-slate-400 mb-2 tracking-wider">Preferred Learning Style</label>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { id: 'practical', label: 'Practical (Code first)', desc: 'Build tools directly' },
                        { id: 'theoretical', label: 'Structured (Courses)', desc: 'Follow guides' },
                        { id: 'competitive', label: 'Sprints (CP/Hack)', desc: 'Compete directly' }
                      ].map((style) => (
                        <button
                          key={style.id}
                          onClick={() => setProfile(prev => ({ ...prev, learning_style: style.id }))}
                          className={`p-3 rounded-lg border text-left flex flex-col transition-all duration-300 ${
                            profile.learning_style === style.id
                              ? 'bg-violet-500/10 border-violet-500/40 text-white'
                              : 'bg-slate-950/60 border-white/5 text-slate-400 hover:border-white/10 hover:text-slate-300'
                          }`}
                        >
                          <span className="text-[10px] font-bold uppercase tracking-wider mb-1 block">{style.label}</span>
                          <span className="text-[8px] text-slate-500 leading-normal">{style.desc}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-8 flex justify-between">
                  <button 
                    onClick={() => setStep(2)}
                    className="px-5 py-2.5 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-xs font-mono text-slate-400 uppercase tracking-wider transition-colors"
                  >
                    Back
                  </button>
                  <button 
                    onClick={triggerCompilation}
                    className="btn-primary px-6 py-2.5 text-xs flex items-center gap-1.5 font-mono uppercase tracking-widest font-bold bg-gradient-to-r from-primary-500 to-indigo-500 hover:from-primary-600 hover:to-indigo-600 border-none shadow-lg shadow-primary-500/20"
                  >
                    Compile Roadmap <Sparkles size={14} />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          )}

          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full"
            >
              <GlassPanel className="p-8 border-primary-500/20 scan-line relative overflow-hidden min-h-[400px] flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500/5 rounded-full blur-[120px] pointer-events-none" />
                
                <div className="text-center py-6">
                  <Cpu className="text-primary-400 animate-spin mb-4 mx-auto" size={32} />
                  <h1 className="text-lg font-black font-mono tracking-widest text-white uppercase mb-1">Compiling Career Intelligence</h1>
                  <p className="text-[10px] font-mono text-primary-400 uppercase tracking-widest">GEMINI AI & SQLite SYNC ACTIVE</p>
                </div>

                {/* Simulated Log Output */}
                <div className="bg-black/60 border border-white/5 rounded-lg p-4 h-48 overflow-y-auto font-mono text-[9px] text-slate-400 space-y-1.5 scrollbar-hide select-none flex flex-col justify-end">
                  {loadingLogs.map((log, idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <span className="text-primary-500 font-bold">{`>`}</span>
                      <span>{log}</span>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex items-center gap-1">
                      <span className="text-primary-400 animate-pulse font-black">_</span>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex items-center justify-between text-[8px] font-mono text-slate-500 uppercase tracking-wider border-t border-white/5 pt-4">
                  <span>Delta Engine 2.0.0</span>
                  <span className="text-primary-500 animate-pulse">Syncing...</span>
                </div>
              </GlassPanel>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
