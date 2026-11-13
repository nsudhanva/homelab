import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { SortTable } from "@/components/sort-table";
import { Search } from "@/components/search";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys, type Recruiter } from "@/lib/api";
import { label, monthYear } from "@/lib/format";
import { useWide } from "@/lib/media";
import { columnHelper } from "@/lib/table";

export const Route = createFileRoute("/recruiters")({
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.overview, queryFn: api.overview }),
  pendingComponent: () => <Skeleton className="h-80 rounded-xl" />,
  component: Recruiters,
});

const col = columnHelper<Recruiter>();
const columns = col.columns([
  col.accessor("name", { header: "Name", sortFn: "text", cell: (i) => <span className="font-medium whitespace-nowrap">{i.getValue()}</span> }),
  col.accessor((r) => r.email ?? "", {
    id: "email",
    header: "Email",
    sortFn: "text",
    cell: (i) =>
      i.getValue() ? (
        <a href={`mailto:${i.getValue()}`} className="break-all text-info hover:underline" onClick={(e) => e.stopPropagation()}>
          {i.getValue()}
        </a>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  }),
  col.accessor((r) => r.title || label(r.role), { id: "title", header: "Title", sortFn: "text" }),
  col.accessor("company", {
    header: "Company",
    sortFn: "text",
    cell: (i) => (
      <Link to="/companies/$key" params={{ key: i.row.original.company_key }} className="whitespace-nowrap hover:underline">
        {i.getValue()}
      </Link>
    ),
  }),
  col.accessor((r) => r.agency ?? "", { id: "agency", header: "Agency", sortFn: "text" }),
  col.accessor((r) => r.roles.join(", "), {
    id: "roles",
    header: "Roles",
    sortFn: "text",
    cell: (i) => <span className="line-clamp-2 max-w-60 text-muted-foreground">{i.getValue() || "—"}</span>,
  }),
  col.accessor("last_date", {
    header: "Last contact",
    cell: (i) => <span className="tabular whitespace-nowrap text-muted-foreground">{monthYear(i.getValue())}</span>,
  }),
  col.accessor("threads", { header: "Threads", cell: (i) => <span className="tabular">{i.getValue()}</span> }),
  col.accessor((r) => label(r.via), { id: "via", header: "Source", sortFn: "text" }),
]);

function Recruiters() {
  const { data } = useQuery({ queryKey: keys.overview, queryFn: api.overview });
  const wide = useWide();
  const [query, setQuery] = useState("");
  const companies = data?.companies;
  const all = useMemo(() => (companies ?? []).flatMap((c) => c.recruiters), [companies]);
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return all;
    return all.filter((r) =>
      [r.name, r.email ?? "", r.title ?? "", r.company, r.agency ?? "", ...r.roles].some((s) => s.toLowerCase().includes(q)),
    );
  }, [all, query]);
  if (!data) return null;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Recruiters</h1>
        <p className="text-sm text-muted-foreground">
          {all.length} people from {data.companies.filter((c) => c.recruiters.length).length} companies.
        </p>
      </div>
      <Search value={query} onChange={setQuery} placeholder="Search name, email, company, or role" />
      {wide ? (
        <SortTable data={rows} columns={columns} sorting={[{ id: "last_date", desc: true }]} rowKey={(r) => r.key} />
      ) : (
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.key}>
            <Card className="gap-1 px-4 py-3 text-sm">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-medium">{r.name}</span>
                <span className="tabular text-xs text-muted-foreground">{monthYear(r.last_date)}</span>
              </div>
              <Link to="/companies/$key" params={{ key: r.company_key }} className="text-xs hover:underline">
                {[r.title || label(r.role), r.company, r.agency && `via ${r.agency}`].filter(Boolean).join(" · ")}
              </Link>
              {r.email && (
                <a href={`mailto:${r.email}`} className="text-xs break-all text-info">
                  {r.email}
                </a>
              )}
              {r.roles.length > 0 && <div className="text-xs text-muted-foreground">{r.roles.join(", ")}</div>}
            </Card>
          </li>
        ))}
        {rows.length === 0 && <p className="py-10 text-center text-sm text-muted-foreground">Nothing matches.</p>}
      </ul>
      )}
    </div>
  );
}
