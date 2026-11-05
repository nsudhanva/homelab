import type { Account, State } from "./api";

const money0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const money2 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function money(value: number): string {
  return Number.isInteger(value) ? money0.format(value) : money2.format(value);
}

export function signedMoney(value: number): string {
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${money2.format(Math.abs(value))}`;
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function lastDay(endIso: string): string {
  const end = new Date(`${endIso}T00:00:00`);
  end.setDate(end.getDate() - 1);
  return end.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function relativeTime(iso: string): string {
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 90) return "just now";
  const minutes = seconds / 60;
  if (minutes < 60) return `${Math.round(minutes)}m ago`;
  const hours = minutes / 60;
  if (hours < 36) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function holderLabel(account: Account): string {
  const parts = [account.holder, account.last4 ? `•• ${account.last4}` : null].filter(Boolean);
  return parts.join(" · ") || account.name;
}

export const OPEN: State[] = ["unused", "partial", "to_activate"];
export const WAITING: State[] = ["pending"];
export const DONE: State[] = ["credited", "used", "activated", "ignored"];

export function bucket(state: State): "todo" | "pending" | "done" {
  if (OPEN.includes(state)) return "todo";
  if (WAITING.includes(state)) return "pending";
  return "done";
}

export type Urgency = "calm" | "soon" | "urgent";

export function urgency(daysLeft: number): Urgency {
  if (daysLeft <= 2) return "urgent";
  if (daysLeft <= 7) return "soon";
  return "calm";
}

export function deadlineText(daysLeft: number): string {
  if (daysLeft <= 0) return "Ends today";
  if (daysLeft === 1) return "Ends tomorrow";
  return `${daysLeft} days left`;
}

const ISSUER_ACCENT: Record<string, string> = {
  "American Express": "from-amber-400 to-yellow-600",
  Chase: "from-sky-500 to-blue-700",
  Discover: "from-orange-400 to-orange-600",
};

export function issuerAccent(issuer: string): string {
  return ISSUER_ACCENT[issuer] ?? "from-zinc-400 to-zinc-600";
}

export function shortCard(name: string): string {
  return name
    .replace(/^American Express /, "Amex ")
    .replace(/ Card$/, "")
    .replace(/^Chase /, "")
    .replace(/ Cash Back$/, "");
}
