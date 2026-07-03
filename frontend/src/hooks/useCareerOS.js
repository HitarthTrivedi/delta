import { useQuery } from '@tanstack/react-query';
import { careerOSAPI } from '../lib/api';

// Shared query key so the (heavy) career context is fetched once and reused
// across Dashboard / CareerChat / ProgressReport / WeeklyPlan.
export const careerContextKey = (userId) => ['careerContext', userId];

// The context endpoint aggregates the whole engine (memory, market, roadmap,
// external opportunity feeds) — keep it fresh well beyond the 60s global
// default so page navigation doesn't re-trigger the expensive compile.
// Mutations (weekly cycle, task updates) seed the cache directly instead.
const CONTEXT_STALE_TIME = 5 * 60 * 1000;

// Read-through cache: returns the cached context if still fresh, otherwise
// fetches and caches it. Use in imperative loaders.
export function fetchCareerContext(queryClient, userId) {
  return queryClient.fetchQuery({
    queryKey: careerContextKey(userId),
    queryFn: () => careerOSAPI.getContext(userId),
    staleTime: CONTEXT_STALE_TIME,
  });
}

// Write-through: call after any FRESH imperative fetch (refresh / post-action /
// weekly cycle / consolidate) so the shared cache reflects the latest data.
export function seedCareerContext(queryClient, userId, data) {
  if (data) queryClient.setQueryData(careerContextKey(userId), data);
}

// Declarative hook for components that prefer it.
export function useCareerContext(userId) {
  return useQuery({
    queryKey: careerContextKey(userId),
    queryFn: () => careerOSAPI.getContext(userId),
    enabled: !!userId,
    staleTime: CONTEXT_STALE_TIME,
  });
}
