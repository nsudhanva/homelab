import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowLeft, Bot, Check, Hand, RotateCcw, ScrollText, SkipForward } from "lucide-react";
import { Mark, type Look } from "@/components/cell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys, type Evidence, type OfferStatus } from "@/lib/api";
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

const LABEL: Record<OfferStatus["state"], string> = {
  credited: "Credited",
  used: "Used",
  activated: "Activated",
  partial: "Partly used",
  pending: "Awaiting credit",
  unused: "Not used",
  ignored: "Not interested",
  to_activate: "Not activated",
};

function lookOf(status: OfferStatus): Look {
  switch (status.state) {
    case "credited":
    case "used":
    case "activated":
      return "used";
    case "partial":
      return "partial";
    case "pending":
      return "pending";
    case "ignored":
      return "skipped";
    case "to_activate":
      return "activate";
    default:
      return status.period.days_left > 0 ? "open" : "missed";
  }
}

function OfferPage() {
  const { offerId, accountId } = Route.useParams();
  const { data } = useQuery({ queryKey: keys.offer(offerId, accountId), queryFn: () => api.offer(offerId, accountId) });
  if (!data) return null;
  const current = data.history[0]?.status;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
        <Link to="/">
          <ArrowLeft className="size-4" /> Tracker
        </Link>
      </Button>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{data.name}</h1>
        <p className="text-sm text-muted-foreground">
          {shortCard(data.card_name)} · {holderLabel(data.account)}
          {data.value > 0 && ` · ${money(data.value)} each ${data.period.replace("_", " ")} period`}
        </p>
      </div>
      <p className="rounded-lg border bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground">{data.cycle}</p>
      {current?.how_to_use && (
        <Card className="gap-0 py-0">
          <CardContent className="p-4 text-sm text-muted-foreground">{current.how_to_use}</CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        Offers decides each period from your transactions. Correct a period only if it is wrong, for example when an
        in-app credit paid an order in full and no card transaction shows it.
      </p>

      <Card className="gap-0 overflow-hidden py-0">
        <ul className="divide-y">
          {data.history.map(({ status, evidence }) => (
            <PeriodRow key={status.period.start} status={status} evidence={evidence} name={data.name} />
          ))}
        </ul>
      </Card>
    </div>
  );
}

function PeriodRow({ status, evidence, name }: { status: OfferStatus; evidence: Evidence[]; name: string }) {
  const override = useOverride();
  const body = { offer_id: status.offer_id, account_id: status.account.id, period_start: status.period.start };
  const fraction = status.value ? status.captured / status.value : 0;
  const activation = status.kind === "activation";
  return (
    <li className="space-y-2 px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-center gap-3">
        <Mark look={lookOf(status)} fraction={fraction} />
        <div className="min-w-0 flex-1">
          <div className="font-medium">{status.period.label}</div>
          <div className="text-xs text-muted-foreground">
            {LABEL[status.state]}
            {status.captured > 0 && ` · ${money(status.captured)} captured`}
            {status.remaining > 0 && ` · ${money(status.remaining)} ${status.period.days_left > 0 ? "left" : "not used"}`}
            {status.override && " · corrected by you"}
          </div>
        </div>
        <div className="flex gap-1.5">
          {status.override ? (
            <Button
              variant="outline"
              size="sm"
              disabled={override.pending}
              onClick={() => override.set({ ...body, status: null }, name, status.period.label)}
            >
              <RotateCcw className="size-4" /> Undo
            </Button>
          ) : (
            ["unused", "partial", "pending", "to_activate"].includes(status.state) && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={override.pending}
                  onClick={() => override.set({ ...body, status: "used" }, name, status.period.label)}
                >
                  <Check className="size-4" /> {activation ? "I activated it" : "I used it"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={override.pending}
                  onClick={() => override.set({ ...body, status: "ignored" }, name, status.period.label)}
                >
                  <SkipForward className="size-4" /> Not interested
                </Button>
              </>
            )
          )}
        </div>
      </div>
      {evidence.length > 0 && (
        <ul className="ml-11 space-y-1">
          {evidence.map((e, i) => (
            <EvidenceLine key={i} evidence={e} />
          ))}
        </ul>
      )}
    </li>
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
