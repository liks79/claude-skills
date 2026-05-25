# /email-archive — Analyze unread Gmail inbox, apply labels, and archive: $ARGUMENTS

Read `is:unread in:inbox` messages from `liks79@gmail.com` via the GWS CLI,
assign appropriate labels with AI, and archive them from the inbox.

## Usage

```
/email-archive              → Process up to 50 messages (default)
/email-archive --dry-run    → Preview only — no changes made
/email-archive 20           → Process up to 20 messages
/email-archive 20 --dry-run → Preview 20 messages
```

---

## Label Taxonomy

Assign each message one label from the table below.

| Label ID | Label Name | When to use |
|----------|------------|-------------|
| `Label_2036993981697889356` | 10.🪐 My World | Personal interests, hobbies, community news |
| `Label_4029957806261703169` | 20.📚 Read Later | General readable content (use when classification is unclear) |
| `Label_39` | 20.📚 Read Later/🗞️ Newsletter | Newsletters and subscription content |
| `Label_3060644997538026638` | 20.📚 Read Later/🎁 Promotion | Promotions, discounts, events (purchase-intent marketing) |
| `Label_4989369974426080235` | 20.📚 Read Later/📖 Medium | Emails from Medium.com and similar blog platforms |
| `Label_5689412040197905776` | 20.📚 Read Later/🔎 Info | Service notices, T&C changes, policy announcements |
| `Label_7628853138665668130` | 30.💼 Career | Recruitment/career-related (use when classification is unclear) |
| `Label_34` | 30.💼 Career/🤝 Referral | Referrals, introductions, networking |
| `Label_4797610418773993089` | 30.💼 Career/🌐 LinkedIn | Emails sent from LinkedIn |
| `Label_5358188143284424550` | 30.💼 Career/📦 Others | Job postings, headhunters, other job-search related |
| `Label_7509620340244847965` | 40.🔒 Security Alert | Security alerts, unusual logins, password change requests |
| `Label_41` | 50.💰 Finance | Finance-related (use when classification is unclear) |
| `Label_42` | 50.💰 Finance/🛍️ Purchases | Payment confirmations, order confirmations, shipping notifications |
| `Label_43` | 50.💰 Finance/🔄 Subscriptions | Subscription renewals, recurring payments, billing alerts |
| `Label_7631763767757303095` | 50.💰 Finance/ℹ️ Info | Bank, card, and investment account info notifications |
| `Label_1849097198608799370` | 50.💰 Finance/🧾 Tax Docs | Tax documents, year-end statements, tax invoices |
| `Label_48` | Notes | For manual note-saving (do not use for auto-classification) |

When no label fits clearly, fall back to `Label_4029957806261703169` (20.📚 Read Later).

---

## Procedure

### Step 1 — Parse arguments

From `$ARGUMENTS`:
- If a bare integer is present, set `MAX_RESULTS=<integer>` (default: 50, max: 100)
- If `--dry-run` is present, set `DRY_RUN=true` (default: false)

### Step 2 — Fetch unread inbox message list

```bash
gws gmail users messages list \
  --params "{\"userId\":\"liks79@gmail.com\",\"q\":\"is:unread in:inbox\",\"maxResults\":$MAX_RESULTS}" \
  2>/dev/null | jq '[.messages[].id]'
```

If no messages are returned, print "No unread messages to process." and exit.

### Step 3 — Fetch per-message metadata (parallel)

For each message ID, retrieve only headers and snippet:

```bash
gws gmail users messages get \
  --params "{\"userId\":\"liks79@gmail.com\",\"id\":\"<MSG_ID>\",\"format\":\"metadata\",\"metadataHeaders\":[\"From\",\"Subject\",\"Date\"]}" \
  2>/dev/null | jq '{id, snippet, headers: .payload.headers}'
```

Run in batches of 10 in parallel to increase throughput.

### Step 4 — AI label assignment

For each message, analyze `From`, `Subject`, and `snippet`, then select the best-matching label ID from the **Label Taxonomy** above.

**Assignment priority**:
1. Sender domain (linkedin.com → LinkedIn, medium.com → Medium, etc.)
2. Subject keywords (payment/order/shipping → Purchases, security/login → Security Alert, etc.)
3. Snippet content
4. Unable to classify → `Label_4029957806261703169` (Read Later)

Prepare the following fields for each message:
- `msg_id`: message ID
- `label_id`: label ID to assign
- `label_name`: human-readable label name
- `subject`: email subject
- `from`: sender
- `reason`: one-line rationale

### Step 5 — Apply changes

**If `DRY_RUN=true`**: skip modifications and go directly to Step 6.

**If `DRY_RUN=false`**: for each message:

```bash
gws gmail users messages modify \
  --params "{\"userId\":\"liks79@gmail.com\",\"id\":\"<MSG_ID>\"}" \
  --json "{\"addLabelIds\":[\"<LABEL_ID>\"],\"removeLabelIds\":[\"INBOX\",\"UNREAD\"]}" \
  2>/dev/null
```

Skip failed messages and record the error.

### Step 6 — Report results

Output in the following format:

```
## 📬 Email Archive Complete [or Preview]

Processed: N / M total
Mode: Applied [or DRY-RUN (preview only)]

| From | Subject | Label | Reason |
|------|---------|-------|--------|
| ... | ... | 20.📚 Read Later/🗞️ Newsletter | Newsletter format |
| ... | ... | 50.💰 Finance/🛍️ Purchases | Payment confirmation |
...

### Errors (if any)
- <msg_id>: <error details>
```

If `DRY_RUN=true`, add "(preview — not applied)" next to the title.
