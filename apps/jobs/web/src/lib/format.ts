const MONTH = new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" });
const DAY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

export function monthYear(iso: string | null | undefined): string {
  return iso ? MONTH.format(new Date(iso)) : "—";
}

export function longDate(iso: string | null | undefined): string {
  return iso ? DAY.format(new Date(iso)) : "—";
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

const LABELS: Record<string, string> = {
  recruiter_outreach: "Outreach",
  application: "Application",
  interview_scheduling: "Scheduling",
  interview: "Interview",
  assessment: "Assessment",
  offer: "Offer",
  rejection: "Rejection",
  follow_up: "Follow-up",
  referral: "Referral",
  job_alert: "Job alert",
  owner_hiring: "You hiring",
  not_job: "Not a job",
  hiring_tool: "Hiring tool",
  linkedin: "LinkedIn",
  email: "Email",
  hiring_manager: "Hiring manager",
};

export function label(value: string): string {
  return LABELS[value] ?? value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

export const NOT_JOB = "Not a job contact";
