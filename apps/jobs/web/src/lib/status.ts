import type { Company } from "@/lib/api";

export const STATUSES = [
  { id: "all", label: "All" },
  { id: "outreach", label: "Outreach" },
  { id: "applied", label: "Applied" },
  { id: "screening", label: "Screening" },
  { id: "interview", label: "Interview" },
  { id: "offer", label: "Offer" },
  { id: "rejected", label: "Rejected" },
  { id: "withdrawn", label: "Withdrawn" },
  { id: "no_reply", label: "No reply" },
] as const;

export type StatusId = (typeof STATUSES)[number]["id"];

const IDS = new Set<string>(STATUSES.map((s) => s.id));

export function parseStatus(value: unknown): StatusId {
  return typeof value === "string" && IDS.has(value) ? (value as StatusId) : "all";
}

export function hasStatus(c: Company, status: StatusId): boolean {
  if (status === "all") return true;
  if (status === "no_reply") return c.no_reply;
  if (status === "rejected" || status === "withdrawn") return c.outcome === status;
  return c.stage === status;
}

export function statusWords(c: Company): string[] {
  const words = [c.stage === "unknown" ? "contacted" : c.stage, c.status];
  if (c.outcome) words.push(c.outcome);
  if (c.no_reply) words.push("no reply");
  return words;
}

export function statusCounts<T>(items: T[], company: (item: T) => Company): Record<StatusId, number> {
  const counts = Object.fromEntries(STATUSES.map((s) => [s.id, 0])) as Record<StatusId, number>;
  for (const item of items) {
    for (const s of STATUSES) if (hasStatus(company(item), s.id)) counts[s.id] += 1;
  }
  return counts;
}
