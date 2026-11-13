"""Excel export of companies, recruiters, conversations, and open questions."""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .build import Company, Conversation


def _sheet(ws: Worksheet, header: list[str], rows: list[list[object]]) -> None:
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, title in enumerate(header, 1):
        width = max([len(title), *(len(str(r[i - 1] or "")) for r in rows[:500])])
        ws.column_dimensions[get_column_letter(i)].width = min(60, max(10, width + 2))


def status(company: Company) -> str:
    if company.outcome:
        return f"{company.stage} → {company.outcome}"
    return "no reply" if company.no_reply else company.stage


def workbook(companies: list[Company], doubts: list[Conversation]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Companies"
    _sheet(
        ws,
        [
            "Company",
            "Recruiters",
            "Emails",
            "Roles",
            "Status",
            "First contact",
            "Last contact",
            "Conversations",
            "Agencies",
        ],
        [
            [
                c.name,
                "; ".join(r.name for r in c.recruiters),
                "; ".join(r.email for r in c.recruiters if r.email),
                "; ".join(sorted(c.roles)),
                status(c),
                c.first_date[:10],
                c.last_date[:10],
                len(c.conversations),
                "; ".join(sorted(c.agencies)),
            ]
            for c in companies
        ],
    )
    _sheet(
        wb.create_sheet("Recruiters"),
        [
            "Name",
            "Email",
            "Title",
            "Company",
            "Agency",
            "Roles",
            "First contact",
            "Last contact",
            "Conversations",
            "Source",
        ],
        [
            [
                r.name,
                r.email,
                r.title,
                c.name,
                r.agency,
                "; ".join(sorted(r.roles)),
                r.first_date[:10],
                r.last_date[:10],
                len(r.threads),
                r.via,
            ]
            for c in companies
            for r in c.recruiters
        ],
    )
    _sheet(
        wb.create_sheet("Conversations"),
        [
            "Last date",
            "Company",
            "Subject",
            "Kind",
            "Stage",
            "No reply",
            "Contacts",
            "Roles",
            "Summary",
            "Gmail",
        ],
        [
            [
                x.last_date[:10],
                c.name,
                x.subject,
                x.kind,
                x.stage,
                "yes" if x.no_reply else "",
                "; ".join(x.contacts),
                "; ".join(x.roles),
                x.summary,
                x.link,
            ]
            for c in companies
            for x in c.conversations
        ],
    )
    _sheet(
        wb.create_sheet("Open questions"),
        ["Last date", "Company", "Subject", "Question", "Options", "Confidence", "Gmail"],
        [
            [
                d.last_date[:10],
                d.company,
                d.subject,
                d.doubt or "Low confidence",
                " | ".join(d.options),
                round(d.confidence, 2),
                d.link,
            ]
            for d in doubts
            if not d.answered
        ],
    )
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
