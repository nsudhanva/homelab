import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { ConversationCard } from "@/components/conversation-card";
import { RecruiterCard } from "@/components/recruiter-card";
import { StatusBadge } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys } from "@/lib/api";
import { monthYear } from "@/lib/format";
import { useRename } from "@/lib/mutations";

export const Route = createFileRoute("/companies/$key")({
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData({ queryKey: keys.company(params.key), queryFn: () => api.company(params.key) }),
  pendingComponent: () => <Skeleton className="h-80 rounded-xl" />,
  errorComponent: () => (
    <p className="py-10 text-center text-sm text-muted-foreground">
      This company is not in the list any more. It may have been renamed. <Link to="/" className="underline">Back to companies</Link>
    </p>
  ),
  component: CompanyPage,
});

function CompanyPage() {
  const { key } = Route.useParams();
  const { data } = useQuery({ queryKey: keys.company(key), queryFn: () => api.company(key) });
  if (!data) return null;
  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Companies
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{data.name}</h1>
          <p className="tabular text-sm text-muted-foreground">
            {monthYear(data.first_date)} – {monthYear(data.last_date)} · {data.conversations} thread{data.conversations === 1 ? "" : "s"}
            {data.roles.length > 0 && ` · ${data.roles.join(", ")}`}
          </p>
        </div>
        <StatusBadge stage={data.stage} outcome={data.outcome} noReply={data.no_reply} />
      </div>

      <Rename companyKey={data.key} current={data.name} />

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Recruiters</h2>
        {data.recruiters.length === 0 ? (
          <p className="text-sm text-muted-foreground">No named recruiter.</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.recruiters.map((r) => (
              <RecruiterCard key={r.key} recruiter={r} />
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Conversations</h2>
        <ul className="space-y-2">
          {data.conversation_list.map((c) => (
            <ConversationCard key={c.thread_id} conversation={c} />
          ))}
        </ul>
      </section>
    </div>
  );
}

function Rename({ companyKey, current }: { companyKey: string; current: string }) {
  const [name, setName] = useState(current);
  const rename = useRename(companyKey);
  return (
    <form
      className="flex max-w-md items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        rename.mutate(name.trim());
      }}
    >
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        aria-label="Company name"
        maxLength={200}
        className="h-9 flex-1 rounded-lg border bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      <Button type="submit" size="sm" variant="outline" disabled={rename.isPending || name.trim() === current}>
        Rename
      </Button>
    </form>
  );
}
