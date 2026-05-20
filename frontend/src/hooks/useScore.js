import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { briefsAPI } from '../lib/api';

export function useCurrentScore(userId) {
  return useQuery({
    queryKey: ['currentScore', userId],
    queryFn: () => briefsAPI.getCurrentScore(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useScoreHistory(userId) {
  return useQuery({
    queryKey: ['scoreHistory', userId],
    queryFn: () => briefsAPI.getScoreHistory(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useLatestBrief(userId) {
  return useQuery({
    queryKey: ['latestBrief', userId],
    queryFn: () => briefsAPI.getLatest(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useCompleteRecommendation(userId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recId, evidenceUrl, evidenceType }) =>
      briefsAPI.completeRecommendation(recId, {
        evidence_url: evidenceUrl,
        evidence_type: evidenceType,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latestBrief', userId] });
      queryClient.invalidateQueries({ queryKey: ['currentScore', userId] });
      queryClient.invalidateQueries({ queryKey: ['scoreHistory', userId] });
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      queryClient.invalidateQueries({ queryKey: ['userStats', userId] });
    },
  });
}
