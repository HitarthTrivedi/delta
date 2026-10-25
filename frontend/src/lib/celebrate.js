import { create } from 'zustand';

// One celebration at a time, shown by <Celebration /> (mounted once in App).
// size "small": a corner card that fades out by itself (a ticked task).
// size "big": a centered moment with Aria (Quick 5 done, level up, goal met).
export const useCelebration = create((set) => ({
  current: null,
  show: (c) => set({ current: { id: Date.now(), size: 'small', ...c } }),
  clear: () => set({ current: null }),
}));

export const celebrate = (c) => useCelebration.getState().show(c);
