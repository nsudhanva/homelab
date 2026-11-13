import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { AnswerPanel } from "@/components/answer-panel";
import { Badge } from "@/components/status";
import { ThreadView } from "@/components/thread-view";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys, type Conversation } from "@/lib/api";
import { label, longDate } from "@/lib/format";

export const Route = createFileRoute("/questions")({
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: keys.questions, queryFn: api.questions }),
  pendingComponent: () => <Skeleton className="h-80 rounded-xl" />,
  component: Questions,
});

function Questions() {
  const { data } = useQuery({ queryKey: keys.questions, queryFn: api.questions });
  if (!data) return null;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Questions</h1>
        <p className="text-sm text-muted-foreground">
          The AI was not sure about these threads. Pick an answer or write a comment, and the AI reads the thread again
          with your answer.
        </p>
      </div>
      {data.open.length === 0 ? (
        <Card className="py-8 text-center text-sm text-muted-foreground">No open questions.</Card>
      ) : (
        <ul className="space-y-3">
          {data.open.map((c) => (
            <QuestionCard key={c.thread_id} conversation={c} />
          ))}
        </ul>
      )}
      {data.answered.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">Answered</h2>
          <ul className="space-y-2">
            {data.answered.map((c) => (
              <li key={c.thread_id}>
                <Card className="gap-1 px-4 py-3 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium">{c.subject || "(no subject)"}</span>
                    <span className="tabular text-xs text-muted-foreground">{longDate(c.last_date)}</span>
                  </div>
                  <p className="text-xs">
                    <span className="text-muted-foreground">Your answer: </span>
                    {[c.answer?.choice, c.answer?.comment].filter(Boolean).join(" — ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    AI now reads it as {label(c.kind).toLowerCase()}
                    {c.company && ` at ${c.company}`}. {c.summary}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function QuestionCard({ conversation: c }: { conversation: Conversation }) {
  const [view, setView] = useState(false);
  return (
    <li>
      <Card className="gap-3 px-4 py-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-medium break-words">{c.subject || "(no subject)"}</span>
            <span className="tabular text-xs text-muted-foreground">{longDate(c.last_date)}</span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            {c.company && c.company_key ? (
              <Link to="/companies/$key" params={{ key: c.company_key }} className="hover:underline">
                {c.company}
              </Link>
            ) : (
              <span>No company found</span>
            )}
            <Badge text={label(c.kind)} className="normal-case" />
            <span className="tabular">{Math.round(c.confidence * 100)}% sure</span>
          </div>
          {c.summary && <p className="text-sm text-muted-foreground">{c.summary}</p>}
        </div>
        <AnswerPanel conversation={{ ...c, doubt: c.doubt ?? "Is this reading correct?" }} />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setView(!view)} aria-expanded={view}>
            {view ? "Hide email" : "View email"}
          </Button>
          <Button asChild size="sm" variant="ghost">
            <a href={c.link} target="_blank" rel="noreferrer">
              Open in Gmail <ExternalLink className="size-3.5" />
            </a>
          </Button>
        </div>
        {view && <ThreadView threadId={c.thread_id} />}
      </Card>
    </li>
  );
}
