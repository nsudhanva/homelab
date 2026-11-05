import { Check, Clock3, KeyRound, Minus, X } from "lucide-react";
import type { Cell } from "@/lib/api";
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";

export type Look =
  | "used"
  | "partial"
  | "open"
  | "missed"
  | "unknown"
  | "pending"
  | "skipped"
  | "activate"
  | "none";

export function look(cell: Cell): Look {
  switch (cell.state) {
    case "credited":
    case "used":
    case "activated":
      return "used";
    case "partial":
      return cell.current ? "partial" : cell.remaining > 0 ? "partial" : "used";
    case "pending":
      return "pending";
    case "ignored":
      return "skipped";
    case "to_activate":
      return cell.current ? "activate" : "unknown";
    case "unused":
      if (cell.current) return "open";
      return cell.data_from ? "unknown" : "missed";
    default:
      return "none";
  }
}

export const LOOK_LABEL: Record<Look, string> = {
  used: "Used",
  partial: "Partly used",
  open: "Open",
  missed: "Missed",
  unknown: "Before your data",
  pending: "Awaiting credit",
  skipped: "Skipped",
  activate: "Activate",
  none: "No data",
};

export function Mark({ look: l, fraction = 0, size = "md" }: { look: Look; fraction?: number; size?: "sm" | "md" }) {
  const box = size === "sm" ? "size-5" : "size-8";
  const icon = size === "sm" ? "size-3" : "size-4";
  if (l === "used")
    return (
      <span className={cn(box, "grid place-items-center rounded-full bg-success text-white shadow-sm shadow-success/30")}>
        <Check className={icon} strokeWidth={3} />
      </span>
    );
  if (l === "partial")
    return (
      <span
        className={cn(box, "rounded-full ring-2 ring-warning ring-inset")}
        style={{
          background: `conic-gradient(var(--warning) ${Math.round(fraction * 360)}deg, transparent 0)`,
        }}
      />
    );
  if (l === "open")
    return <span className={cn(box, "rounded-full border-2 border-dashed border-muted-foreground/45")} />;
  if (l === "missed")
    return (
      <span className={cn(box, "grid place-items-center rounded-full bg-destructive/10 text-destructive ring-2 ring-destructive/40 ring-inset")}>
        <X className={icon} strokeWidth={2.5} />
      </span>
    );
  if (l === "unknown")
    return (
      <span className={cn(box, "grid place-items-center rounded-full border-2 border-dotted border-muted-foreground/40 text-muted-foreground")}>
        <span className={size === "sm" ? "text-[10px]" : "text-xs"}>?</span>
      </span>
    );
  if (l === "pending")
    return (
      <span className={cn(box, "grid place-items-center rounded-full bg-info-soft text-info")}>
        <Clock3 className={icon} strokeWidth={2.5} />
      </span>
    );
  if (l === "skipped")
    return (
      <span className={cn(box, "grid place-items-center rounded-full bg-muted text-muted-foreground")}>
        <Minus className={icon} strokeWidth={2.5} />
      </span>
    );
  if (l === "activate")
    return (
      <span className={cn(box, "grid place-items-center rounded-full bg-warning-soft text-warning")}>
        <KeyRound className={icon} strokeWidth={2.5} />
      </span>
    );
  return <span className="size-1.5 rounded-full bg-muted-foreground/25" />;
}

export function CellCaption({ cell, l }: { cell: Cell; l: Look }) {
  if (l === "none") return null;
  let text = "";
  let tone = "text-muted-foreground";
  if (l === "used") {
    text = cell.captured ? money(cell.captured) : "Done";
    tone = "text-success";
  } else if (l === "partial") {
    text = money(cell.captured);
    tone = "text-warning";
  } else if (l === "open") {
    text = cell.days_left !== null && cell.days_left <= 7 ? `${cell.days_left}d left` : money(cell.remaining);
    if (cell.days_left !== null && cell.days_left <= 7) tone = "text-warning font-semibold";
  } else if (l === "missed") {
    text = money(cell.remaining || cell.value);
    tone = "text-destructive/80";
  } else if (l === "unknown") text = "no data";
  else if (l === "pending") text = "pending";
  else if (l === "skipped") text = "skipped";
  else if (l === "activate") text = "activate";
  return <span className={cn("tabular text-[11px] leading-none", tone)}>{text}</span>;
}
