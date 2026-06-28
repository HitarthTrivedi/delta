import { useQuery } from '@tanstack/react-query';
import { careerOSAPI } from '../lib/api';

// Shared query key so the (heavy) career context is fetched once and reused
// across Dashboard / CareerChat / ProgressReport / WeeklyPlan.
export const careerContextKey = (userId) => ['careerContext', userId];

// Read-through cache: returns the cached context if still fresh (global
// staleTime), otherwise fetches and caches it. Use in imperative loaders.
export function fetchCareerContext(queryClient, userId) {
  return queryClient.fetchQuery({
    queryKey: careerContextKey(userId),
    queryFn: () => careerOSAPI.getContext(userId),
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
  });
}
