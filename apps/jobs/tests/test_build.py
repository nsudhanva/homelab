from conftest import message, thread, verdict

from jobs.build import build, company_key


def test_company_key_ignores_suffixes_and_case():
    assert company_key("Stripe, Inc.") == company_key("stripe") == company_key("Stripe Recruiting")


def test_groups_companies_and_merges_recruiters():
    threads = [
        thread("t1", message(1, days_ago=60)),
        thread("t2", message(2, days_ago=10)),
        thread("t3", message(3, days_ago=5)),
        thread("t4", message(4, days_ago=5)),
    ]
    verdicts = {
        "t1": verdict(
            company="Acme, Inc.",
            contacts=[{"name": "Ann Lee", "email": None, "role": "recruiter", "via": "linkedin"}],
        ),
        "t2": verdict(stage="interview", roles=["Staff Engineer"]),
        "t3": verdict(kind="rejection", stage="rejected", contacts=[]),
        "t4": verdict(kind="job_alert", company="Other"),
    }
    companies, _ = build(threads, verdicts, {}, {})
    assert [c.name for c in companies] == ["Acme"]
    acme = companies[0]
    assert (acme.stage, acme.outcome) == ("interview", "rejected")
    assert len(acme.conversations) == 3
    [ann] = acme.recruiters
    assert ann.email == "ann@acme.com" and ann.threads == {"t1", "t2"}
    assert ann.roles == {"Senior Engineer", "Staff Engineer"}


def test_agency_recruiter_listed_under_client_and_agency_alone():
    threads = [thread("t1", message(1)), thread("t2", message(2))]
    verdicts = {
        "t1": verdict(company="Acme", agency="Hays"),
        "t2": verdict(company=None, agency="Hays"),
    }
    companies, _ = build(threads, verdicts, {}, {})
    by_name = {c.name: c for c in companies}
    assert by_name["Acme"].agencies == {"Hays"}
    assert by_name["Acme"].recruiters[0].agency == "Hays"
    assert by_name["Hays"].recruiters[0].agency is None


def test_no_reply_when_owner_wrote_last_long_ago():
    threads = [
        thread("t1", message(1, days_ago=40), message(2, sent=True, days_ago=30)),
        thread("t2", message(3, sent=True, days_ago=3)),
    ]
    verdicts = {"t1": verdict(), "t2": verdict(company="Beta", kind="application")}
    companies, _ = build(threads, verdicts, {}, {})
    by_name = {c.name: c for c in companies}
    assert by_name["Acme"].no_reply and not by_name["Beta"].no_reply


def test_renames_merge_companies_and_doubts_are_listed():
    threads = [thread("t1", message(1)), thread("t2", message(2))]
    verdicts = {
        "t1": verdict(company="Meta"),
        "t2": verdict(company="Facebook", doubt="Which team?", options=["A", "B"]),
    }
    companies, doubts = build(threads, verdicts, {}, {"facebook": "Meta"})
    assert [c.name for c in companies] == ["Meta"]
    assert [d.thread_id for d in doubts] == ["t2"]
