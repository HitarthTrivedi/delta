import { useQuery } from '@tanstack/react-query';
import { sandboxReportAPI } from '../lib/api';

// The Test Center report (readiness, per-skill scores, the user's field), shared
// by the Test Center and the practice tools so it's fetched once per minute,
// not on every page.
export function useSandboxReport(userId) {
  return useQuery({
    queryKey: ['sandboxReport', userId],
    queryFn: () => sandboxReportAPI.get(userId),
    enabled: !!userId,
    staleTime: 60 * 1000,
  });
}
