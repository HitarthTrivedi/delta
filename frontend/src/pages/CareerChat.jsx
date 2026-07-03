import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Send, Cpu, Sparkles, BookOpen } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import { chatAPI, briefsAPI } from '../lib/api';
import { fetchCareerContext } from '../hooks/useCareerOS';
import { toast } from 'sonner';

// Markdown renderer for Agent 2 answers. Nested list depth is differentiated
// via the .chat-markdown CSS below (react-markdown gives one component per
// tag regardless of depth, so per-level marker/indent steps live in CSS).
function ChatMarkdown({ content }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-3 last:mb-0 space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 last:mb-0 space-y-1.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic text-ink">{children}</em>,
          code: ({ inline, children }) =>
            inline ? (
              <code className="bg-accent-surface text-oxblood px-1 py-0.5 text-[12px] font-mono">{children}</code>
            ) : (
              <pre className="bg-accent-surface border border-rule p-3 overflow-x-auto my-3">
                <code className="text-oxblood text-[12px] font-mono">{children}</code>
              </pre>
            ),
          h1: ({ children }) => <h1 className="font-display text-lg font-semibold text-ink mb-2 mt-4 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="font-display text-base font-semibold text-ink mb-2 mt-4 first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-ink mb-1.5 mt-3 first:mt-0">{children}</h3>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-oxblood underline hover:text-ink">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border border-rule bg-accent-surface px-3 py-2 text-ink-soft italic my-3">{children}</blockquote>
          ),
          hr: () => <hr className="border-rule my-4" />,
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto border border-rule">
              <table className="w-full border-collapse text-[13px]">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-accent-surface">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-rule last:border-b-0">{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-semibold text-ink border-r border-rule last:border-r-0">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 align-top text-ink-soft border-r border-rule last:border-r-0">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
      <style>{`
        /* Each nesting level steps in by one more pl-5 (20px) and swaps marker
           style, matching how Perplexity differentiates sub-points instead of
           repeating the same disc/indent at every depth. */
        .chat-markdown ul ul, .chat-markdown ol ul { list-style-type: circle; margin: 6px 0 0; }
        .chat-markdown ul ul ul, .chat-markdown ol ul ul { list-style-type: square; }
        .chat-markdown ul ol, .chat-markdown ol ol { margin: 6px 0 0; }
        .chat-markdown li > ul, .chat-markdown li > ol { margin-bottom: 0; }
        .chat-markdown li::marker { color: var(--ink-soft); }
      `}</style>
    </div>
  );
}

export default function CareerChat() {
  const userId = useAuthStore((state) => state.userId);
  const queryClient = useQueryClient();
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
        fetchCareerContext(queryClient, userId).catch(() => null),
      ]);
      setMessages(history.messages || []);
      setActiveBrief(briefRes);
      setCareerContext(contextRes);
    } catch (err) {
      console.error(err);
    }
  }, [userId, queryClient]);

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

    let acc = '';
    // Append the assistant turn on the first token, then keep updating it.
    const renderAssistant = (content) => setMessages(prev => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      if (last && last.role === 'assistant') copy[copy.length - 1] = { ...last, content };
      else copy.push({ role: 'assistant', content });
      return copy;
    });

    try {
      await chatAPI.streamMessage({ user_id: userId, message: text }, {
        onToken: (t) => { acc += t; renderAssistant(acc); },
        onDone: (payload) => { renderAssistant((payload && payload.response) || acc || ''); },
        onError: async (err) => {
          console.error(err);
          // Hard stream failure — fall back to the non-streaming endpoint.
          try {
            const res = await chatAPI.send({ user_id: userId, message: text });
            renderAssistant(res.response);
          } catch (e2) {
            console.error(e2);
            toast.error('Failed to get a response. Please try again.');
          }
        },
      });
    } finally {
      setSending(false);
    }
  };

  const autofillChip = (skill) => {
    setInput(`How do I build a strong project in ${skill} that I can put on my resume?`);
  };

  const proofProjects = careerContext?.proof_projects || [];
  const portfolio = careerContext?.portfolio_assessment || {};
  const targetRole = careerContext?.memory?.ambitions?.target_role || '';
  const activePhase = careerContext?.roadmap?.weekly_focus?.phase_name || 'Building skills';

  return (
    <div className="pt-20 pb-8 px-4 sm:px-6 max-w-7xl mx-auto min-h-screen text-ink flex flex-col">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3 border-b border-rule pb-4">
        <Cpu className="text-oxblood shrink-0" size={20} />
        <div>
          <h1 className="font-display text-xl font-semibold text-oxblood">Delta Career AI</h1>
          <p className="text-xs text-ink-soft">Your personal career co-pilot — ask anything about your roadmap, skills, or next steps</p>
        </div>
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-12 gap-5 flex-1 min-h-0">

        {/* Left panel — context & chips (hidden on mobile, shown as row on md+) */}
        <div className="hidden lg:flex lg:col-span-3 flex-col gap-4">
          <GlassPanel className="p-4 flex flex-col gap-4 flex-1">
            <div>
              <p className="font-mono text-[10px] uppercase text-ink-soft tracking-[0.18em] flex items-center gap-1.5 mb-2">
                <BookOpen size={10} /> Context
              </p>
              {targetRole && (
                <p className="text-xs text-ink-soft">
                  <span className="text-ink font-medium">{targetRole}</span>
                </p>
              )}
              <p className="text-[11px] text-ink-soft mt-0.5">{activePhase}</p>
            </div>

            {activeBrief?.demanded_skills?.length > 0 && (
              <div>
                <p className="font-mono text-[10px] uppercase text-ink-soft tracking-[0.18em] mb-2">Ask about</p>
                <div className="flex flex-wrap gap-1.5">
                  {activeBrief.demanded_skills.slice(0, 8).map((skill) => (
                    <button
                      key={skill}
                      onClick={() => autofillChip(skill)}
                      className="px-2.5 py-1 bg-paper hover:bg-accent-surface border border-rule hover:border-oxblood/40 text-[10px] text-ink transition-colors flex items-center gap-1"
                    >
                      <Sparkles size={8} className="text-oxblood" /> {skill}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {proofProjects.length > 0 && (
              <div>
                <p className="font-mono text-[10px] uppercase text-ink-soft tracking-[0.18em] mb-2">Proof Projects</p>
                <div className="space-y-1.5">
                  {proofProjects.slice(0, 3).map((project) => (
                    <button
                      key={project.id}
                      onClick={() => setInput(`Help me build: ${project.title}. Give me exact milestones and a README structure.`)}
                      className="w-full text-left p-2 bg-accent-surface border border-rule hover:border-oxblood/40 transition-colors"
                    >
                      <span className="block text-xs text-oxblood font-medium truncate">{project.title}</span>
                      <span className="block text-[10px] text-ink-soft mt-0.5 truncate">{project.resume_headline}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(portfolio).length > 0 && (
              <div className="border-t border-rule pt-3">
                <p className="font-mono text-[10px] uppercase text-ink-soft tracking-[0.18em] mb-1.5">Portfolio</p>
                <p className="text-[11px] text-ink-soft">
                  Status: <span className="text-oxblood font-medium">{portfolio.readiness || 'unknown'}</span>
                </p>
              </div>
            )}
          </GlassPanel>
        </div>

        {/* Chat panel */}
        <div className="lg:col-span-9 flex flex-col flex-1 min-h-[500px]">
          <GlassPanel className="flex-1 flex flex-col p-4 sm:p-6 min-h-0" hover={false}>

            {/* Turns — flowing Q&A, not chat bubbles: each turn is a query line
                followed by the answer flowing directly below it, divided by a
                rule from the next turn. */}
            <div className="flex-1 overflow-y-auto pr-1 scrollbar-hide" style={{ maxHeight: 'calc(100vh - 280px)', minHeight: 300 }}>
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Sparkles className="text-oxblood mb-3" size={26} />
                  <p className="font-display text-lg font-medium text-ink mb-1.5">Ask me anything</p>
                  <p className="text-xs text-ink-soft max-w-sm">
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
                        className="px-3.5 py-2 bg-paper border border-rule text-xs text-ink hover:border-oxblood/40 hover:bg-accent-surface transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.reduce((turns, msg, idx) => {
                  // Group each user message with the assistant reply that follows it
                  // into one "turn" block, matching Perplexity's per-question layout.
                  if (msg.role === 'user') turns.push({ query: msg, answer: null });
                  else if (turns.length) turns[turns.length - 1].answer = msg;
                  else turns.push({ query: null, answer: msg });
                  return turns;
                }, []).map((turn, idx) => (
                  <div key={idx} className={`py-6 first:pt-0 ${idx === 0 ? '' : 'border-t border-rule'}`}>
                    {turn.query && (
                      <h2 className="font-display text-xl font-medium text-ink leading-snug mb-3">
                        {turn.query.content}
                      </h2>
                    )}
                    {turn.answer ? (
                      <div className="flex gap-3">
                        <Cpu size={14} className="text-oxblood shrink-0 mt-1" />
                        <div className="text-sm text-ink min-w-0 flex-1">
                          <ChatMarkdown content={turn.answer.content} />
                        </div>
                      </div>
                    ) : (
                      idx === messages.reduce((c, m) => c + (m.role === 'user' ? 1 : 0), 0) - 1 && sending && (
                        <div className="flex items-center gap-2.5 text-ink-soft">
                          <Cpu size={14} className="text-oxblood animate-spin shrink-0" />
                          <div className="flex gap-1 items-center">
                            <span className="w-1.5 h-1.5 bg-oxblood animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 bg-oxblood animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1.5 h-1.5 bg-oxblood animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        </div>
                      )
                    )}
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="mt-4 flex gap-2 border-t border-rule pt-4"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything about your career, roadmap, or next steps..."
                disabled={sending}
                className="flex-1 bg-paper border border-rule px-4 py-3 text-sm text-ink placeholder-ink-soft focus:outline-none focus:border-oxblood transition-colors"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="px-4 py-3 bg-oxblood hover:bg-ink disabled:opacity-40 disabled:cursor-not-allowed text-bone transition-colors shrink-0"
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
