import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { ChevronRight, Download } from "lucide-react";
import { useMemo, useState } from "react";
import { RecruiterCard } from "@/components/recruiter-card";
import { SortTable } from "@/components/sort-table";
import { Chips, Search } from "@/components/search";
import { StatusBadge } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EXPORT_URL, api, keys, type Company, type Recruiter } from "@/lib/api";
import { monthYear } from "@/lib/format";
import { useWide } from "@/lib/media";
import { STATUSES, hasStatus, parseStatus, statusCounts, statusWords, type StatusId } from "@/lib/status";
import { columnHelper } from "@/lib/table";

type CompanySearch = { q?: string; status?: StatusId; recruiter?: boolean };

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): CompanySearch => ({
    q: typeof search.q === "string" && search.q ? search.q : undefined,
    status: parseStatus(search.status) === "all" ? undefined : parseStatus(search.status),
    recruiter: search.recruiter === true || search.recruiter === "true" ? true : undefined,
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.overview, queryFn: api.overview }),
  pendingComponent: () => <Skeleton className="h-80 rounded-xl" />,
  component: Companies,
});

function matches(c: Company, q: string): boolean {
  if (!q) return true;
  const hay = [
    c.name,
    ...c.roles,
    ...c.agencies,
    ...statusWords(c),
    ...c.recruiters.flatMap((r) => [r.name, r.email ?? ""]),
  ];
  return hay.some((s) => s.toLowerCase().includes(q));
}

const col = columnHelper<Company>();
const columns = col.columns([
  col.accessor("name", {
    header: "Company",
    sortFn: "text",
    cell: (info) => <span className="font-medium">{info.getValue()}</span>,
  }),
  col.accessor((c) => c.recruiters.length, {
    id: "recruiters",
    header: "Recruiters",
    cell: (info) => <Names recruiters={info.row.original.recruiters} />,
  }),
  col.accessor((c) => c.roles.join(", "), {
    id: "roles",
    header: "Roles",
    sortFn: "text",
    cell: (info) => <span className="line-clamp-2 max-w-64 text-muted-foreground">{info.getValue() || "—"}</span>,
  }),
  col.accessor("status", {
    header: "Status",
    sortFn: "text",
    cell: (info) => {
      const c = info.row.original;
      return <StatusBadge stage={c.stage} outcome={c.outcome} noReply={c.no_reply} />;
    },
  }),
  col.accessor("first_date", { header: "First", cell: (info) => <Date value={info.getValue()} /> }),
  col.accessor("last_date", { header: "Last", cell: (info) => <Date value={info.getValue()} /> }),
  col.accessor("conversations", {
    header: "Threads",
    cell: (info) => <span className="tabular">{info.getValue()}</span>,
  }),
]);

function Date({ value }: { value: string }) {
  return <span className="tabular whitespace-nowrap text-muted-foreground">{monthYear(value)}</span>;
}

function Names({ recruiters }: { recruiters: Recruiter[] }) {
  if (!recruiters.length) return <span className="text-muted-foreground">—</span>;
  const shown = recruiters.slice(0, 2).map((r) => r.name).join(", ");
  return (
    <span className="line-clamp-2 max-w-56">
      {shown}
      {recruiters.length > 2 && <span className="text-muted-foreground"> +{recruiters.length - 2}</span>}
    </span>
  );
}

function Companies() {
  const { data } = useQuery({ queryKey: keys.overview, queryFn: api.overview });
  const wide = useWide();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const query = search.q ?? "";
  const status = search.status ?? "all";
  const recruiterOnly = search.recruiter ?? false;
  const update = (next: CompanySearch) =>
    navigate({ search: (prev) => ({ ...prev, ...next }), replace: true });
  const [open, setOpen] = useState<string | null>(null);
  const companies = data?.companies;
  const pool = useMemo(
    () => (companies ?? []).filter((c) => !recruiterOnly || c.recruiters.length > 0),
    [companies, recruiterOnly],
  );
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return pool.filter((c) => hasStatus(c, status) && matches(c, q));
  }, [pool, query, status]);
  const counts = useMemo(() => statusCounts(pool, (c) => c), [pool]);
  if (!data) return null;
  const t = data.totals;
  const toggle = (c: Company) => setOpen(open === c.key ? null : c.key);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Companies</h1>
          <p className="text-sm text-muted-foreground">Every company that contacted you or that you applied to, from Gmail.</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <a href={EXPORT_URL} download>
            <Download className="size-4" /> Download Excel
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Stat label="Companies" value={t.companies} />
        <Stat label="Recruiters" value={t.recruiters} />
        <Stat label="Conversations" value={t.conversations} />
        <Stat label="No reply" value={t.no_reply} />
        <Link to="/questions" className="col-span-2 sm:col-span-1">
          <Stat label="Open questions" value={t.open_questions} highlight={t.open_questions > 0} />
        </Link>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Search
            value={query}
            onChange={(q) => update({ q: q || undefined })}
            placeholder="Search company, recruiter, email, role, or status"
          />
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={recruiterOnly}
              onChange={(e) => update({ recruiter: e.target.checked || undefined })}
              className="size-4 accent-foreground"
            />
            Only companies with a recruiter
          </label>
        </div>
        <Chips
          value={status}
          onChange={(s) => update({ status: s === "all" ? undefined : s })}
          options={STATUSES.map((s) => ({ id: s.id, label: s.label, count: counts[s.id] }))}
        />
        <p className="text-xs text-muted-foreground">
          {rows.length} of {data.companies.length} companies
        </p>
      </div>

      {wide ? (
        <SortTable
          data={rows}
          columns={columns}
          sorting={[{ id: "last_date", desc: true }]}
          rowKey={(c) => c.key}
          expanded={open}
          onRowClick={toggle}
          renderExpanded={(c) => <Details company={c} />}
        />
      ) : (
      <ul className="space-y-2">
        {rows.map((c) => (
          <li key={c.key}>
            <Card className="gap-0 py-0">
              <button type="button" onClick={() => toggle(c)} className="w-full space-y-1.5 px-4 py-3 text-left">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium">{c.name}</span>
                  <StatusBadge stage={c.stage} outcome={c.outcome} noReply={c.no_reply} />
                </div>
                {c.recruiters.length > 0 && <Names recruiters={c.recruiters} />}
                <div className="line-clamp-1 text-xs text-muted-foreground">{c.roles.join(", ") || "No role named"}</div>
                <div className="tabular text-xs text-muted-foreground">
                  {monthYear(c.first_date)} – {monthYear(c.last_date)} · {c.conversations} thread{c.conversations === 1 ? "" : "s"}
                </div>
              </button>
              {open === c.key && (
                <div className="border-t bg-muted/40 px-4 py-3">
                  <Details company={c} />
                </div>
              )}
            </Card>
          </li>
        ))}
        {rows.length === 0 && <p className="py-10 text-center text-sm text-muted-foreground">Nothing matches.</p>}
      </ul>
      )}
    </div>
  );
}

function Stat({ label: name, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <Card className="gap-0 px-4 py-3">
      <div className="text-xs text-muted-foreground">{name}</div>
      <div className={highlight ? "tabular text-xl font-semibold text-warning" : "tabular text-xl font-semibold"}>{value}</div>
    </Card>
  );
}

function Details({ company }: { company: Company }) {
  return (
    <div className="space-y-3">
      {company.recruiters.length === 0 ? (
        <p className="text-sm text-muted-foreground">No named recruiter. The threads came from a hiring tool or a team address.</p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2">
          {company.recruiters.map((r) => (
            <RecruiterCard key={r.key} recruiter={r} />
          ))}
        </ul>
      )}
      {company.agencies.length > 0 && (
        <p className="text-xs text-muted-foreground">Through agencies: {company.agencies.join(", ")}</p>
      )}
      <Link
        to="/companies/$key"
        params={{ key: company.key }}
        className="inline-flex items-center gap-1 text-sm font-medium hover:underline"
      >
        Conversations{company.open_questions > 0 && ` (${company.open_questions} open question${company.open_questions === 1 ? "" : "s"})`}
        <ChevronRight className="size-4" />
      </Link>
    </div>
  );
}
