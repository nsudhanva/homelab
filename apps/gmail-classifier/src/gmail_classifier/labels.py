"""Routing hints for curated Gmail labels.

A hint is rendered next to its label in the prompt only when the account has that label,
so one table serves every account. Hints describe sender intent and the senders seen in
practice; labels without a hint are self-explanatory (for example Personal/Doordash).
"""

LABEL_HINTS: dict[str, str] = {
    "Companies/Apply": (
        "Outbound job applications: ATS confirmations (Greenhouse, Lever, Ashby, Workday, "
        "SmartRecruiters, iCIMS), interview scheduling, take-home assignments and their cloud "
        "alerts, NDAs or CDAs signed while interviewing, outcomes and rejections"
    ),
    "Companies/Jobs": (
        "Inbound recruiter, headhunter, or talent-agency outreach, and intro calls booked "
        "through Cal.com"
    ),
    "Companies/Zerodha": "Zerodha, NSE, and CDSL trading account statements and alerts",
    "Personal": (
        "Account administration with no dedicated label: sign-in links, one-time codes, "
        "security and policy notices, and cloud or developer tool accounts (Anthropic, "
        "Google Cloud, Oracle Cloud, Backblaze, Slack)"
    ),
    "Personal/GitHub": (
        "GitHub notifications, CI failures, Dependabot, code scanning, and package registries "
        "(npm, crates.io, RubyGems, PyPI)"
    ),
    "Personal/Rent": (
        "The current apartment building: Ironworks or RealPage notices, daily digests, service "
        "requests, amenity and parking notices, and Door building access"
    ),
    "Personal/Real Estate": "Apartment hunting, other buildings' leasing offices, and movers",
    "Personal/Banks": (
        "Banks writing directly: statements, card alerts, payment reminders, and account "
        "requests (ICICI, Axis, Bank of Baroda)"
    ),
    "Personal/Amex": "American Express statements, alerts, and fraud notices",
    "Personal/Amazon": "Amazon orders and shipping (amazon.com, amazon.in) and the Amazon Pay card",
    "Personal/Apple": "Apple Card, Apple Cash, and Apple account emails",
    "Personal/Health": "Doctors, clinics, imaging, physical therapy, and medical billing",
    "Personal/Family/Maanasa": "Anything that names or schedules something for Maanasa",
    "Personal/Family/Narayana": "Emails from or about Narayana",
    "Personal/Family/Rashmi": "Emails from or about Rashmi",
    "Personal/Family/Sameera": "Emails from or about Sameera",
    "Personal/College": "PES University faculty and alumni communication",
    "Personal/sudhanva.me": (
        "The personal site and blog: Ghost, PikaPods hosting, Google Analytics, Bing Webmaster, "
        "and subscriber milestones"
    ),
    "Personal/Tax": "Tax preparers and filings",
    "Personal/Bookings": "Restaurant and experience reservations, including their sign-in codes",
    "Personal/Travel": "Flights, hotels, car rentals, and trip plans",
    "Personal/USPS": "USPS Informed Delivery digests",
    "Initiable": (
        "The Initiable startup: company filings, AI startup programs, and founder or AI meetups"
    ),
    "Finance": (
        "Bills, invoices, and payment receipts for services without their own label: cloud "
        "invoices (Oracle, Cloudflare, Google Cloud, AWS budgets), phone and broadband bills, "
        "and crypto exchanges"
    ),
    "Newsletters": (
        "Editorial newsletters and digests: Substack, ByteByteGo, MLOps Community, Quora, news"
    ),
    "Shopping": "Retail orders, receipts, and store promotions without a dedicated label",
    "Social": "Personal invitations and parties, and replies on social networks",
    "Entertainment": "Streaming and video services such as YouTube and Peacock",
    "USA": (
        "US government and civic life: city services, DMV or RMV, tolls, traffic citations, "
        "immigration, and visas"
    ),
    "YOLO": "Northeastern University student life and events",
    "Random": (
        "Self-sent tests, Gmail auto-generated unsubscribe messages, delivery failure bounces, "
        "and cold sales pitches"
    ),
    "cc-automated": "Daily brief emails sent from the +cc address",
}


def render_label_guide(labels: list[str]) -> str:
    """Format allowed labels as a bullet list, with a hint where one is known."""
    return "\n".join(
        f"- {label}: {LABEL_HINTS[label]}" if label in LABEL_HINTS else f"- {label}"
        for label in labels
    )
