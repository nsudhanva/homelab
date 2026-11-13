import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { api, keys } from "@/lib/api";
import { longDate } from "@/lib/format";

export function ThreadView({ threadId }: { threadId: string }) {
  const { data, isLoading } = useQuery({ queryKey: keys.thread(threadId), queryFn: () => api.thread(threadId) });
  if (isLoading) return <Skeleton className="h-24 rounded-lg" />;
  if (!data) return <p className="text-xs text-muted-foreground">Could not load the email.</p>;
  return (
    <ol className="space-y-2">
      {data.messages.map((m, i) => (
        <li key={i} className="rounded-lg border bg-background p-3 text-xs">
          <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-medium text-foreground">
              {m.from}
              {m.email && <span className="font-normal text-muted-foreground"> · {m.email}</span>}
            </span>
            <span className="text-muted-foreground">{longDate(m.date)}</span>
          </div>
          <p className="max-h-60 overflow-y-auto whitespace-pre-wrap break-words text-muted-foreground">{m.text}</p>
        </li>
      ))}
    </ol>
  );
}
