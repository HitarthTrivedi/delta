import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Zap, BookOpen, Target, Sparkles, ChevronRight, User, 
  GraduationCap, Award, Cpu, ShieldAlert, Terminal, 
  CheckCircle2, Database, Network, Hourglass, Volume2, VolumeX, 
  HelpCircle, AlertTriangle, Flame, AlertCircle, Compass, FileText
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import axios from 'axios';
import { toast } from 'sonner';
import { careerOSAPI, ingestionAPI, briefsAPI } from '../lib/api';

// Utility to dynamically load PDF.js and extract text from PDF, MD, or TXT files
const parseFile = async (file) => {
  if (file.type === "text/plain" || file.name.endsWith(".txt") || file.name.endsWith(".md")) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(e);
      reader.readAsText(file);
    });
  } else if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const typedarray = new Uint8Array(e.target.result);
          
          // Load PDF.js dynamically from unpkg/cdnjs if not present
          if (!window.pdfjsLib) {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js';
            document.head.appendChild(script);
            
            await new Promise((res) => {
              script.onload = () => {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
                res();
              };
            });
          }
          
          const pdf = await window.pdfjsLib.getDocument(typedarray).promise;
          let text = '';
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const content = await page.getTextContent();
            text += content.items.map(item => item.str).join(' ') + '\n';
          }
          resolve(text);
        } catch (err) {
          reject(new Error("Failed to parse PDF file. Ensure it is a valid text-based PDF and not password protected."));
        }
      };
      reader.onerror = (e) => reject(e);
      reader.readAsArrayBuffer(file);
    });
  } else {
    throw new Error("Unsupported file type. Please upload a .txt, .md, or .pdf file.");
  }
};

export default function Onboarding() {
  const navigate = useNavigate();
  const userId = useAuthStore((state) => state.userId);
  const [step, setStep] = useState(1);
  
  // File Uploader & Parser States
  const [fileParsing, setFileParsing] = useState(false);
  const fileInputRef = useRef(null);

  // Direct Step 1 Direct Resume Ingest States
  const [step1FileParsing, setStep1FileParsing] = useState(false);
  const step1FileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileParsing(true);
    toast.info(`Parsing ${file.name}... Please wait.`);
    try {
      const text = await parseFile(file);
      setRawProfileImportText(text);
      toast.success(`Successfully parsed ${file.name}! Review the extracted content in the editor below.`);
    } catch (err) {
      toast.error(err.message || "Failed to parse file.");
    } finally {
      setFileParsing(false);
    }
  };

  const handleStep1FileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setStep1FileParsing(true);
    toast.info(`Reading and extracting ${file.name}...`);
    try {
      const text = await parseFile(file);
      setRawAmbition(text);
      toast.success(`Successfully loaded ${file.name}! Your background and ambitions have been extracted into the vision field below.`);
    } catch (err) {
      toast.error(err.message || "Failed to extract text from file.");
    } finally {
      setStep1FileParsing(false);
    }
  };

  
  // App states
  const [loading, setLoading] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [domainPacks, setDomainPacks] = useState([]);
  const logContainerRef = useRef(null);

  // Conversational Graph-RAG ingestion states
  const [sessionId, setSessionId] = useState(null);
  const [rawAmbition, setRawAmbition] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  
  // Real-time Cognitive Ingestion State metrics
  const [confidenceScore, setConfidenceScore] = useState(0.05);
  const [activeTensions, setActiveTensions] = useState([]);
  const [activePitfalls, setActivePitfalls] = useState([]);
  const [missingGaps, setMissingGaps] = useState([]);
  const [graphSummary, setGraphSummary] = useState({ nodes_count: 1, edges_count: 0, skills: [], ambitions: [] });

  // Personal Data Bridge State
  const [bridgeLoading, setBridgeLoading] = useState(false);
  const [rawProfileImportText, setRawProfileImportText] = useState('');
  const [showBridgeModal, setShowBridgeModal] = useState(false);

  // Profile data state
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    current_role: 'Student',
    target_role: 'AI Developer / Software Engineer',
    hours_per_week: 15,
    learning_style: 'practical',
  });

  const [skills, setSkills] = useState([]);
  const [newSkillName, setNewSkillName] = useState('');

  useEffect(() => {
    // Load pre-configured domain packs
    careerOSAPI.getDomainPacks()
      .then(setDomainPacks)
      .catch(() => {
        setDomainPacks([
          { id: 'cs_ai', label: 'CS / AI Engineering', target_roles: ['AI Developer / Software Engineer'], skill_taxonomy: ['LLMs', 'Docker', 'APIs', 'Agents'] },
          { id: 'data', label: 'Data / Analytics', target_roles: ['Data Scientist'], skill_taxonomy: ['SQL', 'ML', 'Dashboards'] },
          { id: 'finance', label: 'Quant Development', target_roles: ['Quant Developer'], skill_taxonomy: ['C++', 'Math', 'Low Latency'] }
        ]);
      });
  }, []);

  // Audio helper using Web Audio API
  const playBeep = (freq = 900, duration = 0.04, volume = 0.015) => {
    if (!soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(volume, audioCtx.currentTime);
      
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + duration);
    } catch (e) {
      // AudioContext is blocked or not supported
    }
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
  };

  const handleSkillProficiency = (index, val) => {
    playBeep(600 + val * 40, 0.05, 0.02);
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
    playBeep(800, 0.08, 0.02);
    setSkills(prev => [...prev, { name: name.trim(), proficiency: 3, category: 'custom' }]);
  };

  // Personal Data Bridge Trigger
  const handleProfileBridgeImport = async () => {
    if (!rawProfileImportText.trim()) {
      toast.error("Please paste your resume or LinkedIn profile data first.");
      return;
    }
    setBridgeLoading(true);
    playBeep(440, 0.1, 0.03);
    try {
      const result = await ingestionAPI.bridge(userId, rawProfileImportText, "linkedin");
      if (result.success) {
        toast.success(`Bridge Success! Discovered & imported ${result.nodes_imported} nodes into your Digital Twin.`);
        // Seed skills array from bridge output
        if (result.imported_nodes_labels) {
          const importedSkills = result.imported_nodes_labels.map(label => ({
            name: label,
            proficiency: 4,
            category: 'imported'
          }));
          setSkills(prev => [...prev, ...importedSkills]);
        }
        
        // Sync stats
        setConfidenceScore(result.confidence_score);
        setMissingGaps(result.gaps_remaining || []);
        
        setShowBridgeModal(false);
        setRawProfileImportText('');
        playBeep(1200, 0.25, 0.03);
      } else {
        toast.error("Profile import was unable to extract clear skills. Please enter them manually.");
      }
    } catch (e) {
      toast.error("Ingestion bridge experienced a connection issue.");
    } finally {
      setBridgeLoading(false);
    }
  };

  // Step 1 -> Step 2 Handshake: Starts the interactive Graph-RAG onboarding session
  const startAdaptiveIntake = async () => {
    if (!profile.name || !profile.email) {
      toast.error('Identity required. Please enter a valid name and email.');
      return;
    }
    if (!rawAmbition.trim()) {
      toast.error('Tell Delta what you want, even if it is messy and incomplete.');
      return;
    }

    setAiLoading(true);
    playBeep(440, 0.15, 0.03);
    try {
      // Map domain pack target journey type
      let journeyType = "general";
      if (profile.target_role.toLowerCase().includes("software") || profile.target_role.toLowerCase().includes("backend") || profile.target_role.toLowerCase().includes("frontend")) {
        journeyType = "software_engineering";
      } else if (profile.target_role.toLowerCase().includes("data") || profile.target_role.toLowerCase().includes("ml") || profile.target_role.toLowerCase().includes("ai")) {
        journeyType = "data_ai";
      } else if (profile.target_role.toLowerCase().includes("quant") || profile.target_role.toLowerCase().includes("c++")) {
        journeyType = "quant_development";
      } else if (profile.target_role.toLowerCase().includes("product")) {
        journeyType = "product_management";
      } else if (profile.target_role.toLowerCase().includes("founder") || profile.target_role.toLowerCase().includes("startup")) {
        journeyType = "entrepreneurship";
      }

      // Sync user name / email on backend
      const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
      await axios.put(`${baseURL}/users/${userId}`, profile);

      const sessionData = await ingestionAPI.start(userId, journeyType);
      setSessionId(sessionData.session_id);
      setConfidenceScore(sessionData.confidence_score);

      // Load initial chat
      const log = sessionData.conversation;
      let parsedLog = [];
      try {
        parsedLog = JSON.parse(log[0]);
      } catch (parseErr) {
        parsedLog = [{ role: 'assistant', content: sessionData.conversation[0] || "Ingestion session started. What are your primary ambitions?" }];
      }

      const initialChat = parsedLog.map(item => ({
        role: item.role,
        content: item.content,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        dimension: item.dimension
      }));

      setChatHistory(initialChat);
      setStep(2);
      
      // Load real-time state stats
      await syncRealTimeIngestionState();
      
      toast.success('Cognitive graph connection established. Real-time Intake Cockpit active.');
    } catch (err) {
      console.error(err);
      toast.error('AI intake handshake failed. Continuing with manual profile.');
      setStep(3);
    } finally {
      setAiLoading(false);
    }
  };

  const syncRealTimeIngestionState = async () => {
    try {
      const state = await ingestionAPI.getState(userId);
      setConfidenceScore(state.session?.confidence_score || 0.05);
      setActiveTensions(state.active_tensions || []);
      setGraphSummary(state.graph_summary || { nodes_count: 1, edges_count: 0, skills: [], ambitions: [] });
    } catch (err) {
      console.error("Failed to sync graph metrics: ", err);
    }
  };

  // Submits the active answer in the interactive Graph-RAG loop
  const submitChatAnswer = async () => {
    if (!currentAnswer.trim()) {
      toast.error('Please input your reply to Delta.');
      return;
    }

    setAiLoading(true);
    playBeep(700, 0.06, 0.02);

    // Push user reply to local history immediately for responsiveness
    const newUserMsg = {
      role: 'user',
      content: currentAnswer,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setChatHistory(prev => [...prev, newUserMsg]);
    const originalAnswer = currentAnswer;
    setCurrentAnswer('');

    try {
      const response = await ingestionAPI.submitAnswer(userId, sessionId, originalAnswer);
      
      // Update real-time state metrics
      setConfidenceScore(response.confidence_score);
      setActivePitfalls(response.active_pitfalls || []);
      setActiveTensions(response.tensions || []);
      setMissingGaps(response.gaps || []);
      
      // Append assistant's custom recursive question / reply
      const assistantMsg = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      
      setChatHistory(prev => [...prev, assistantMsg]);
      playBeep(900, 0.05, 0.015);

      // Fetch latest graph nodes sync
      await syncRealTimeIngestionState();

      if (response.status === 'completed') {
        toast.success("Graph ingestion complete! Digital Twin calibrated.");
        
        // Populate standard skills state with extracted capabilities
        if (response.conversation) {
          // Sync skills
          try {
            const state = await ingestionAPI.getState(userId);
            if (state.graph_summary?.skills) {
              setSkills(state.graph_summary.skills.map(s => ({
                name: s,
                proficiency: 4,
                category: 'extracted'
              })));
            }
          } catch(e) {}
        }
        
        setTimeout(() => {
          playBeep(1200, 0.2, 0.03);
          setStep(3);
        }, 3000);
      }
    } catch (err) {
      console.error(err);
      toast.error('Connection timed out. Please try sending your reply again.');
    } finally {
      setAiLoading(false);
    }
  };

  // Force Complete Onboarding
  const handleForceComplete = async () => {
    try {
      setAiLoading(true);
      const res = await ingestionAPI.forceComplete(userId);
      toast.success("Forced onboarding profile compile. Calibrating memory graph...");
      
      // Fetch skills
      const state = await ingestionAPI.getState(userId);
      if (state.graph_summary?.skills) {
        setSkills(state.graph_summary.skills.map(s => ({
          name: s,
          proficiency: 4,
          category: 'extracted'
        })));
      }
      
      setStep(3);
    } catch (e) {
      toast.error("Failed to complete onboarding session.");
    } finally {
      setAiLoading(false);
    }
  };

  // Compile final intake to seed SQLite models and play compiling animation
  const compileCareerOS = async () => {
    setStep(4);
    setLoading(true);

    // Visual console logs sequence showing Graph-Vector memory architecture seeding
    const logSequence = [
      { text: 'DELTA OPERATING SYSTEM [Version 3.5.0-RELEASE]', delay: 200, freq: 800 },
      { text: '(c) 2026 Delta Intelligence Inc. All rights reserved.', delay: 200, freq: 800 },
      { text: '---------------------------------------------------------', delay: 100, freq: 0 },
      { text: '[info] Booting Graph-Vector Semantic Memory Database... OK', delay: 400, freq: 600 },
      { text: '[info] Synchronizing SQLite tables for networkx storage...', delay: 300, freq: 600 },
      { text: '[sql]  SELECT * FROM semantic_nodes WHERE user_id = ?;', delay: 150, freq: 500 },
      { text: `       -> Discovered ${graphSummary.nodes_count} vertices and ${graphSummary.edges_count} directed edges.`, delay: 100, freq: 500 },
      { text: '[embedding] Invoking sentence-transformers model (all-MiniLM-L6-v2)...', delay: 250, freq: 600 },
      { text: '            Generating semantic vectors for new nodes... SUCCESS (0.104s)', delay: 100, freq: 1100 },
      { text: '[critic] Checking active Tension Nodes...', delay: 150, freq: 500 },
      { text: `         Active Tensions: ${activeTensions.length} nodes registered in SQLite.`, delay: 200, freq: 1100 },
      { text: '[behavior] Running Pitfall Scanners on final frame...', delay: 150, freq: 500 },
      { text: `           Active Trap signals: ${activePitfalls.map(p => p.pitfall_type).join(', ') || 'None (Healthy trajectory)'}`, delay: 100, freq: 500 },
      { text: '[golden-path] Resolving 1% benchmark targets for journey year 1...', delay: 200, freq: 1100 },
      { text: `              Target state aligned with Elite Competitor Framework.`, delay: 100, freq: 400 },
      { text: `[snapshot] Compiling flat CareerMemoryProfile snapshot payload:`, delay: 300, freq: 700 },
      { text: `           - Target role: [${profile.target_role}]`, delay: 100, freq: 400 },
      { text: `           - Extracted skills: [${skills.map(s => s.name).join(', ')}]`, delay: 100, freq: 400 },
      { text: `           - Constraints: [${profile.hours_per_week} hours/week]`, delay: 100, freq: 400 },
      { text: `[database] Seeding legacy SkillNodes in delta.db... SUCCESS`, delay: 200, freq: 1000 },
      { text: `[engine] Running Central OS 3-Phase Roadmap compiler...`, delay: 500, freq: 900 },
      { text: `         Phase 1: Foundations | Phase 2: Core | Phase 3: Applied Production`, delay: 150, freq: 400 },
      { text: `[database] INSERT INTO roadmap_states VALUES (roadmap_id: ${userId}) -> SUCCESS`, delay: 300, freq: 1200 },
      { text: `[journey] Logging JourneyEvent 'onboarding_completed'... SUCCESS`, delay: 200, freq: 1000 },
      { text: `---------------------------------------------------------`, delay: 100, freq: 0 },
      { text: `[system] Career OS initialized. Booting graphical user interface...`, delay: 300, freq: 1500 }
    ];

    // Play logs visually with beeps
    for (const log of logSequence) {
      await new Promise(resolve => setTimeout(resolve, log.delay));
      setLoadingLogs(prev => [...prev, log.text]);
      if (log.freq > 0) {
        playBeep(log.freq, 0.04, 0.012);
      }
      if (logContainerRef.current) {
        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
      }
    }

    try {
      const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
      
      // 1. Sync User Profile
      await axios.put(`${baseURL}/users/${userId}`, profile);
      
      // 2. Sync SkillNodes
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

      // 3. Seeding Weekly Brief / Roadmap State
      await axios.post(`${baseURL}/briefs/generate/${userId}`);

      // 4. Seeding Weekly Brief Core cycle snapshot
      await careerOSAPI.initialize(userId, {
        source: 'graph_vector_conversational_cockpit',
        structured: {
          ambitions: profile.target_role,
          target_domain: selectedDomainPack?.id,
          domain_label: selectedDomainPack?.label,
          domain_pack: selectedDomainPack,
          current_level: profile.current_role,
          hours_per_week: profile.hours_per_week,
          learning_style: profile.learning_style,
          extracted_skills: skills.map(skill => skill.name),
          gaps_identified: skills.filter(skill => skill.proficiency <= 3).map(skill => skill.name),
          constraints: [`${profile.hours_per_week} hours per week available`],
          content_preferences: [profile.learning_style],
        },
      });

      toast.success('Cognitive Career OS Synced successfully!');
      setTimeout(() => {
        navigate('/dashboard');
      }, 500);

    } catch (err) {
      console.error(err);
      toast.error('Local SQLite Sync encountered an issue. Using offline recovery mode.');
      setTimeout(() => navigate('/dashboard'), 1500);
    } finally {
      setLoading(false);
    }
  };

  const visibleDomainPacks = domainPacks.slice(0, 8);
  const selectedDomainPack = visibleDomainPacks.find(pack =>
    (pack.target_roles || []).includes(profile.target_role)
  ) || visibleDomainPacks[0];

  return (
    <div className="pt-20 min-h-screen mesh-gradient-1 bg-grid-pattern relative overflow-hidden flex flex-col justify-center items-center px-4 select-none">
      {/* Absolute Ambient Background Lights */}
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-primary-500/5 rounded-full blur-[180px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none" />

      {/* sound controls */}
      <div className="absolute top-24 right-8 z-20 flex gap-2">
        {step === 1 && (
          <button
            onClick={() => setShowBridgeModal(true)}
            className="px-3 py-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 font-mono text-[9px] uppercase tracking-wider transition-all flex items-center gap-1.5 shadow-md shadow-indigo-500/5"
            title="Import LinkedIn or Resume raw profiles"
          >
            <FileText size={12} /> Personal Data Bridge
          </button>
        )}
        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className="p-2 rounded-lg bg-slate-900/80 border border-white/5 hover:border-white/10 text-slate-400 hover:text-slate-200 transition-all shadow-md"
          title={soundEnabled ? 'Disable tactical audio chimes' : 'Enable tactical audio chimes'}
        >
          {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
        </button>
      </div>

      <div className="w-full max-w-5xl z-10">
        {/* Onboarding Nav indicators */}
        {step < 4 && (
          <div className="flex items-center justify-between max-w-md mx-auto mb-8 px-4 font-mono select-none">
            {[
              { num: 1, label: 'Identity' },
              { num: 2, label: 'Graph Intake' },
              { num: 3, label: 'Tuning' },
            ].map((node) => (
              <div key={node.num} className="flex items-center flex-1 last:flex-initial">
                <div className="flex flex-col items-center gap-1.5">
                  <div className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                    step === node.num 
                      ? 'bg-primary-500 border-primary-400 text-white shadow-lg shadow-primary-500/20' 
                      : step > node.num 
                        ? 'bg-primary-500/10 border-primary-500/30 text-primary-400' 
                        : 'bg-slate-900 border-white/5 text-slate-500'
                  }`}>
                    {node.num}
                  </div>
                  <span className={`text-[8px] uppercase tracking-widest ${
                    step === node.num ? 'text-white font-bold' : 'text-slate-500'
                  }`}>{node.label}</span>
                </div>
                {node.num < 3 && (
                  <div className={`h-[1px] flex-1 mx-4 -mt-4 transition-colors duration-300 ${
                    step > node.num ? 'bg-primary-500/30' : 'bg-white/5'
                  }`} />
                )}
              </div>
            ))}
          </div>
        )}

        <AnimatePresence mode="wait">
          
          {/* STEP 1: IDENTITY & MESSY AMBITIONS */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              className="max-w-2xl mx-auto"
            >
              <GlassPanel className="p-8 border-primary-500/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-3 text-primary-400 bg-primary-500/5 border-b border-l border-white/5 rounded-bl-xl">
                  <User size={16} />
                </div>
                
                <h1 className="text-xl font-black font-mono tracking-widest text-white uppercase mb-1">Delta Career OS Ingestion</h1>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-8">Establish your professional profile and ambitions</p>
                
                <div className="space-y-5 font-mono">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[9px] uppercase text-slate-400 mb-1.5 tracking-wider">Full Name</label>
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
                      <label className="block text-[9px] uppercase text-slate-400 mb-1.5 tracking-wider">Email Address</label>
                      <input 
                        type="email" 
                        name="email"
                        placeholder="e.g. harsh@student.iit.ac.in"
                        value={profile.email}
                        onChange={handleProfileChange}
                        className="w-full bg-slate-950/80 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[9px] uppercase text-slate-400 mb-1.5 tracking-wider">Target Domain / Role</label>
                    <div className="grid grid-cols-2 gap-3 mt-1.5">
                      {visibleDomainPacks.map((role) => {
                        const targetRole = role.target_roles?.[0] || role.label;
                        const desc = (role.skill_taxonomy || []).slice(0, 4).join(', ');
                        return (
                        <button
                          key={role.id}
                          type="button"
                          onClick={() => {
                            playBeep(600, 0.05, 0.015);
                            setProfile(prev => ({ ...prev, target_role: targetRole, target_domain: role.id }));
                          }}
                          className={`p-3.5 rounded-lg border text-left flex flex-col transition-all duration-300 ${
                            profile.target_role === targetRole
                              ? 'bg-primary-500/10 border-primary-500/40 text-white shadow-lg'
                              : 'bg-slate-950/60 border-white/5 text-slate-400 hover:border-white/10'
                          }`}
                        >
                          <span className="text-[10px] font-bold uppercase tracking-wider mb-1 block">{role.label}</span>
                          <span className="text-[8px] text-slate-500 leading-normal">{desc}</span>
                        </button>
                      )})}
                    </div>
                  </div>

                  <div>
                    <label className="block text-[9px] uppercase text-slate-400 mb-1.5 tracking-wider">Messy Ambitions & Background Journey</label>
                    <p className="text-[8px] text-slate-500 uppercase tracking-wide mb-1.5 leading-normal">
                      Describe your career path, dreams, experience, and constraints in natural human language. Delta will dynamically parse and update your memory graph.
                    </p>

                    {/* Direct Step 1 Direct Resume Ingest Uploader */}
                    <div 
                      onClick={() => step1FileInputRef.current?.click()}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={async (e) => {
                        e.preventDefault();
                        const file = e.dataTransfer.files?.[0];
                        if (file) {
                          setStep1FileParsing(true);
                          toast.info(`Reading ${file.name}...`);
                          try {
                            const text = await parseFile(file);
                            setRawAmbition(text);
                            toast.success(`Successfully loaded ${file.name}! Review/edit your vision below.`);
                          } catch (err) {
                            toast.error(err.message || "Error reading file.");
                          } finally {
                            setStep1FileParsing(false);
                          }
                        }
                      }}
                      className="border border-dashed border-indigo-500/20 hover:border-indigo-500/50 transition-all bg-slate-950/40 hover:bg-slate-950/70 py-4 px-4 rounded-lg flex flex-col items-center justify-center cursor-pointer mb-3 select-none group"
                    >
                      <input 
                        type="file" 
                        ref={step1FileInputRef} 
                        onChange={handleStep1FileUpload} 
                        accept=".pdf,.txt,.md" 
                        className="hidden" 
                      />
                      <div className="flex items-center gap-2 text-indigo-400/80 group-hover:text-indigo-300 transition-colors">
                        <FileText size={16} className={step1FileParsing ? "animate-spin" : "animate-pulse"} />
                        <span className="text-xs uppercase font-bold tracking-widest font-mono">
                          {step1FileParsing ? "Reading File..." : "Or Drag & Drop / Click to Upload Resume"}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest font-mono">
                        Direct Reader: PDF, MD, TXT (Auto-extracts to the field below)
                      </p>
                    </div>

                    <textarea
                      value={rawAmbition}
                      onChange={(e) => setRawAmbition(e.target.value)}
                      placeholder="e.g. I am in my third year of college. I like coding in Python but I have no project proof on GitHub. I get confused with backend and want to learn how to build production-grade LLM applications. I can study 15 hours per week..."
                      className="w-full min-h-[110px] bg-slate-950/80 border border-white/5 rounded-lg px-4 py-3 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors resize-none leading-relaxed"
                    />
                  </div>
                </div>

                <div className="mt-8 flex justify-between items-center">
                  <div className="flex items-center gap-1.5 font-mono text-[8px] text-slate-500 uppercase tracking-widest leading-none">
                    <Database size={10} className="text-primary-500" /> Graph-RAG Active Storage
                  </div>
                  <button 
                    onClick={startAdaptiveIntake}
                    disabled={aiLoading}
                    className="btn-primary px-6 py-2.5 text-xs flex items-center gap-1.5 font-mono uppercase tracking-widest font-bold disabled:opacity-50"
                  >
                    {aiLoading ? 'Querying Market Pulse...' : 'Initialize Memory Graph'} <Sparkles size={14} className="text-indigo-400" />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          )}

          {/* STEP 2: RECURSIVE CONVERSATIONAL INTAKE CHAT */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              className="grid grid-cols-3 gap-6 w-full"
            >
              {/* Conversational Terminal (Main Left) */}
              <div className="col-span-2 flex flex-col h-[550px]">
                <GlassPanel className="p-6 border-primary-500/10 flex flex-col flex-1 relative overflow-hidden bg-slate-950/30">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4 select-none">
                    <div className="flex items-center gap-2">
                      <Terminal size={14} className="text-primary-500 animate-pulse" />
                      <span className="font-mono text-[9px] uppercase tracking-widest text-slate-300 font-bold">
                        Cognitive Twin Engine (User: {profile.name})
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={handleForceComplete}
                        className="font-mono text-[8px] bg-white/5 border border-white/10 hover:bg-white/10 text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded uppercase tracking-wider transition-colors"
                      >
                        Skip Onboarding
                      </button>
                      <span className="font-mono text-[8px] bg-primary-500/10 text-primary-400 border border-primary-500/20 px-2 py-0.5 rounded uppercase tracking-wider animate-pulse">
                        Graph-RAG Active
                      </span>
                    </div>
                  </div>

                  {/* Messages list */}
                  <div className="flex-1 overflow-y-auto pr-1 space-y-4 font-mono scrollbar-hide text-xs">
                    {chatHistory.map((chat, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: chat.role === 'assistant' ? -10 : 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`flex flex-col ${chat.role === 'user' ? 'items-end' : 'items-start'}`}
                      >
                        <div className="flex items-center gap-1.5 mb-1 select-none">
                          <span className={`text-[8px] uppercase tracking-widest font-black ${
                            chat.role === 'user' ? 'text-indigo-400' : 'text-primary-400'
                          }`}>
                            {chat.role === 'user' ? 'User' : 'Delta Intake AI'}
                          </span>
                          <span className="text-[7px] text-slate-600 font-bold">{chat.timestamp}</span>
                        </div>
                        <div className={`p-3 rounded-lg max-w-[85%] border leading-relaxed ${
                          chat.role === 'user'
                            ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-100 rounded-tr-none'
                            : chat.isQuestion || idx === chatHistory.length - 1
                              ? 'bg-primary-500/15 border-primary-500/30 text-white font-bold rounded-tl-none shadow-md shadow-primary-500/5'
                              : 'bg-slate-900 border-white/5 text-slate-300 rounded-tl-none'
                        }`}>
                          {chat.content}
                        </div>
                      </motion.div>
                    ))}
                    {aiLoading && (
                      <div className="flex items-center gap-2 select-none">
                        <span className="text-[8px] uppercase tracking-widest font-black text-primary-400">Delta Intake AI</span>
                        <div className="flex gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Reply Input Bar */}
                  <div className="mt-4 pt-3 border-t border-white/5 flex gap-2 font-mono">
                    <input
                      type="text"
                      placeholder={aiLoading ? "Thinking..." : "Reply to Delta..."}
                      disabled={aiLoading}
                      value={currentAnswer}
                      onChange={(e) => setCurrentAnswer(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') submitChatAnswer();
                      }}
                      className="flex-1 bg-slate-950/80 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary-500 transition-colors disabled:opacity-50"
                    />
                    <button
                      onClick={submitChatAnswer}
                      disabled={aiLoading}
                      className="px-5 py-2.5 rounded-lg bg-primary-500 text-slate-950 font-bold hover:bg-primary-400 text-xs uppercase tracking-widest font-mono transition-all flex items-center gap-1.5 disabled:opacity-50"
                    >
                      Reply <ChevronRight size={12} />
                    </button>
                  </div>
                </GlassPanel>
              </div>

              {/* Cognitive State Sidebar (Right) */}
              <div className="col-span-1 flex flex-col h-[550px] space-y-4">
                {/* Circular completeness Gauge */}
                <GlassPanel className="p-4 border-indigo-500/10 flex flex-col items-center justify-center relative bg-slate-950/60 font-mono text-center select-none">
                  <span className="text-[8px] uppercase text-slate-400 font-bold mb-3 tracking-widest block">Ingestion Completeness</span>
                  <div className="relative w-24 h-24 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="48" cy="48" r="40" stroke="rgba(255,255,255,0.05)" strokeWidth="6" fill="transparent" />
                      <circle 
                        cx="48" 
                        cy="48" 
                        r="40" 
                        stroke="url(#progress-gradient)" 
                        strokeWidth="6" 
                        fill="transparent" 
                        strokeDasharray={2 * Math.PI * 40}
                        strokeDashoffset={2 * Math.PI * 40 * (1 - confidenceScore)}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                      />
                      <defs>
                        <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#ec4899" />
                          <stop offset="100%" stopColor="#6366f1" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute text-center">
                      <span className="text-base font-black text-white">{Math.round(confidenceScore * 100)}%</span>
                      <span className="text-[6px] text-slate-500 uppercase tracking-widest block">complete</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-3 w-full border-t border-white/5 pt-2">
                    <div>
                      <span className="text-[7px] text-slate-500 uppercase tracking-wider block">Graph Nodes</span>
                      <span className="text-xs font-black text-white">{graphSummary.nodes_count}</span>
                    </div>
                    <div>
                      <span className="text-[7px] text-slate-500 uppercase tracking-wider block">Graph Edges</span>
                      <span className="text-xs font-black text-indigo-400">{graphSummary.edges_count}</span>
                    </div>
                  </div>
                </GlassPanel>

                {/* Dynamic Tension Challenge Card (High severity) */}
                <GlassPanel className="p-4 border-rose-500/15 flex flex-col justify-start bg-slate-950/60 font-mono select-none overflow-y-auto max-h-[220px]">
                  <div className="flex items-center gap-1.5 text-rose-400 mb-2">
                    <AlertTriangle size={12} className="animate-bounce" />
                    <span className="text-[8px] uppercase font-bold tracking-widest">Active Tension Nodes ({activeTensions.length})</span>
                  </div>
                  
                  {activeTensions.length > 0 ? (
                    <div className="space-y-3">
                      {activeTensions.slice(0, 2).map((t) => (
                        <div key={t.id} className="p-2.5 rounded bg-rose-500/5 border border-rose-500/10 text-[8px] uppercase leading-relaxed leading-normal text-slate-300">
                          <span className="block text-[7px] text-rose-500 font-bold tracking-wider mb-0.5">{t.type}</span>
                          <div className="mb-1 text-rose-200"><strong>Claim:</strong> "{t.claim}"</div>
                          <div className="text-indigo-300"><strong>Market Reality:</strong> "{t.reality}"</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-4 text-slate-500 text-[8px]">
                      <CheckCircle2 size={16} className="text-emerald-500/50 mb-1" />
                      <span>Zero contradictory signals</span>
                    </div>
                  )}
                </GlassPanel>

                {/* Behavioral Pitfalls Panel */}
                <GlassPanel className="p-4 border-amber-500/15 flex flex-col justify-start bg-slate-950/60 font-mono select-none overflow-y-auto max-h-[150px]">
                  <div className="flex items-center gap-1.5 text-amber-400 mb-2">
                    <Flame size={12} className="animate-pulse" />
                    <span className="text-[8px] uppercase font-bold tracking-widest">Behavioral Pitfalls ({activePitfalls.length})</span>
                  </div>

                  {activePitfalls.length > 0 ? (
                    <div className="space-y-2">
                      {activePitfalls.slice(0, 1).map((p, idx) => (
                        <div key={idx} className="p-2.5 rounded bg-amber-500/5 border border-amber-500/10 text-[8px] uppercase leading-relaxed leading-normal text-slate-300">
                          <span className="block text-[7px] text-amber-500 font-bold tracking-wider mb-0.5">{p.pitfall_type}</span>
                          <div className="text-amber-200 mb-1"><strong>Detector:</strong> "{p.evidence}"</div>
                          <div className="text-slate-400"><strong>Intervention:</strong> {p.intervention}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-4 text-slate-500 text-[8px]">
                      <Compass size={16} className="text-emerald-500/50 mb-1" />
                      <span>No behavioral traps active</span>
                    </div>
                  )}
                </GlassPanel>
              </div>
            </motion.div>
          )}

          {/* STEP 3: CONSTRAINTS, PACING & STATED CAPABILITIES TUNING */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              className="max-w-3xl mx-auto"
            >
              <GlassPanel className="p-8 border-violet-500/10">
                <div className="absolute top-0 right-0 p-3 text-violet-400 bg-violet-500/5 border-b border-l border-white/5 rounded-bl-xl">
                  <Target size={16} />
                </div>
                
                <h1 className="text-xl font-black font-mono tracking-widest text-white uppercase mb-1">Growth Configuration</h1>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-6">Review capability matrix, pacing, and preferred study styles</p>

                <div className="space-y-6 font-mono">
                  {/* Capabilities List */}
                  <div>
                    <h2 className="text-[10px] uppercase text-slate-400 mb-3.5 tracking-wider flex items-center gap-1.5 font-bold">
                      <Award size={13} className="text-indigo-400" /> Stated Capabilities & Proficiencies
                    </h2>
                    {skills.length > 0 ? (
                      <div className="space-y-3">
                        {skills.map((skill, index) => (
                          <div key={skill.name} className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-white/5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-slate-300">{skill.name}</span>
                              <span className="text-[7px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded uppercase tracking-wider">
                                {skill.category}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-[9px] text-slate-500 uppercase mr-1">Rank:</span>
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

                        {/* Add Skill bar */}
                        <div className="flex items-center gap-2 pt-1">
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
                            className="flex-1 bg-slate-950/60 border border-white/5 rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
                          />
                          <button
                            onClick={() => {
                              addSkill(newSkillName);
                              setNewSkillName('');
                            }}
                            className="px-4 py-2 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-xs text-slate-300 transition-colors"
                          >
                            Add
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-6 border border-white/5 rounded-lg text-slate-500 text-xs bg-slate-950/20">
                        No skills extracted yet. Add a few claimed skills to start.
                        <div className="flex items-center gap-2 max-w-sm mx-auto mt-4">
                          <input
                            type="text"
                            placeholder="Add skill... (e.g. Python)"
                            value={newSkillName}
                            onChange={(e) => setNewSkillName(e.target.value)}
                            className="flex-1 bg-slate-950 border border-white/5 rounded-lg px-3 py-1.5 text-xs text-white"
                          />
                          <button
                            onClick={() => {
                              addSkill(newSkillName);
                              setNewSkillName('');
                            }}
                            className="px-4 py-1.5 rounded-lg bg-white/5 text-xs border border-white/5 text-slate-300"
                          >
                            Add
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-6 pt-3 border-t border-white/5">
                    {/* Weekly Commitment Hours slider */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Weekly Pacing Commitment</label>
                        <span className="text-[10px] text-primary-400 font-bold">{profile.hours_per_week} hrs/week</span>
                      </div>
                      <input 
                        type="range" 
                        min="3" 
                        max="40"
                        value={profile.hours_per_week}
                        onChange={(e) => {
                          setProfile(prev => ({ ...prev, hours_per_week: parseInt(e.target.value) }));
                        }}
                        className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-primary-500 border border-white/5"
                      />
                      <div className="flex justify-between text-[7px] text-slate-500 uppercase mt-1">
                        <span>Low (3h)</span>
                        <span>Standard (15h)</span>
                        <span>High (40h)</span>
                      </div>
                    </div>

                    {/* Learning Style Preference */}
                    <div>
                      <label className="block text-[10px] uppercase font-bold text-slate-400 mb-2 tracking-wider">Preferred Learning Mode</label>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { id: 'practical', label: 'Practical', desc: 'Code first' },
                          { id: 'theoretical', label: 'Academic', desc: 'Syllabus' },
                          { id: 'competitive', label: 'Sprints', desc: 'Hackathons' }
                        ].map((style) => (
                          <button
                            key={style.id}
                            onClick={() => {
                              playBeep(500, 0.05, 0.015);
                              setProfile(prev => ({ ...prev, learning_style: style.id }));
                            }}
                            className={`p-2 rounded-lg border text-left flex flex-col justify-between transition-all duration-300 ${
                              profile.learning_style === style.id
                                ? 'bg-violet-500/10 border-violet-500/40 text-white'
                                : 'bg-slate-950/60 border-white/5 text-slate-400 hover:border-white/10 hover:text-slate-300'
                            }`}
                          >
                            <span className="text-[9px] font-bold uppercase tracking-wider mb-0.5 block">{style.label}</span>
                            <span className="text-[7px] text-slate-500 leading-none">{style.desc}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 flex justify-between">
                  <button 
                    onClick={() => {
                      if (sessionId) setStep(2);
                      else setStep(1);
                    }}
                    className="px-5 py-2.5 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-xs font-mono text-slate-400 uppercase tracking-wider transition-colors"
                  >
                    Back
                  </button>
                  <button 
                    onClick={compileCareerOS}
                    className="btn-primary px-6 py-2.5 text-xs flex items-center gap-1.5 font-mono uppercase tracking-widest font-bold bg-gradient-to-r from-primary-500 to-indigo-500 hover:from-primary-600 hover:to-indigo-600 border-none shadow-lg shadow-primary-500/20"
                  >
                    Synchronize & Compile OS <Cpu size={14} className="text-primary-950" />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          )}

          {/* STEP 4: CYBERPUNK COMPILER TERMINAL */}
          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="max-w-2xl mx-auto w-full"
            >
              <GlassPanel className="p-8 border-primary-500/20 scan-line relative overflow-hidden min-h-[460px] flex flex-col justify-between bg-black/40">
                <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500/5 rounded-full blur-[140px] pointer-events-none" />
                
                <div className="text-center py-4 border-b border-white/5">
                  <Cpu className="text-primary-400 animate-spin mb-3 mx-auto" size={32} />
                  <h1 className="text-base font-black font-mono tracking-widest text-white uppercase mb-0.5">Compiling Career OS Graph</h1>
                  <p className="text-[9px] font-mono text-primary-400 uppercase tracking-widest">Active bidirectional sqlite state compilation</p>
                </div>

                {/* Simulated Log Output Console */}
                <div 
                  ref={logContainerRef}
                  className="bg-black/90 border border-white/5 rounded-lg p-5 h-64 overflow-y-auto font-mono text-[9px] text-slate-400 space-y-1.5 scrollbar-hide select-none flex flex-col justify-start leading-relaxed text-left"
                >
                  {loadingLogs.map((log, idx) => (
                    <div key={idx} className="flex items-start gap-1.5">
                      <span className="text-primary-500 font-bold flex-shrink-0">{`>`}</span>
                      <pre className="whitespace-pre-wrap font-mono m-0 p-0 text-slate-300">{log}</pre>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex items-center gap-1">
                      <span className="text-primary-400 animate-pulse font-black">_</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-[8px] font-mono text-slate-500 uppercase tracking-wider border-t border-white/5 pt-4">
                  <span>Delta OS v3.5.0 (GraphRAG Active)</span>
                  <span className="text-primary-500 animate-pulse font-bold">SQL Database Syncing...</span>
                </div>
              </GlassPanel>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* PERSONAL DATA BRIDGE MODAL */}
      <AnimatePresence>
        {showBridgeModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg"
            >
              <GlassPanel className="p-6 border-indigo-500/20 font-mono">
                <div className="flex justify-between items-center mb-4 pb-2 border-b border-white/5 select-none">
                  <div className="flex items-center gap-2 text-indigo-400">
                    <FileText size={16} />
                    <span className="text-xs uppercase font-bold tracking-widest">Personal Data Ingestion Bridge</span>
                  </div>
                  <button
                    onClick={() => {
                      playBeep(500, 0.05, 0.01);
                      setShowBridgeModal(false);
                    }}
                    className="text-slate-500 hover:text-slate-300 text-xs"
                  >
                    CLOSE
                  </button>
                </div>
                
                <p className="text-[8px] text-slate-500 uppercase tracking-wider leading-relaxed mb-4">
                  Paste the plain text of your resume or LinkedIn profile page. Delta Profile Intelligence will extract entities, construct your graph vertices, and seed your baseline capabilities immediately!
                </p>

                {/* File Drag & Drop / Upload Zone */}
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={async (e) => {
                    e.preventDefault();
                    const file = e.dataTransfer.files?.[0];
                    if (file) {
                      setFileParsing(true);
                      toast.info(`Reading ${file.name}...`);
                      try {
                        const text = await parseFile(file);
                        setRawProfileImportText(text);
                        toast.success(`Successfully extracted ${file.name}!`);
                      } catch (err) {
                        toast.error(err.message || "Error reading file.");
                      } finally {
                        setFileParsing(false);
                      }
                    }
                  }}
                  className="border border-dashed border-indigo-500/30 hover:border-indigo-500/60 transition-colors bg-slate-950/40 hover:bg-slate-950/60 py-5 px-4 rounded-lg flex flex-col items-center justify-center cursor-pointer mb-4 select-none group"
                >
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileUpload} 
                    accept=".pdf,.txt,.md" 
                    className="hidden" 
                  />
                  <div className="flex items-center gap-2 text-indigo-400 group-hover:scale-105 transition-transform">
                    <FileText size={18} className="animate-pulse" />
                    <span className="text-[10px] uppercase font-bold tracking-widest">
                      {fileParsing ? "Extracting Data..." : "Drag & Drop Resume File"}
                    </span>
                  </div>
                  <p className="text-[8px] text-slate-500 mt-1 uppercase tracking-widest">
                    Supports PDF, Markdown, and TXT files (Auto-parsed on client)
                  </p>
                </div>

                <textarea
                  value={rawProfileImportText}
                  onChange={(e) => setRawProfileImportText(e.target.value)}
                  placeholder="Or review/paste/edit raw LinkedIn summary, experiences, and accomplishments text here..."
                  className="w-full min-h-[160px] bg-slate-950/80 border border-white/5 rounded-lg px-4 py-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none leading-relaxed mb-4"
                />

                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => {
                      playBeep(500, 0.05, 0.01);
                      setShowBridgeModal(false);
                    }}
                    className="px-4 py-2 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-[10px] text-slate-400 uppercase tracking-wider transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleProfileBridgeImport}
                    disabled={bridgeLoading}
                    className="px-5 py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-slate-950 font-bold text-[10px] uppercase tracking-widest transition-all flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {bridgeLoading ? "Bridging profile..." : "Inject via Bridge"} <Sparkles size={12} />
                  </button>
                </div>
              </GlassPanel>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
