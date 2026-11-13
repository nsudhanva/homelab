import { Mail } from "lucide-react";
import type { Recruiter } from "@/lib/api";
import { label, monthYear } from "@/lib/format";

export function RecruiterCard({ recruiter: r }: { recruiter: Recruiter }) {
  return (
    <li className="rounded-lg border bg-card p-3 text-sm">
      <div className="font-medium">{r.name}</div>
      <div className="text-xs text-muted-foreground">
        {[r.title || label(r.role), r.agency && `at ${r.agency}`, label(r.via)].filter(Boolean).join(" · ")}
      </div>
      {r.email && (
        <a href={`mailto:${r.email}`} className="mt-1 inline-flex items-center gap-1 text-xs break-all text-info hover:underline">
          <Mail className="size-3.5 shrink-0" /> {r.email}
        </a>
      )}
      {r.roles.length > 0 && <div className="mt-1 text-xs text-muted-foreground">{r.roles.join(", ")}</div>}
      <div className="tabular mt-1 text-[11px] text-muted-foreground">
        {monthYear(r.first_date)} – {monthYear(r.last_date)} · {r.threads} thread{r.threads === 1 ? "" : "s"}
      </div>
    </li>
  );
}
