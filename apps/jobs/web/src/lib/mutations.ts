import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, keys, type AnswerBody } from "@/lib/api";

export function useAnswer(threadId: string, onDone?: () => void) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: AnswerBody) => api.answer(threadId, body),
    onSuccess: (result) => {
      toast.success(result.applied ? "Saved — AI updated" : "Saved — applied at next sync");
      onDone?.();
    },
    onError: () => toast.error("Could not save. Try again."),
    onSettled: () => client.invalidateQueries({ queryKey: keys.all }),
  });
}

export function useRename(key: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.rename(key, name),
    onSuccess: () => toast.success("Company name saved"),
    onError: () => toast.error("Could not save. Try again."),
    onSettled: () => client.invalidateQueries({ queryKey: keys.all }),
  });
}
