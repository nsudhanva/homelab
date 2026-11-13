import { cn } from "@/lib/utils";

const TONE: Record<string, string> = {
  offer: "bg-success-soft text-success",
  interview: "bg-info-soft text-info",
  screening: "bg-info-soft text-info",
  rejected: "bg-destructive/10 text-destructive",
  withdrawn: "bg-muted text-muted-foreground",
  "no reply": "bg-warning-soft text-warning",
};

export function StatusBadge({ stage, outcome, noReply }: { stage: string; outcome?: string | null; noReply?: boolean }) {
  const main = noReply && !outcome ? "no reply" : stage;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Badge text={main} />
      {outcome && <Badge text={outcome} />}
    </span>
  );
}

export function Badge({ text, className }: { text: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap capitalize",
        TONE[text] ?? "bg-muted text-muted-foreground",
        className,
      )}
    >
      {text === "unknown" ? "contacted" : text}
    </span>
  );
}
