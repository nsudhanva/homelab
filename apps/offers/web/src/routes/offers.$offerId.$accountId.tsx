import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowLeft, Bot, Hand, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateChip, StateIcon } from "@/components/state";
import { api, keys, type Evidence } from "@/lib/api";
import { holderLabel, money, shortCard, shortDate, signedMoney } from "@/lib/format";
import { useOverride } from "@/lib/mutations";

export const Route = createFileRoute("/offers/$offerId/$accountId")({
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData({
      queryKey: keys.offer(params.offerId, params.accountId),
      queryFn: () => api.offer(params.offerId, params.accountId),
    }),
  pendingComponent: () => <Skeleton className="h-80 rounded-xl" />,
  errorComponent: () => <p className="text-sm text-muted-foreground">This offer is not available.</p>,
  component: OfferPage,
});

const SOURCE = {
  rule: { icon: ScrollText, label: "Rule" },
  ai: { icon: Bot, label: "AI" },
  manual: { icon: Hand, label: "You" },
} as const;

function OfferPage() {
  const { offerId, accountId } = Route.useParams();
  const setOverride = useOverride();
  const { data } = useQuery({ queryKey: keys.offer(offerId, accountId), queryFn: () => api.offer(offerId, accountId) });
  if (!data) return null;
  const current = data.history[0]?.status;

  return (
    <div className="space-y-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
        <Link to="/">
          <ArrowLeft className="size-4" /> Back
        </Link>
      </Button>

      <div className="flex items-start gap-3">
        {current && <StateIcon state={current.state} className="mt-1" />}
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight">{data.name}</h1>
          <p className="text-sm text-muted-foreground">
            {shortCard(data.card_name)} · {holderLabel(data.account)}
            {data.value > 0 && ` · ${money(data.value)} each ${data.period.replace("_", " ")} period`}
          </p>
        </div>
      </div>
      {current?.how_to_use && (
        <Card className="gap-0 py-0">
          <CardContent className="p-4 text-sm text-muted-foreground">{current.how_to_use}</CardContent>
        </Card>
      )}

      <section className="space-y-2">
        <h2 className="px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">History</h2>
        <Card className="gap-0 overflow-hidden py-0">
          <ul className="divide-y">
            {data.history.map(({ status, evidence }) => (
              <li key={status.period.start} className="space-y-2 px-4 py-3.5 sm:px-5">
                <div className="flex items-center gap-3">
                  <StateIcon state={status.state} className="size-6" />
                  <div className="flex-1">
                    <div className="text-sm font-medium">{status.period.label}</div>
                    {status.captured > 0 && (
                      <div className="tabular text-xs text-success">{money(status.captured)} captured</div>
                    )}
                  </div>
                  <StateChip state={status.state} />
                  {status.override && (
                    <Button variant="ghost" size="sm" onClick={() => setOverride(status, null)}>
                      Undo
                    </Button>
                  )}
                </div>
                {evidence.length > 0 && (
                  <ul className="ml-9 space-y-1">
                    {evidence.map((e, i) => (
                      <EvidenceLine key={i} evidence={e} />
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </section>
    </div>
  );
}

function EvidenceLine({ evidence }: { evidence: Evidence }) {
  const source = SOURCE[evidence.source];
  const Icon = source.icon;
  const txn = evidence.txn;
  return (
    <li className="flex items-center gap-2 text-xs text-muted-foreground">
      <Icon className="size-3.5 shrink-0" aria-label={source.label} />
      <span className="tabular w-12 shrink-0">{txn ? shortDate(txn.date) : ""}</span>
      <span className="min-w-0 flex-1 truncate">
        {evidence.kind === "credit" ? "Credit" : "Purchase"} · {txn?.payee || txn?.description}
      </span>
      <span className={evidence.kind === "credit" ? "tabular text-success" : "tabular"}>
        {txn ? signedMoney(txn.amount) : money(evidence.amount)}
      </span>
    </li>
  );
}
