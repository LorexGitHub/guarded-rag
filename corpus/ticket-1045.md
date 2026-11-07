# Ticket 1045: Dashboard widgets load slowly

**Customer:** Sofia Lindqvist, sofia.lindqvist@example.com, phone +1 555 010 0174. **Assigned to:** Tomas Berg (Support Agent), tomas.berg@example.com.

## Customer message

Hello, this is Sofia. Since Monday the dashboard takes about a minute to show the usage widgets. Could you look into this today? You can reach me on +1 555 010 0174 if a call is easier than email. Thank you.

## Agent notes

Tomas here. I traced the delay to a slow query that ran without an index. I then added the index; widgets now load in under three seconds. I wrote to Sofia at sofia.lindqvist@example.com and offered a call back on +1 555 010 0174.

## Internal follow-up

Tomas checked whether other accounts were affected and found no more reports in the last seven days. The case was added to the knowledge base with the steps above, so that colleagues on the next shift can solve the same problem without asking the customer for details again. If it comes back, the incident template should be used and the on-call engineer informed through the paging tool.

## Resolution

The customer confirmed that the problem is solved. The ticket is closed and tagged for the weekly support review so that we can look for a pattern.
