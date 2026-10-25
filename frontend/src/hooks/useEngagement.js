import { useQuery } from '@tanstack/react-query';
import { engagementAPI } from '../lib/api';
import { celebrate } from '../lib/celebrate';

export const engagementKey = (userId) => ['engagement', userId];

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return undefined;
  }
}

/** Streak, XP, level, today's goal: shared by the navbar chip and the Today page. */
export function useEngagement(userId) {
  return useQuery({
    queryKey: engagementKey(userId),
    queryFn: () => engagementAPI.get(userId, browserTimezone()),
    enabled: !!userId,
    staleTime: 30 * 1000,
  });
}

/**
 * Call after any learning action (task ticked, test/interview/coding done).
 * XP is awarded on the server; this refetches and celebrates only what was
 * actually earned, so the reward on screen always matches the record.
 */
export async function refreshEngagement(queryClient, userId, { size = 'small' } = {}) {
  if (!userId) return null;
  const before = queryClient.getQueryData(engagementKey(userId));
  let after;
  try {
    after = await queryClient.fetchQuery({
      queryKey: engagementKey(userId),
      queryFn: () => engagementAPI.get(userId),
      staleTime: 0,
    });
  } catch {
    return null; // rewards are a bonus: never break the action that earned them
  }
  // size "none": the caller shows its own celebration; just refresh the numbers.
  if (size !== 'none' && before && after && after.xp_total > before.xp_total) {
    const levelUp = after.level.level > before.level.level ? after.level : null;
    const goalMet = after.goal_met_today && !before.goal_met_today;
    celebrate({
      size: levelUp || goalMet ? 'big' : size,
      xp: after.xp_total - before.xp_total,
      streak: after.streak,
      streakUp: after.streak > before.streak,
      goalMet,
      levelUp,
    });
  }
  return after;
}
