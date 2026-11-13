import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { AnswerPanel } from "@/components/answer-panel";
import { Badge } from "@/components/status";
import { ThreadView } from "@/components/thread-view";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Conversation } from "@/lib/api";
import { label, longDate } from "@/lib/format";

export function ConversationCard({ conversation: c }: { conversation: Conversation }) {
  const [panel, setPanel] = useState<"view" | "correct" | null>(null);
  const toggle = (p: "view" | "correct") => setPanel(panel === p ? null : p);
  return (
    <li>
      <Card className="gap-2 px-4 py-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="font-medium break-words">{c.subject || "(no subject)"}</span>
          <span className="tabular text-xs text-muted-foreground">{longDate(c.last_date)}</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge text={label(c.kind)} className="normal-case" />
          <Badge text={c.stage} />
          {c.no_reply && <Badge text="no reply" />}
          {c.doubt && !c.answered && <Badge text="question" className="bg-warning-soft text-warning" />}
        </div>
        {c.summary && <p className="text-sm text-muted-foreground">{c.summary}</p>}
        {(c.contacts.length > 0 || c.roles.length > 0) && (
          <p className="text-xs text-muted-foreground">
            {[c.contacts.join(", "), c.roles.join(", ")].filter(Boolean).join(" · ")}
          </p>
        )}
        {c.answer && (
          <p className="text-xs">
            <span className="text-muted-foreground">Your answer: </span>
            {[c.answer.choice, c.answer.comment].filter(Boolean).join(" — ")}
          </p>
        )}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={() => toggle("view")} aria-expanded={panel === "view"}>
            {panel === "view" ? "Hide email" : "View email"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => toggle("correct")} aria-expanded={panel === "correct"}>
            Correct this
          </Button>
          <Button asChild size="sm" variant="ghost">
            <a href={c.link} target="_blank" rel="noreferrer">
              Open in Gmail <ExternalLink className="size-3.5" />
            </a>
          </Button>
        </div>
        {panel === "view" && <ThreadView threadId={c.thread_id} />}
        {panel === "correct" && <AnswerPanel conversation={c} onDone={() => setPanel(null)} />}
      </Card>
    </li>
  );
}
