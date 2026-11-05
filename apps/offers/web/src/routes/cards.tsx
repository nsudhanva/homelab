import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys, trackerApi } from "@/lib/api";
import {
  MONTH_NAMES,
  holderLabel,
  issuerAccent,
  longDate,
  money,
  monthBefore,
  monthYear,
  shortCard,
  shortDate,
  signedMoney,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/cards")({
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.dashboard(), queryFn: () => api.dashboard() }),
  pendingComponent: () => <Skeleton className="h-60 rounded-xl" />,
  component: Cards,
});

function Cards() {
  const { data } = useQuery({ queryKey: keys.dashboard(), queryFn: () => api.dashboard() });
  const { data: tracker } = useQuery({ queryKey: trackerApi.key(6), queryFn: () => trackerApi.get(6) });
  if (!data) return null;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Cards</h1>
        <p className="text-sm text-muted-foreground">
          Credits captured in each card's fee year, the 12 months between two annual fees, compared with the fee.
          Each offer says when it resets.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(tracker?.cards ?? []).map((card) => {
          const f = card.fee;
          const captured = f.year_start ? f.year_captured : card.year_captured;
          const coverage = card.annual_fee ? (captured / card.annual_fee) * 100 : 0;
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
                    <div className="text-xs text-muted-foreground">
                      {f.year_start && f.year_end
                        ? `Fee year ${monthYear(f.year_start)} – ${monthBefore(f.year_end)}`
                        : "This calendar year"}
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="tabular text-2xl font-semibold text-success">{money(captured)}</span>
                      <span className="tabular text-xs text-muted-foreground">{Math.round(coverage)}% of the fee</span>
                    </div>
                    <Progress value={Math.min(100, coverage)} className="h-2" />
                    <div className="text-xs text-muted-foreground">
                      {f.source === "fee" && f.fee_date
                        ? `Annual fee posted ${longDate(f.fee_date)}.`
                        : f.anniversary_month
                          ? `Card year starts in ${MONTH_NAMES[f.anniversary_month - 1]} (estimated; the fee is not in your data).`
                          : "The annual fee date is not in your data."}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">No annual fee.</div>
                )}

                {card.rewards && (
                  <div className="space-y-1.5 border-t pt-3 text-xs">
                    <div className="flex items-baseline justify-between">
                      <span className="font-medium text-foreground">
                        Earns{card.rewards.program ? ` ${card.rewards.program}` : ""}
                      </span>
                      <span className="tabular text-success">{money(card.rewards.year_value)} this year (est.)</span>
                    </div>
                    <ul className="space-y-1 text-muted-foreground">
                      {card.rewards.rules.map((b) => (
                        <li key={b.name}>
                          <span className="tabular font-medium text-foreground">
                            {card.rewards!.currency === "cash" ? `${b.rate}%` : `${b.rate}x`}
                          </span>{" "}
                          {b.name}
                          {b.detail && <span> · {b.detail}</span>}
                        </li>
                      ))}
                      <li>
                        <span className="tabular font-medium text-foreground">
                          {card.rewards.currency === "cash" ? `${card.rewards.base}%` : `${card.rewards.base}x`}
                        </span>{" "}
                        Everything else
                      </li>
                    </ul>
                    {card.rewards.note && <p className="text-muted-foreground/80">{card.rewards.note}</p>}
                  </div>
                )}

                <ul className="space-y-2 border-t pt-3">
                  {card.rows.map((r) => (
                    <li key={r.offer_id} className="text-xs">
                      <div className="font-medium text-foreground">
                        {r.name}
                        {r.kind !== "activation" && (
                          <span className="tabular font-normal text-muted-foreground"> · {money(r.value)}</span>
                        )}
                      </div>
                      <div className={r.period === "cardmember_year" ? "text-info" : "text-muted-foreground"}>
                        {r.cycle}
                      </div>
                    </li>
                  ))}
                </ul>
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
