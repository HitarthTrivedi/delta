import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Zap, Cpu, RefreshCw, Sparkles, BookOpen, User } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import { chatAPI, briefsAPI } from '../lib/api';
import { toast } from 'sonner';

export default function CareerChat() {
  const userId = useAuthStore((state) => state.userId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [activeBrief, setActiveBrief] = useState(null);
  const messagesEndRef = useRef(null);

  const loadData = async () => {
    try {
      const history = await chatAPI.getHistory(userId);
      setMessages(history.messages || []);

      const briefRes = await briefsAPI.getLatest(userId);
      setActiveBrief(briefRes);
    } catch (err) {
      console.error(err);
      toast.error('Unable to establish SQLite websocket link. Reverting to offline thread.');
    }
  };

  useEffect(() => {
    loadData();
  }, [userId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim()) return;

    if (!textToSend) setInput('');

    // Append user message
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setSending(true);

    try {
      const response = await chatAPI.send({
        user_id: userId,
        message: text
      });

      // Append AI response
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
    } catch (err) {
      console.error(err);
      toast.error('AI Core handshake failed. SQLite database roll-back completed.');
    } finally {
      setSending(false);
    }
  };

  const autofillChip = (skill) => {
    const questions = [
      `How do I set up a robust, industry-grade project structure for ${skill}?`,
      `What are the most common mistakes beginners make when learning ${skill}?`,
      `Explain the advanced senior developer twists and caveats for ${skill}.`,
      `Give me a mock technical question on ${skill} commonly asked in Bengaluru startups.`
    ];
    const chosen = questions[Math.floor(Math.random() * questions.length)];
    setInput(chosen);
  };

  return (
    <div className="pt-20 px-6 max-w-7xl mx-auto min-h-screen text-slate-300 font-mono pb-12 relative overflow-hidden flex flex-col">
      {/* Glow overlays */}
      <div className="absolute top-10 left-10 w-[400px] h-[400px] bg-primary-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-cyan-500/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Title */}
      <div className="mb-6 flex justify-between items-center border-b border-white/5 pb-4">
        <div>
          <h1 className="text-2xl font-black tracking-widest text-white uppercase flex items-center gap-2">
            <Cpu className="text-primary-400 animate-pulse" size={24} /> DELTA // CAREER_AI
          </h1>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">
            Realtime Sandbox Chat Link // Cognitive Context Synced to SQLite
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch flex-1">
        
        {/* Left Side: Context drawer & Target recommendations */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <GlassPanel className="p-6 border-white/5 flex flex-col justify-between flex-1 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-80 h-80 bg-primary-500/5 rounded-full blur-[120px] pointer-events-none" />
            
            <div className="space-y-4">
              <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest flex items-center gap-1.5">
                <BookOpen size={12} /> Active Targets Context
              </h2>
              <p className="text-[8px] text-slate-500 uppercase leading-normal">
                Click any context chip below to auto-populate senior-developer prompts mapped directly to your active roadmap nodes.
              </p>

              <div className="flex flex-wrap gap-2 pt-2">
                {activeBrief?.demanded_skills?.map((skill) => (
                  <button
                    key={skill}
                    onClick={() => autofillChip(skill)}
                    className="px-2.5 py-1.5 rounded bg-white/5 hover:bg-primary-500/10 border border-white/5 hover:border-primary-500/20 text-[9px] font-bold text-slate-300 uppercase transition-all duration-300 flex items-center gap-1"
                  >
                    <Sparkles size={8} className="text-primary-400" /> {skill}
                  </button>
                ))}
              </div>
            </div>

            <div className="border-t border-white/5 pt-4 mt-6">
              <h3 className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mb-2">Cognitive Capabilities Active</h3>
              <div className="space-y-1.5 font-mono text-[8px] text-slate-400 uppercase">
                <p>+ Contextual RAG matching enabled</p>
                <p>+ SQLite history tracking live</p>
                <p>+ Bangalore hiring standards mapping</p>
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* Right Side: Messaging Terminal */}
        <div className="lg:col-span-8 flex flex-col min-h-[500px]">
          <GlassPanel className="flex-1 flex flex-col justify-between p-6 border-primary-500/10 relative overflow-hidden">
            
            {/* Scrollable messages box */}
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 scrollbar-hide max-h-[480px]">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col justify-center items-center text-center py-20 text-slate-500">
                  <Zap className="text-primary-400 animate-pulse mb-3" size={24} />
                  <p className="text-[10px] uppercase font-bold text-slate-300">Delta Career Intelligence Co-Pilot Initialized</p>
                  <p className="text-[8px] uppercase max-w-sm leading-normal mt-1">
                    Ask me anything about your roadmap, local Bangalore hiring requirements, resume optimizations, or Docker setups!
                  </p>
                </div>
              ) : (
                messages.map((msg, idx) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div 
                      key={idx} 
                      className={`flex gap-3 max-w-[80%] ${
                        isUser ? 'ml-auto flex-row-reverse' : ''
                      }`}
                    >
                      {/* Avatar */}
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                        isUser 
                          ? 'bg-slate-900 border-white/5 text-slate-400' 
                          : 'bg-primary-500/10 border-primary-500/20 text-primary-400'
                      }`}>
                        {isUser ? <User size={14} /> : <Cpu size={14} />}
                      </div>

                      {/* Content block */}
                      <div className={`p-3 rounded-xl border text-[10px] uppercase leading-normal font-mono ${
                        isUser 
                          ? 'bg-slate-900 border-white/5 text-slate-200' 
                          : 'bg-slate-950/60 border-primary-500/5 text-slate-300 relative overflow-hidden'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  );
                })
              )}
              {sending && (
                <div className="flex gap-3 max-w-[80%]">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border bg-primary-500/10 border-primary-500/20 text-primary-400">
                    <Cpu size={14} className="animate-spin" />
                  </div>
                  <div className="p-3 rounded-xl border bg-slate-950/60 border-primary-500/5 text-primary-500 font-bold text-[9px] uppercase tracking-wider animate-pulse flex items-center gap-1.5">
                    Co-pilot is calculating...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form 
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="mt-6 flex gap-2 border-t border-white/5 pt-4"
            >
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Delta AI a career question... (e.g. Optimize Docker slim image)"
                disabled={sending}
                className="flex-1 bg-slate-900 border border-white/5 rounded-lg px-4 py-3 text-[10px] text-white focus:outline-none focus:border-primary-500 font-mono"
              />
              <button
                type="submit"
                disabled={sending}
                className="p-3 rounded-lg bg-primary-500 hover:bg-primary-600 border border-primary-400 text-white transition-colors"
              >
                <Send size={14} />
              </button>
            </form>

          </GlassPanel>
        </div>

      </div>
    </div>
  );
}
