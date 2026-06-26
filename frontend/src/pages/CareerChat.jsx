import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Zap, Cpu, Sparkles, BookOpen, User } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import { chatAPI, briefsAPI, careerOSAPI } from '../lib/api';
import { toast } from 'sonner';

// Markdown component styled for dark chat bubbles
function ChatMarkdown({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
        code: ({ inline, children }) =>
          inline ? (
            <code className="bg-slate-800 text-cyan-300 px-1 py-0.5 rounded text-[11px] font-mono">{children}</code>
          ) : (
            <pre className="bg-slate-900 border border-white/10 rounded-lg p-3 overflow-x-auto my-2">
              <code className="text-cyan-300 text-[11px] font-mono">{children}</code>
            </pre>
          ),
        h1: ({ children }) => <h1 className="text-base font-bold text-white mb-1 mt-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-bold text-white mb-1 mt-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-200 mb-1 mt-2">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-400 underline hover:text-primary-300">
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-primary-500/50 pl-3 text-slate-400 italic my-2">{children}</blockquote>
        ),
        hr: () => <hr className="border-white/10 my-3" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function CareerChat() {
  const userId = useAuthStore((state) => state.userId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [activeBrief, setActiveBrief] = useState(null);
  const [careerContext, setCareerContext] = useState(null);
  const messagesEndRef = useRef(null);

  const loadData = useCallback(async () => {
    try {
      const [history, briefRes, contextRes] = await Promise.all([
        chatAPI.getHistory(userId),
        briefsAPI.getLatest(userId).catch(() => null),
        careerOSAPI.getContext(userId).catch(() => null),
      ]);
      setMessages(history.messages || []);
      setActiveBrief(briefRes);
      setCareerContext(contextRes);
    } catch (err) {
      console.error(err);
    }
  }, [userId]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim();
    if (!text) return;
    if (!textToSend) setInput('');

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setSending(true);

    try {
      const response = await chatAPI.send({ user_id: userId, message: text });
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
    } catch (err) {
      console.error(err);
      toast.error('Failed to get a response. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const autofillChip = (skill) => {
    const questions = [
      `How do I build a strong project in ${skill} that I can put on my resume?`,
      `What are the most common mistakes beginners make when learning ${skill}?`,
      `What should an intermediate ${skill} developer know that beginners often miss?`,
      `Give me a practical weekly plan to get job-ready with ${skill}.`,
    ];
    setInput(questions[Math.floor(Math.random() * questions.length)]);
  };

  const proofProjects = careerContext?.proof_projects || [];
  const portfolio = careerContext?.portfolio_assessment || {};
  const targetRole = careerContext?.memory?.ambitions?.target_role || 'Your career goal';
  const activePhase = careerContext?.roadmap?.weekly_focus?.phase_name || 'Building skills';

  return (
    <div className="pt-20 pb-8 px-4 sm:px-6 max-w-7xl mx-auto min-h-screen text-slate-300 flex flex-col">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3 border-b border-white/5 pb-4">
        <Cpu className="text-primary-400 shrink-0" size={20} />
        <div>
          <h1 className="text-lg font-bold text-white">Delta Career AI</h1>
          <p className="text-xs text-slate-500">Your personal career co-pilot — ask anything about your roadmap, skills, or next steps</p>
        </div>
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-12 gap-5 flex-1 min-h-0">

        {/* Left panel — context & chips (hidden on mobile, shown as row on md+) */}
        <div className="hidden lg:flex lg:col-span-3 flex-col gap-4">
          <GlassPanel className="p-4 border-white/5 flex flex-col gap-4 flex-1">
            <div>
              <p className="text-[10px] font-bold uppercase text-slate-500 tracking-widest flex items-center gap-1 mb-2">
                <BookOpen size={10} /> Context
              </p>
              <p className="text-xs text-slate-400">
                <span className="text-white font-medium">{targetRole}</span>
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">{activePhase}</p>
            </div>

            {activeBrief?.demanded_skills?.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-2">Ask about</p>
                <div className="flex flex-wrap gap-1.5">
                  {activeBrief.demanded_skills.slice(0, 8).map((skill) => (
                    <button
                      key={skill}
                      onClick={() => autofillChip(skill)}
                      className="px-2 py-1 rounded bg-white/5 hover:bg-primary-500/10 border border-white/5 hover:border-primary-500/20 text-[10px] text-slate-300 transition-all flex items-center gap-1"
                    >
                      <Sparkles size={8} className="text-primary-400" /> {skill}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {proofProjects.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-2">Proof Projects</p>
                <div className="space-y-1.5">
                  {proofProjects.slice(0, 3).map((project) => (
                    <button
                      key={project.id}
                      onClick={() => setInput(`Help me build: ${project.title}. Give me exact milestones and a README structure.`)}
                      className="w-full text-left p-2 rounded bg-slate-950/60 border border-white/5 hover:border-primary-500/20 transition-colors"
                    >
                      <span className="block text-xs text-primary-400 font-medium truncate">{project.title}</span>
                      <span className="block text-[10px] text-slate-500 mt-0.5 truncate">{project.resume_headline}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(portfolio).length > 0 && (
              <div className="border-t border-white/5 pt-3">
                <p className="text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-1.5">Portfolio</p>
                <p className="text-[11px] text-slate-400">
                  Status: <span className="text-primary-400 font-medium">{portfolio.readiness || 'unknown'}</span>
                </p>
              </div>
            )}
          </GlassPanel>
        </div>

        {/* Chat panel */}
        <div className="lg:col-span-9 flex flex-col flex-1 min-h-[500px]">
          <GlassPanel className="flex-1 flex flex-col p-4 sm:p-5 border-primary-500/10 min-h-0">

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-hide" style={{ maxHeight: 'calc(100vh - 280px)', minHeight: 300 }}>
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Zap className="text-primary-400 mb-3" size={28} />
                  <p className="text-sm font-semibold text-white mb-1">Ask me anything</p>
                  <p className="text-xs text-slate-500 max-w-sm">
                    I know your profile, skills, roadmap, and weekly tasks. Ask about your next steps, how to build a project, what to put on your resume, or anything career-related.
                  </p>
                  {/* Quick starter chips on empty state */}
                  <div className="flex flex-wrap gap-2 justify-center mt-5">
                    {[
                      "What should I focus on this week?",
                      "How do I improve my resume?",
                      "What projects should I build?",
                      "Am I on track for my goal?",
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300 hover:bg-primary-500/10 hover:border-primary-500/20 transition-all"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div key={idx} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      {!isUser && (
                        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-primary-500/15 border border-primary-500/30 text-primary-400 mt-0.5">
                          <Cpu size={13} />
                        </div>
                      )}
                      <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                        isUser
                          ? 'bg-primary-600/20 border border-primary-500/20 text-slate-100 rounded-tr-sm'
                          : 'bg-slate-900/80 border border-white/8 text-slate-200 rounded-tl-sm'
                      }`}>
                        {isUser ? (
                          <p className="leading-relaxed">{msg.content}</p>
                        ) : (
                          <ChatMarkdown content={msg.content} />
                        )}
                      </div>
                      {isUser && (
                        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-slate-800 border border-white/10 text-slate-400 mt-0.5">
                          <User size={13} />
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {sending && (
                <div className="flex gap-3 justify-start">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-primary-500/15 border border-primary-500/30 text-primary-400">
                    <Cpu size={13} className="animate-spin" />
                  </div>
                  <div className="bg-slate-900/80 border border-white/8 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1 items-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="mt-4 flex gap-2 border-t border-white/5 pt-4"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything about your career, roadmap, or next steps..."
                disabled={sending}
                className="flex-1 bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-primary-500/50 transition-colors"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="px-4 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors shrink-0"
              >
                <Send size={16} />
              </button>
            </form>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
