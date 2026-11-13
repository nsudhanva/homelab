"""AI extraction of recruiters, companies, and roles from one email thread."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from .gmail import Thread

Kind = Literal[
    "recruiter_outreach",
    "application",
    "interview_scheduling",
    "interview",
    "assessment",
    "offer",
    "rejection",
    "follow_up",
    "referral",
    "job_alert",
    "owner_hiring",
    "not_job",
]
Stage = Literal[
    "outreach", "applied", "screening", "interview", "offer", "rejected", "withdrawn", "unknown"
]

RELEVANT_KINDS = {
    "recruiter_outreach",
    "application",
    "interview_scheduling",
    "interview",
    "assessment",
    "offer",
    "rejection",
    "follow_up",
    "referral",
}


class Contact(BaseModel):
    name: str = Field(description="Full name of the person, as they sign or as shown")
    email: str | None = Field(
        None, description="Their personal work address. Null for no-reply or LinkedIn relays"
    )
    title: str | None = Field(None, description="Job title if stated, e.g. 'Technical Recruiter'")
    role: Literal["recruiter", "coordinator", "hiring_manager", "interviewer", "other"]
    works_for: str | None = Field(None, description="Company or agency the person works for")
    via: Literal["email", "linkedin", "hiring_tool"] = "email"


class Verdict(BaseModel):
    kind: Kind
    company: str | None = Field(
        None, description="The hiring company (the employer of the job), not the agency"
    )
    agency: str | None = Field(
        None, description="Third-party recruiting agency, if the recruiter is not the employer"
    )
    roles: list[str] = Field(default_factory=list, description="Job titles discussed")
    contacts: list[Contact] = Field(default_factory=list)
    stage: Stage = "unknown"
    summary: str = Field(description="One short sentence on what happened in the thread")
    confidence: float = Field(ge=0, le=1)
    doubt: str | None = Field(
        None, description="A short question for the owner when you are not sure, else null"
    )
    options: list[str] = Field(
        default_factory=list, description="2 to 4 short answers to the doubt, most likely first"
    )

    @property
    def relevant(self) -> bool:
        return self.kind in RELEVANT_KINDS


INSTRUCTIONS = """\
You read one email thread from the mailbox of the owner, a software engineer.
Messages marked ME were sent by the owner.

Decide whether the thread is about the owner as a job candidate, and extract the facts.

kind:
- recruiter_outreach: a recruiter, sourcer, founder, or hiring manager contacts the owner
  about a job, by email, InMail, or a hiring platform (Hired, Wellfound, and so on).
- application: the owner applies or the company confirms an application.
- interview_scheduling, interview, assessment: scheduling, invites, interview loops,
  coding tests, take-home tasks.
- offer, rejection: outcome messages.
- follow_up: the owner or the company follows up on an earlier contact.
- referral: someone refers the owner, or the owner asks for a referral, for a specific job.
- job_alert: automated job lists, "jobs you may like", saved searches, newsletters from job
  boards. These are not a contact.
- owner_hiring: the owner is the interviewer or hiring for their own team, or helps a friend.
- not_job: anything else (sales, events, school, receipts, social).

Rules:
- company is the employer of the job. Staffing and recruiting agencies (for example Robert
  Half, TEKsystems, Hays, Randstad) are never the company: put them in agency, and put the
  client in company only when the thread names it. Use your knowledge to tell agencies from
  employers.
- Use the plain company name ("Stripe", not "Stripe, Inc." or "Stripe Recruiting").
- contacts are people on the company or agency side who wrote to the owner, scheduled with
  them, or were named as the owner's recruiter or coordinator. Never include the owner.
  Each contact is one real person with a personal name. Team or department senders such as
  "Acme Talent Acquisition" or "Acme Recruiting Team" are not contacts. Do not invent
  people. A no-reply sender is not a person; use the name in the signature or the
  "X via LinkedIn" name instead, with email null.
- An email address in contacts must appear in the thread. Do not guess addresses.
- stage is the furthest point the thread shows: outreach, applied, screening (recruiter or
  first call), interview (technical or onsite), offer, rejected, withdrawn (the owner declined).
- confidence is your certainty about kind, company, and contacts together.
- When an important fact is unclear and the owner can answer it (is this a real job contact,
  is the owner the candidate, which company), set doubt to one short question and give 2 to 4
  options. Do not ask about facts that nobody in the thread states, such as an agency's
  unnamed client or a missing job title. Otherwise doubt is null.
- If the owner answered a doubt, the answer and comment are correct. Follow them and set
  doubt to null.
"""


def render(thread: Thread, answer: dict[str, Any] | None = None) -> str:
    messages = thread.messages
    if len(messages) > 12:
        messages = [*messages[:3], *messages[-9:]]
    blocks = []
    for m in messages:
        who = "ME" if m.sent else f"{m.sender_name} <{m.sender_email}>"
        extra = f"\nAttachments: {', '.join(m.attachments)}" if m.attachments else ""
        blocks.append(
            f"--- {m.date[:10]} FROM {who} TO {', '.join(m.to[:5])}\n"
            f"Subject: {m.subject}{extra}\n{m.text[:2500]}"
        )
    text = "\n\n".join(blocks)
    if len(thread.messages) > len(messages):
        text = f"({len(thread.messages) - len(messages)} middle messages left out)\n\n{text}"
    if answer and (answer.get("choice") or answer.get("comment")):
        text += (
            "\n\n=== Owner's answer ===\n"
            f"Answer: {answer.get('choice') or '-'}\nComment: {answer.get('comment') or '-'}"
        )
    return text


class Extractor:
    """Wraps the shared AI task so tests can replace it."""

    def __init__(self) -> None:
        from homelab_ai import AITask

        self.task = AITask(name="jobs", output_type=Verdict, instructions=INSTRUCTIONS)
        self.model = self.task.describe().split(" -> ")[0]

    def __call__(self, thread: Thread, answer: dict[str, Any] | None = None) -> Verdict:
        return self.task.run_sync(render(thread, answer))
