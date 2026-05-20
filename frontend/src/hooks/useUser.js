import { useQuery } from '@tanstack/react-query';
import { usersAPI } from '../lib/api';

export function useUserWithSkills(userId) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => usersAPI.getWithSkills(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useUserStats(userId) {
  return useQuery({
    queryKey: ['userStats', userId],
    queryFn: () => usersAPI.getStats(userId),
    enabled: !!userId,
    staleTime: 30000,
    select: (data) => ({
      role_alignment: data.role_alignment || 0,
      evidence_density: data.evidence_density || 0,
      market_pulse: data.market_pulse || 'N/A',
      gaps: data.gaps || [],
    }),
  });
}
