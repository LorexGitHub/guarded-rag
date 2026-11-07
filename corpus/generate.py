"""Write the eval corpus and its ground-truth manifest (ADR 0007).

Deterministic: hand-written templates and a hand-picked persona list, no randomness.
Run `python corpus/generate.py` to rewrite the committed files.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
PHONE_FORMATS = {
    "paren": "({a}) {b}-{c}",
    "dash": "{a}-{b}-{c}",
    "plus": "+1 {a} {b} {c}",
}


@dataclass(frozen=True)
class Person:
    name: str
    role: str
    phone: str  # ten digits
    emp_id: str = ""

    @property
    def email(self) -> str:
        return self.name.lower().replace(" ", ".") + "@example.com"


def _person(name, role, line, emp=""):
    return Person(name, role, f"555010{line:04d}", f"EMP-{emp}" if emp else "")


EMPLOYEES = {
    "jane": _person("Jane Doe", "Support Lead", 142, "10421"),
    "will": _person("Will Hunt", "Engineering Manager", 143, "10422"),
    "grace": _person("Grace Park", "HR Business Partner", 144, "10423"),
    "mark": _person("Mark Fields", "Finance Analyst", 145, "10424"),
    "april": _person("April Winter", "People Operations Lead", 146, "10425"),
    "priya": _person("Priya Raman", "Senior Engineer", 147, "10426"),
    "tomas": _person("Tomas Berg", "Support Agent", 148, "10427"),
    "lena": _person("Lena Okafor", "Support Agent", 149, "10428"),
    "diego": _person("Diego Alvarez", "Site Reliability Engineer", 150, "10429"),
    "hannah": _person("Hannah Weiss", "Product Manager", 151, "10430"),
    "samir": _person("Samir Haddad", "Security Engineer", 152, "10431"),
    "chloe": _person("Chloe Nguyen", "Recruiter", 153, "10432"),
    "oskar": _person("Oskar Lind", "Data Engineer", 154, "10433"),
    "ruth": _person("Ruth Mbeki", "Office Manager", 155, "10434"),
    "felix": _person("Felix Brandt", "Account Executive", 156, "10435"),
}
CUSTOMERS = {
    "marcus": _person("Marcus Webb", "customer", 171),
    "elena": _person("Elena Rossi", "customer", 172),
    "kwame": _person("Kwame Mensah", "customer", 173),
    "sofia": _person("Sofia Lindqvist", "customer", 174),
    "daniel": _person("Daniel Cho", "customer", 175),
    "aisha": _person("Aisha Rahman", "customer", 176),
}
E, C = EMPLOYEES, CUSTOMERS


class Doc:
    """Builds one document's text and records every seeded value it contains."""

    def __init__(self, filename):
        self.filename = filename
        self.entries = []

    def _seed(self, value, entity_type, normalized):
        self.entries.append(
            {"value": value, "entity_type": entity_type, "doc": self.filename,
             "normalized": normalized}
        )
        return value

    def name(self, p):
        return self._seed(p.name, "PERSON", p.name.lower())

    def email(self, p):
        return self._seed(p.email, "EMAIL_ADDRESS", p.email)

    def phone(self, p, fmt="paren"):
        a, b, c = p.phone[:3], p.phone[3:6], p.phone[6:]
        return self._seed(PHONE_FORMATS[fmt].format(a=a, b=b, c=c), "PHONE_NUMBER", p.phone)

    def emp_id(self, p):
        return self._seed(p.emp_id, "EMPLOYEE_ID", p.emp_id.lower())


TOKEN = re.compile(r"\[(name|email):(\w+)\]")


def _flow(text):
    """Join wrapped source lines into paragraphs; blank lines separate blocks."""
    return "\n\n".join(" ".join(block.split()) for block in text.split("\n\n"))


def _paragraphs(*paras):
    return "\n\n".join(_flow(p) for p in paras) + "\n"


def policy(d, policy_text, **fields):
    """Render a (title, *paragraphs) policy, seeding each [name:key] / [email:key] token."""
    title, *paras = policy_text
    text = "\n\n".join(_flow(p) for p in paras)
    text = text.format(**fields) if fields else text
    seed = {"name": d.name, "email": d.email}
    text = TOKEN.sub(lambda m: seed[m[1]](E[m[2]]), text)
    return f"# {title.format(**fields)}\n\n{text}\n"


PTO_POLICY = (
    "{title}",
        """This policy explains how paid time off works at Acme Example. It applies to every
        full-time and part-time employee from their first day. Paid time off covers vacation,
        personal days, and short absences that are not medical. Sick leave and parental leave
        are covered in separate policies. {extra}""",
        """## Accrual

        Full-time employees receive {days} days of paid time off per calendar year. The days
        accrue monthly, so an employee who joins in July receives half of the annual amount.
        Part-time employees accrue in proportion to their scheduled hours. Accrued time is
        shown in the people portal on the first working day of each month.""",
        """## Requesting time off

        Submit a request in the people portal at least {notice} before the first day of
        leave. Your manager approves or declines the request within three working days. For
        absences of more than ten consecutive days, speak to your manager before you submit.
        Approval is not guaranteed in the last week of a quarter, when many teams close their
        books or ship releases, so plan long breaks early.""",
        """## Carry-over and payout

        Up to {carry} unused days carry over into the next year and expire on 31 March. Days
        above that limit are lost on 31 December. Acme Example does not pay out unused days
        during employment. When employment ends, the final paycheck includes accrued but
        unused days, as local law requires.""",
        """## Public holidays and closures

        Public holidays do not count against paid time off. When the company closes between
        24 December and 1 January, those days are also free of charge to your balance. If you
        work a public holiday because of on-call duty, you earn one day of time off in lieu,
        which you should use within 60 days.""",
        """## Sick days and short notice

        Do not use paid time off for illness; report sick days to your manager on the first
        morning and record them in the people portal. If you fall ill during planned leave
        and bring a medical note, the sick days are returned to your balance. Unplanned
        personal emergencies, such as a burst pipe at home, may be booked as paid time off
        after the fact if you tell your manager as soon as you can. Managers should be
        flexible and avoid asking for details that are private.""",
        """## Questions

        Contact [name:grace] at [email:grace] for balance corrections or accrual
        questions. [name:april] at [email:april] handles exceptions, such as
        extended unpaid leave or a request that overlaps a blackout week.""",
    )


PTO_2025 = {
    "title": "PTO Policy", "days": 25, "carry": 5, "notice": "ten working days",
    "extra": "This version took effect on 1 January 2025 and replaces all earlier versions.",
}
PTO_2022 = {
    "title": "PTO Policy (2022, archived)", "days": 20, "carry": 3, "notice": "five working days",
    "extra": "This version was replaced on 1 January 2025 and is kept only for the record.",
}


REMOTE_WORK_POLICY = (
    "Remote Work Policy",
        """Acme Example supports remote work because focused work and flexible hours help many
        teams do their best work. This policy sets the shared rules so that remote work stays
        fair for people in the office and people at home. It applies to all employees whose
        role allows remote work. Roles that need physical presence, such as the office
        manager, follow the schedule in their offer letter.""",
        """## Eligibility and agreements

        After the first ninety days, employees may work remotely up to three days per week
        with their manager's agreement. Fully remote arrangements need a written agreement
        signed by the manager and People Operations. The agreement names the working country,
        because tax and employment rules differ between countries. Work from another country
        for more than fourteen days in a year needs advance approval.""",
        """## Core hours and availability

        Every team agrees on four core hours in which everyone is reachable by chat and
        video. Outside core hours, employees may shape their day as they like, as long as
        deadlines are met. Keep your calendar current and mark focus time so colleagues know
        when you are away. Update your chat status when you step out for more than an hour.""",
        """## Equipment and security

        Acme Example provides a laptop, a monitor and a headset for the home office. Use the
        company laptop for all work, and keep its disk encryption and automatic updates on.
        Do not work on customer data in public places where others can see your screen, and
        use the company VPN on any network you do not control. Report a lost or stolen
        device to the security team within one hour.""",
        """## Home office allowance

        New remote employees receive a one-time allowance of 400 euros for a desk, a chair
        or lighting. Keep the receipts and file them under the expense policy. The office
        manager, [name:ruth], arranges shipping of company equipment and can be
        reached at [email:ruth].""",
        """## Working across time zones

        Remote employees who live more than three hours away from their team agree on a
        shared overlap with that team. Meetings are scheduled inside the overlap, and long
        discussions are written down so that people in other zones can reply later. Record
        decisions in the team wiki. Travel to the office for planning weeks is paid by the
        company and is announced at least six weeks ahead, so that employees can arrange
        childcare or other commitments around it.""",
        """## Questions

        Raise questions about eligibility or agreements with [name:april] at
        [email:april]. Employees who disagree with a decision may ask for a second review
        by the head of People Operations within ten working days.""",
)


EXPENSE_POLICY = (
    "Expense Policy",
        """This policy tells employees what Acme Example pays for when they work, travel or
        entertain customers, and how to claim the money back. Spend company money as if it were
        your own, choose reasonable options, and keep every receipt. Claims that break these
        rules may be declined, and repeated misuse is handled under the code of conduct.""",
        """## What is covered

        The company pays for transport to approved business trips, hotels up to 160 euros per
        night, meals while travelling up to 45 euros per day, and software that your manager
        approved in advance. Alcohol is not covered unless a customer dinner was approved
        beforehand. Personal items, fines and upgrades are never covered.""",
        """## Booking and approval

        Book flights and hotels through the company travel tool so that invoices go straight to
        Finance. Trips that cost more than 1,000 euros need written approval from your
        manager before you book. Expenses above 5,000 euros in a single claim also need the
        approval of a department head.""",
        """## Filing a claim

        File the claim in the expense tool within thirty days of the purchase. Attach a
        photograph or scan of the receipt, name the project or cost centre, and add one line
        about the business purpose. Claims without receipts are paid only up to 25 euros and
        only once per quarter. Finance pays approved claims with the next monthly payroll.""",
        """## Corporate cards

        Employees who travel often may receive a corporate card. The card is for business
        costs only. Reconcile every card transaction in the expense tool by the fifth working
        day of the next month. Lost cards must be blocked at once, then reported to Finance.""",
        """## Mileage, per diems and foreign currency

        Private car use for business is reimbursed at 0.30 euros per kilometre, with the
        route recorded in the claim. Meals on days with an overnight stay use the per diem
        rate instead of receipts. Claims in a foreign currency are converted at the rate on
        the day of purchase, and the card statement serves as proof of that rate. Tips are
        reimbursed up to ten percent where they are customary. Gifts for customers must
        stay below 50 euros per person and need a note naming the recipient's company.""",
        """## Questions

        Finance questions go to [name:mark] at [email:mark]. For questions about
        booking tools, ask [name:ruth] at [email:ruth].""",
)


CODE_OF_CONDUCT = (
    "Code of Conduct",
        """Acme Example expects every employee, contractor and visitor to treat others with
        respect. This code describes the behaviour we expect and what happens when someone
        falls short. It applies in the office, in video calls, in chat, at events and on
        customer sites, wherever you act as a representative of the company.""",
        """## Respect and inclusion

        Treat colleagues, customers and partners fairly and politely. Harassment,
        discrimination, bullying and insulting jokes have no place here, whether they happen in
        person or online. Listen to different views, give feedback about the work and not the
        person, and assume good intent until you learn otherwise.""",
        """## Honesty and conflicts of interest

        Be truthful in reports, timesheets and expense claims. Tell your manager early when you
        have a personal or financial interest that could affect a business decision, for
        example a family member who works for a supplier. Do not accept gifts worth more than
        50 euros from anyone who does business with the company.""",
        """## Protecting information

        Customer data, employee records and unreleased plans are confidential. Share them only
        with people who need them for their work, and only through approved tools. Do not
        copy personal data into private notes, public chat rooms or tools that Acme Example has
        not approved. Report any suspected data leak to the security team immediately.""",
        """## Social media and public speaking

        Make clear that your views are your own when you write about work in public. Do not
        post screenshots of internal tools, customer messages or unreleased features. If a
        journalist or conference organiser contacts you about the company, send the request
        to the communications team before you reply. Speaking at events on your own time is
        welcome, and the company will help you prepare slides and review them for
        confidential content.""",
        """## Raising a concern

        If you see or experience behaviour that breaks this code, you can speak to your manager,
        to [name:grace] at [email:grace], or to [name:samir] at [email:samir] for
        matters that involve security or data. You may also report a concern anonymously
        through the ethics form in the people portal. The company does not allow retaliation
        against anyone who raises a concern in good faith.""",
        """## Consequences

        People Operations looks into every report promptly and fairly. Depending on the
        findings, the outcome ranges from a coaching conversation to a written warning or the
        end of employment. Serious matters, such as threats or fraud, may also be passed to the
        authorities.""",
)


ON_CALL_POLICY = (
    "On-Call Policy",
        """Some Acme Example services must stay available day and night. Engineers who run these
        services share an on-call rotation. This policy describes how the rotation works,
        what the company pays for it, and what you can expect when your pager goes off.""",
        """## Rotation

        Each rotation lasts one week, from Monday at 10:00 to the next Monday at 10:00. Every
        team keeps at least five people in its rotation, so nobody is on call more than one week
        in five. Swap shifts with a teammate by changing the schedule in the paging tool, and
        tell your manager when you do.""",
        """## Response times

        The primary engineer acknowledges a page within ten minutes and starts working on a
        severity one incident within thirty minutes. A secondary engineer is paged if the
        primary does not acknowledge. Keep a laptop and a stable connection within reach for
        the whole week, and do not plan travel that makes this impossible.""",
        """## Pay and time off

        On-call engineers receive a weekly allowance of 350 euros, plus overtime pay for any
        incident work outside normal hours. After a night with more than two hours of incident
        work, take the next morning off without using paid time off. Public holidays on call
        earn a day in lieu, as the PTO policy explains.""",
        """## After an incident

        Within three working days of a severity one or two incident, the primary engineer writes
        a blameless review. The review lists the timeline, the cause, and the follow-up work
        with owners. Share it with the team and add the actions to the backlog.""",
        """## Handover and documentation

        At the end of each rotation the outgoing engineer writes a short handover note in the
        team channel: open incidents, flaky alerts, planned deploys and anything unusual.
        The incoming engineer reads it before the rotation begins and asks questions in the
        handover call on Monday morning. Runbooks live in the team wiki and are updated
        whenever a page turns out to be missing a step. Alerts that wake someone without
        needing action are tuned or deleted within two weeks.""",
        """## Questions

        The rotation owner is [name:diego], reachable at [email:diego]. Escalations
        and exceptions go to [name:will] at [email:will].""",
)


def employee_directory(d):
    rows = "\n".join(
        f"| {d.name(p)} | {p.role} | {d.phone(p)} | {d.email(p)} | {d.emp_id(p)} |"
        for p in E.values()
    )
    return (
        "# Employee Directory\n\n"
        "Internal use only. Report changes to People Operations.\n\n"
        "| Name | Role | Phone | Email | Employee ID |\n"
        "| --- | --- | --- | --- | --- |\n" + rows + "\n"
    )


TICKETS = [
    ("1042", "marcus", "tomas", "dash", "Export to CSV fails on large reports",
     "My exports stop at about 10,000 rows and then the download shows a blank page.",
     "reproduced the failure with a 12,000-row report and found a timeout in the export job",
     "raised the timeout and re-ran the export; the full file downloaded"),
    ("1043", "elena", "lena", "plus", "Cannot reset my password",
     "The reset email never arrives, and I have tried three times since this morning.",
     "found the address was on the suppression list after a bounce last month",
     "removed it from the list and sent a fresh reset link"),
    ("1044", "kwame", "jane", "paren", "Invoice shows the wrong company name",
     "Our March invoice lists our old company name, and our accountant cannot accept it.",
     "confirmed the billing profile was never updated after the rename",
     "corrected the profile and issued a replacement invoice"),
    ("1045", "sofia", "tomas", "plus", "Dashboard widgets load slowly",
     "Since Monday the dashboard takes about a minute to show the usage widgets.",
     "traced the delay to a slow query that ran without an index",
     "added the index; widgets now load in under three seconds"),
    ("1046", "daniel", "lena", "dash", "Request to add a second admin",
     "Please make my colleague an administrator for our workspace so that I am not the only one.",
     "verified the request came from the current workspace owner",
     "added the second administrator and confirmed by email"),
    ("1047", "aisha", "jane", "paren", "Webhook deliveries are missing",
     "Our endpoint did not receive any order webhooks between noon and 14:00 yesterday.",
     "found a short outage in our delivery queue during that time window",
     "replayed the missed events and confirmed receipt on your endpoint"),
]


def ticket(d, number, customer, agent, fmt, title, problem, finding, fix):
    cust, agt = C[customer], E[agent]
    return f"# Ticket {number}: {title}\n\n" + _paragraphs(
        f"""**Customer:** {d.name(cust)}, {d.email(cust)}, phone {d.phone(cust, fmt)}.
        **Assigned to:** {d.name(agt)} ({agt.role}), {d.email(agt)}.""",
        f"""## Customer message

        Hello, this is {cust.name.split()[0]}. {problem} Could you look into this today? You can
        reach me on {d.phone(cust, fmt)} if a call is easier than email. Thank you.""",
        f"""## Agent notes

        {agt.name.split()[0]} here. I {finding}. I then {fix}. I wrote to {cust.name.split()[0]}
        at {d.email(cust)} and offered a call back on {d.phone(cust, fmt)}.""",
        f"""## Internal follow-up

        {agt.name.split()[0]} checked whether other accounts were affected and found no more
        reports in the last seven days. The case was added to the knowledge base with the
        steps above, so that colleagues on the next shift can solve the same problem without
        asking the customer for details again. If it comes back, the incident template
        should be used and the on-call engineer informed through the paging tool.""",
        """## Resolution

        The customer confirmed that the problem is solved. The ticket is closed and tagged for
        the weekly support review so that we can look for a pattern.""",
    )


def builders():
    def fixed(text, **fields):
        return lambda d: policy(d, text, **fields)

    docs = {
        "pto_policy.md": fixed(PTO_POLICY, **PTO_2025),
        "remote_work_policy.md": fixed(REMOTE_WORK_POLICY),
        "expense_policy.md": fixed(EXPENSE_POLICY),
        "code_of_conduct.md": fixed(CODE_OF_CONDUCT),
        "on_call_policy.md": fixed(ON_CALL_POLICY),
        "employee_directory.md": employee_directory,
        "pto_policy_2022_archived.md": fixed(PTO_POLICY, **PTO_2022),
        "pto_faq_draft.md": fixed(PTO_FAQ_DRAFT),
    }
    for number, *args in TICKETS:
        docs[f"ticket-{number}.md"] = lambda d, n=number, a=tuple(args): ticket(d, n, *a)
    return docs


PTO_FAQ_DRAFT = (
    "PTO FAQ (draft)",
        """This draft answers common questions about paid time off. It was written before the 2025
        policy was final and has not been reviewed by People Operations, so some numbers may be
        out of date. Treat the PTO Policy as the source of truth.""",
        """## How many days do I get?

        The draft assumed 22 days per calendar year for full-time employees, with up to four
        days carried over. Check the current policy for the final numbers.""",
        """## How do I ask for time off?

        Use the people portal and give your manager a few days of notice. Your manager answers
        quickly in most cases, but long breaks around the end of a quarter are harder to
        approve.""",
        """## What about public holidays and company closures?

        Public holidays are free. The winter closure is free as well. If you work a public
        holiday, you may take a day in lieu later.""",
)


def render():
    files, manifest = {}, []
    for filename, build in builders().items():
        doc = Doc(filename)
        files[filename] = build(doc)
        manifest.extend(doc.entries)
    files["ground_truth.yaml"] = manifest_yaml(manifest)
    return files


def manifest_yaml(manifest):
    # JSON strings are valid YAML scalars, so no YAML library is needed to write the file.
    lines = ["# Generated by corpus/generate.py. Do not edit."]
    for entry in manifest:
        first = True
        for key in ("value", "entity_type", "doc", "normalized"):
            lines.append(("- " if first else "  ") + f"{key}: {json.dumps(entry[key])}")
            first = False
    return "\n".join(lines) + "\n"


def main(out_dir=OUT_DIR):
    for filename, content in render().items():
        (out_dir / filename).write_text(content)


if __name__ == "__main__":
    main()
