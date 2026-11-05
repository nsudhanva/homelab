import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { StateIcon } from "@/components/state";
import { api, keys } from "@/lib/api";
import { holderLabel, issuerAccent, money, shortCard, shortDate, signedMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/cards")({
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.dashboard(), queryFn: () => api.dashboard() }),
  pendingComponent: () => <Skeleton className="h-60 rounded-xl" />,
  component: Cards,
});

function Cards() {
  const { data } = useQuery({ queryKey: keys.dashboard(), queryFn: () => api.dashboard() });
  if (!data) return null;
  const year = new Date(`${data.today}T00:00:00`).getFullYear();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Cards</h1>
        <p className="text-sm text-muted-foreground">
          Tracked credits captured in {year}, compared with each card's annual fee.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {data.cards.map((card) => {
          const coverage = card.annual_fee ? (card.year_captured / card.annual_fee) * 100 : 0;
          return (
            <Card key={`${card.card_id}:${card.account.id}`} className="gap-0 overflow-hidden py-0">
              <div className={cn("h-1.5 bg-gradient-to-r", issuerAccent(card.issuer))} />
              <CardContent className="space-y-4 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{shortCard(card.name)}</div>
                    <div className="text-xs text-muted-foreground">{holderLabel(card.account)}</div>
                  </div>
                  {card.annual_fee > 0 && (
                    <div className="text-right text-xs text-muted-foreground">
                      Annual fee
                      <div className="tabular text-sm font-medium text-foreground">{money(card.annual_fee)}</div>
                    </div>
                  )}
                </div>

                {card.annual_fee > 0 ? (
                  <div className="space-y-1.5">
                    <div className="flex items-baseline justify-between">
                      <span className="tabular text-2xl font-semibold text-success">{money(card.year_captured)}</span>
                      <span className="tabular text-xs text-muted-foreground">
                        {Math.round(coverage)}% of the fee
                      </span>
                    </div>
                    <Progress value={Math.min(100, coverage)} className="h-2" />
                    <div className="text-xs text-muted-foreground">
                      <span className="tabular text-warning">{money(card.year_missed)}</span> missed in finished
                      periods
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">No annual fee.</div>
                )}

                <div className="flex flex-wrap gap-1.5">
                  {card.offers.map((o) => (
                    <span
                      key={o.offer_id}
                      title={o.name}
                      className="inline-flex items-center gap-1.5 rounded-full border py-0.5 pr-2.5 pl-0.5 text-xs"
                    >
                      <StateIcon state={o.state} className="size-5" />
                      {o.name}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Credits not linked to an offer</h2>
        <p className="text-xs text-muted-foreground">
          Some are refunds. A credit that repeats can be an offer to add to the catalog.
        </p>
        {data.unlinked.length === 0 ? (
          <Card className="py-6 text-center text-sm text-muted-foreground">None.</Card>
        ) : (
          <Card className="gap-0 overflow-hidden py-0">
            <ul className="divide-y">
              {data.unlinked.map((t) => (
                <li key={t.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                  <span className="tabular w-14 shrink-0 text-xs text-muted-foreground">{shortDate(t.date)}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{t.payee || t.description}</span>
                    {t.account && (
                      <span className="block truncate text-xs text-muted-foreground">{holderLabel(t.account)}</span>
                    )}
                  </span>
                  <span className="tabular font-medium text-success">{signedMoney(t.amount)}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>
    </div>
  );
}
