import { Check } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Conversation } from "@/lib/api";
import { NOT_JOB } from "@/lib/format";
import { useAnswer } from "@/lib/mutations";
import { cn } from "@/lib/utils";

export function AnswerPanel({ conversation, onDone }: { conversation: Conversation; onDone?: () => void }) {
  const [choice, setChoice] = useState<string | null>(conversation.answer?.choice ?? null);
  const [comment, setComment] = useState(conversation.answer?.comment ?? "");
  const save = useAnswer(conversation.thread_id, onDone);
  const options = [...conversation.options.filter((o) => o !== NOT_JOB), NOT_JOB];
  return (
    <div className="space-y-3">
      {conversation.doubt && <p className="text-sm font-medium">{conversation.doubt}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => setChoice(choice === o ? null : o)}
            aria-pressed={choice === o}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-left text-xs transition-colors",
              choice === o ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-accent",
            )}
          >
            {choice === o && <Check className="size-3.5 shrink-0" />}
            {o}
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        maxLength={2000}
        placeholder="Comment for the AI (optional), for example: the company is Acme, the recruiter was Jane"
        aria-label="Comment"
        className="w-full rounded-lg border bg-card px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
      />
      <Button
        size="sm"
        disabled={save.isPending || (!choice && !comment.trim())}
        onClick={() => save.mutate({ choice, comment: comment.trim() || null })}
      >
        {save.isPending ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
