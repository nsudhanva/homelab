import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { CircleCheckBig, CircleSlash, RefreshCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys, type ReviewItem } from "@/lib/api";
import { holderLabel, shortCard, shortDate, signedMoney } from "@/lib/format";
import { useDecide } from "@/lib/mutations";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/review")({
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.review, queryFn: api.review }),
  pendingComponent: () => <Skeleton className="h-40 rounded-xl" />,
  component: AiLog,
});

function AiLog() {
  const { data = [] } = useQuery({ queryKey: keys.review, queryFn: api.review });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">AI log</h1>
        <p className="text-sm text-muted-foreground">
          The AI decides transactions that the rules cannot, and its answer applies automatically. These are the
          answers it was least sure about. You do not need to do anything. Flip one only if it is wrong.
        </p>
      </div>
      {data.length === 0 ? (
        <Card className="items-center gap-2 py-12 text-center">
          <CircleCheckBig className="size-8 text-success" />
          <div className="font-medium">No low-confidence decisions</div>
          <p className="text-sm text-muted-foreground">The rules and the AI were sure about everything.</p>
        </Card>
      ) : (
        <ul className="space-y-3">
          {data.map((item) => (
            <LogCard key={`${item.txn.id}:${item.offer_id}`} item={item} />
          ))}
        </ul>
      )}
    </div>
  );
}

function LogCard({ item }: { item: ReviewItem }) {
  const decide = useDecide();
  return (
    <li>
      <Card className="gap-0 py-0">
        <CardContent className="space-y-3 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-medium">{item.txn.payee || item.txn.description}</div>
              <div className="text-xs text-muted-foreground">
                {shortDate(item.txn.date)}
                {item.txn.account && ` · ${holderLabel(item.txn.account)}`}
              </div>
            </div>
            <div className={cn("tabular font-semibold", item.txn.amount > 0 && "text-success")}>
              {signedMoney(item.txn.amount)}
            </div>
          </div>
          <div className="flex items-start gap-2 text-sm">
            {item.ai_match ? (
              <CircleCheckBig className="mt-0.5 size-4 shrink-0 text-success" />
            ) : (
              <CircleSlash className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            )}
            <span>
              {item.ai_match ? "Counted toward " : "Not counted toward "}
              <span className="font-medium">{item.offer_name}</span>
              <span className="text-muted-foreground"> on {shortCard(item.card_name)}</span>
            </span>
          </div>
          <p className="flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            <Sparkles className="mt-0.5 size-3.5 shrink-0" />
            <span>
              {Math.round(item.confidence * 100)}% sure. {item.reason}
            </span>
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 text-muted-foreground"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ txn_id: item.txn.id, offer_id: item.offer_id, match: !item.ai_match })}
          >
            <RefreshCcw className="size-4" /> Wrong? Flip it
          </Button>
        </CardContent>
      </Card>
    </li>
  );
}
