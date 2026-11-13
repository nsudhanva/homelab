export type Recruiter = {
  key: string;
  name: string;
  email: string | null;
  title: string | null;
  role: string;
  company: string;
  company_key: string;
  agency: string | null;
  via: string;
  roles: string[];
  first_date: string;
  last_date: string;
  threads: number;
};

export type Company = {
  key: string;
  name: string;
  stage: string;
  outcome: string | null;
  status: string;
  no_reply: boolean;
  first_date: string;
  last_date: string;
  roles: string[];
  agencies: string[];
  conversations: number;
  open_questions: number;
  recruiters: Recruiter[];
};

export type Answer = { thread_id: string; choice: string | null; comment: string | null; created_at: string };

export type Conversation = {
  thread_id: string;
  subject: string;
  first_date: string;
  last_date: string;
  kind: string;
  stage: string;
  summary: string;
  roles: string[];
  contacts: string[];
  company: string;
  company_key: string;
  agency: string | null;
  no_reply: boolean;
  confidence: number;
  doubt: string | null;
  options: string[];
  answered: boolean;
  link: string;
  answer: Answer | null;
};

export type Overview = {
  last_sync: string | null;
  last_fetch: string | null;
  totals: { companies: number; recruiters: number; conversations: number; open_questions: number; no_reply: number };
  companies: Company[];
};

export type CompanyDetail = Company & { conversation_list: Conversation[] };

export type Verdict = {
  kind: string;
  company: string | null;
  agency: string | null;
  roles: string[];
  stage: string;
  summary: string;
  confidence: number;
};

export type ThreadDetail = {
  id: string;
  subject: string;
  verdict: Verdict | null;
  answer: Answer | null;
  messages: { date: string; from: string; email: string | null; text: string }[];
};

export type AnswerBody = { choice?: string | null; comment?: string | null };
export type AnswerResult = { saved: boolean; applied: boolean; verdict: Verdict | null };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const keys = {
  all: ["jobs"] as const,
  overview: ["jobs", "overview"] as const,
  company: (key: string) => ["jobs", "company", key] as const,
  questions: ["jobs", "questions"] as const,
  thread: (id: string) => ["jobs", "thread", id] as const,
};

export const api = {
  overview: () => request<Overview>("/api/overview"),
  company: (key: string) => request<CompanyDetail>(`/api/companies/${encodeURIComponent(key)}`),
  questions: () => request<{ open: Conversation[]; answered: Conversation[] }>("/api/questions"),
  thread: (id: string) => request<ThreadDetail>(`/api/threads/${encodeURIComponent(id)}`),
  answer: (id: string, body: AnswerBody) =>
    request<AnswerResult>(`/api/threads/${encodeURIComponent(id)}/answer`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  rename: (key: string, name: string) =>
    request<{ saved: boolean }>(`/api/companies/${encodeURIComponent(key)}/rename`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
};

export const EXPORT_URL = "/api/export.xlsx";
