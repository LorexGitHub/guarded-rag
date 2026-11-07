# Ticket 1042: Export to CSV fails on large reports

**Customer:** Marcus Webb, marcus.webb@example.com, phone 555-010-0171. **Assigned to:** Tomas Berg (Support Agent), tomas.berg@example.com.

## Customer message

Hello, this is Marcus. My exports stop at about 10,000 rows and then the download shows a blank page. Could you look into this today? You can reach me on 555-010-0171 if a call is easier than email. Thank you.

## Agent notes

Tomas here. I reproduced the failure with a 12,000-row report and found a timeout in the export job. I then raised the timeout and re-ran the export; the full file downloaded. I wrote to Marcus at marcus.webb@example.com and offered a call back on 555-010-0171.

## Internal follow-up

Tomas checked whether other accounts were affected and found no more reports in the last seven days. The case was added to the knowledge base with the steps above, so that colleagues on the next shift can solve the same problem without asking the customer for details again. If it comes back, the incident template should be used and the on-call engineer informed through the paging tool.

## Resolution

The customer confirmed that the problem is solved. The ticket is closed and tagged for the weekly support review so that we can look for a pattern.
