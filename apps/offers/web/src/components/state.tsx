import { BadgeCheck, CircleCheck, CircleDashed, CircleMinus, Circle, Clock3, KeyRound } from "lucide-react";
import type { ComponentType } from "react";
import type { State } from "@/lib/api";
import { cn } from "@/lib/utils";

type Meta = {
  label: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  tone: string;
  chip: string;
};

export const STATE: Record<State, Meta> = {
  credited: {
    label: "Credited",
    icon: BadgeCheck,
    tone: "text-success",
    chip: "bg-success-soft text-success",
  },
  used: { label: "Used", icon: CircleCheck, tone: "text-success", chip: "bg-success-soft text-success" },
  activated: {
    label: "Activated",
    icon: CircleCheck,
    tone: "text-success",
    chip: "bg-success-soft text-success",
  },
  partial: {
    label: "Part used",
    icon: CircleDashed,
    tone: "text-warning",
    chip: "bg-warning-soft text-warning",
  },
  pending: {
    label: "Awaiting credit",
    icon: Clock3,
    tone: "text-info",
    chip: "bg-info-soft text-info",
  },
  unused: { label: "Unused", icon: Circle, tone: "text-muted-foreground", chip: "bg-muted text-muted-foreground" },
  ignored: {
    label: "Skipped",
    icon: CircleMinus,
    tone: "text-muted-foreground/70",
    chip: "bg-muted text-muted-foreground",
  },
  to_activate: {
    label: "Activation needed",
    icon: KeyRound,
    tone: "text-warning",
    chip: "bg-warning-soft text-warning",
  },
};

const FILLED: State[] = ["credited", "used", "activated"];

export function StateIcon({ state, className }: { state: State; className?: string }) {
  const meta = STATE[state];
  const Icon = meta.icon;
  if (FILLED.includes(state)) {
    return (
      <span
        className={cn("grid size-7 shrink-0 place-items-center rounded-full bg-success text-background", className)}
        aria-hidden
      >
        <Icon className="size-4" strokeWidth={2.75} />
      </span>
    );
  }
  return <Icon className={cn("size-7 shrink-0", meta.tone, className)} strokeWidth={1.75} aria-hidden />;
}

export function StateChip({ state, className }: { state: State; className?: string }) {
  const meta = STATE[state];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap",
        meta.chip,
        className,
      )}
    >
      {meta.label}
    </span>
  );
}

export function UsePips({ uses, used }: { uses: number; used: number }) {
  return (
    <span className="inline-flex gap-1" aria-label={`${used} of ${uses} used`}>
      {Array.from({ length: uses }, (_, i) => (
        <span
          key={i}
          className={cn("h-1.5 w-4 rounded-full", i < used ? "bg-success" : "bg-muted-foreground/25")}
        />
      ))}
    </span>
  );
}
