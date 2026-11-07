# On-Call Policy

Some Acme Example services must stay available day and night. Engineers who run these services share an on-call rotation. This policy describes how the rotation works, what the company pays for it, and what you can expect when your pager goes off.

## Rotation

Each rotation lasts one week, from Monday at 10:00 to the next Monday at 10:00. Every team keeps at least five people in its rotation, so nobody is on call more than one week in five. Swap shifts with a teammate by changing the schedule in the paging tool, and tell your manager when you do.

## Response times

The primary engineer acknowledges a page within ten minutes and starts working on a severity one incident within thirty minutes. A secondary engineer is paged if the primary does not acknowledge. Keep a laptop and a stable connection within reach for the whole week, and do not plan travel that makes this impossible.

## Pay and time off

On-call engineers receive a weekly allowance of 350 euros, plus overtime pay for any incident work outside normal hours. After a night with more than two hours of incident work, take the next morning off without using paid time off. Public holidays on call earn a day in lieu, as the PTO policy explains.

## After an incident

Within three working days of a severity one or two incident, the primary engineer writes a blameless review. The review lists the timeline, the cause, and the follow-up work with owners. Share it with the team and add the actions to the backlog.

## Handover and documentation

At the end of each rotation the outgoing engineer writes a short handover note in the team channel: open incidents, flaky alerts, planned deploys and anything unusual. The incoming engineer reads it before the rotation begins and asks questions in the handover call on Monday morning. Runbooks live in the team wiki and are updated whenever a page turns out to be missing a step. Alerts that wake someone without needing action are tuned or deleted within two weeks.

## Questions

The rotation owner is Diego Alvarez, reachable at diego.alvarez@example.com. Escalations and exceptions go to Will Hunt at will.hunt@example.com.
