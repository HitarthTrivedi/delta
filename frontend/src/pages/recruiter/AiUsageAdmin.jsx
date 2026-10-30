import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { engagementAPI } from '../../lib/api';

// Admin: this month's AI spend (estimated from real token counts), the budget,
// alerts already sent, and whether Delta has dropped to the lite model.
export default function AiUsageAdmin() {
  const { data, isLoading, error } = useQuery({ queryKey: ['admin-ai-usage'], queryFn: engagementAPI.adminAiUsage });
  if (isLoading) return <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />;
  if (!data) return <p className="text-ink-soft text-[14px]">{error?.response?.data?.detail || 'Could not load AI usage.'}</p>;
  const usd = (v) => `$${(v || 0).toFixed(2)}`;
  return (
    <div className="grid gap-4">
      <section className="bg-paper border border-rule p-5">
        <p className="m-0 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">{data.month}</p>
        <p className="m-0 mt-1 text-[24px] font-semibold text-ink tabular-nums">
          {usd(data.spent)}{data.budget ? <span className="text-ink-soft text-[16px] font-normal"> of {usd(data.budget)} ({data.pct}%)</span> : ''}
        </p>
        <p className="m-0 mt-1 text-[13.5px] text-ink-soft">
          {!data.budget
            ? 'No monthly budget set (AI_MONTHLY_BUDGET_USD), so there are no alerts and nothing degrades.'
            : data.degraded
              ? 'Budget reached: every AI task uses the lite model and optional AI features are paused until next month or until the budget is raised.'
              : `Admins are emailed at ${data.thresholds.join('%, ')}%.`}
          {data.alerts_sent.length > 0 && ` Alerts sent this month: ${data.alerts_sent.join('%, ')}%.`}
        </p>
        <p className="m-0 mt-1 text-[12px] text-ink-soft">Estimates from token counts × the prices in config; your provider's bill is the source of truth.</p>
      </section>
      <div className="overflow-x-auto border border-rule bg-paper">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="text-left text-ink-soft font-mono text-[10.5px] uppercase tracking-[0.1em]">
              <th className="px-3 py-2 font-normal">Task</th><th className="px-3 py-2 font-normal">Model</th>
              <th className="px-3 py-2 font-normal text-right">Calls</th><th className="px-3 py-2 font-normal text-right">Tokens in / out</th>
              <th className="px-3 py-2 font-normal text-right">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {data.breakdown.map((r) => (
              <tr key={`${r.task}-${r.model}`} className="border-t border-rule">
                <td className="px-3 py-2 text-ink">{r.task}</td>
                <td className="px-3 py-2 text-ink-soft">{r.model}</td>
                <td className="px-3 py-2 text-right tabular-nums">{r.calls}</td>
                <td className="px-3 py-2 text-right tabular-nums text-ink-soft">{r.input_tokens.toLocaleString()} / {r.output_tokens.toLocaleString()}</td>
                <td className="px-3 py-2 text-right tabular-nums">{usd(r.est_cost_usd)}</td>
              </tr>
            ))}
            {!data.breakdown.length && <tr><td colSpan={5} className="px-3 py-3 text-ink-soft">No AI calls this month yet.</td></tr>}
          </tbody>
        </table>
      </div>
      <details className="text-[13px] text-ink-soft">
        <summary className="cursor-pointer">Which model each task uses</summary>
        <ul className="mt-2 grid gap-0.5 pl-5">
          {Object.entries(data.routes).sort().map(([task, route]) => <li key={task}><span className="text-ink">{task}</span>: {route}</li>)}
        </ul>
      </details>
    </div>
  );
}
