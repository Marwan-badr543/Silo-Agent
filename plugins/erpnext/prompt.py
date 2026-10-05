APPROVAL_PROMPT = """You are given a customer's reply to the question "Shall I go ahead and log this support ticket?".
Decide which of three answers it is:
- approved: a clear yes, even with extra details such as an email address.
- declined: a clear no or a change of mind.
- other: a question, a correction, or anything unclear.
Why: a ticket is created in the company's system, so when in doubt, choose other and never approved."""
