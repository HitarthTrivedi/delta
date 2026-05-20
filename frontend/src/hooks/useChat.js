import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '../lib/api';

export function useChatHistory(userId) {
  return useQuery({
    queryKey: ['chatHistory', userId],
    queryFn: () => chatAPI.getHistory(userId),
    enabled: !!userId,
    staleTime: 10000,
  });
}

export function useSendMessage(userId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (message) => chatAPI.send({ user_id: userId, message }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatHistory', userId] });
    },
  });
}
