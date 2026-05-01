Use gws CLI to add or view events in Google Calendar: $ARGUMENTS

## Usage

```
# Add event (natural language parsing)
/cal Team meeting tomorrow at 2pm for 1 hour
/cal 2026-05-01 10:00 Sprint review 2 hours --meet
/cal Tonight at 7pm dinner appointment location: Gangnam Station 1 hour

# View events
/cal today          → Today's events
/cal tomorrow       → Tomorrow's events
/cal week           → This week's events
/cal 3              → Events for the next 3 days

# Options
--meet              Automatically add Google Meet link
--attendee <email>  Add attendee (can be used multiple times)
--cal <ID>          Specify calendar (default: primary)
```

## Timezone

Default timezone: **Asia/Seoul (KST, UTC+9)**

## Procedure

### Step 1 — Parse Arguments

Analyze `$ARGUMENTS` to determine **view mode** vs **create mode**.

#### View Mode (when starting with these keywords)
| Input | gws Option |
|-------|-----------|
| `today` | `+agenda --today` |
| `tomorrow` / `tomorrow agenda` | `+agenda --tomorrow` |
| `week` | `+agenda --week` |
| Number N (standalone) | `+agenda --days N` |

→ View mode skips to **Step 4 (View)**.

#### Create Mode
Extract the following fields from natural language input:

| Field | Extraction Method | Default |
|-------|------------------|---------|
| `--summary` | Remaining text after removing date/time/duration | (required) |
| `--start` | Date + time → RFC3339 conversion | (required) |
| `--end` | start + duration (default 1 hour) → RFC3339 | start + 1 hour |
| `--location` | Text after `location:` or `at ` | (optional) |
| `--description` | Text after `description:` or `desc:` | (optional) |
| `--meet` | When `--meet` is included | not included |
| `--attendee` | `--attendee email` repeated | (optional) |
| `--calendar` | `--cal ID` | primary |

**Natural language date/time → RFC3339 conversion rules (KST basis)**:
- `today` → today's date (KST)
- `tomorrow` → tomorrow's date (KST)
- `day after tomorrow` → day after tomorrow's date (KST)
- `N am` → `THH:00:00+09:00`
- `N pm` → `T(N+12):00:00+09:00`
- `N:M` → `THH:MM:00+09:00`
- `YYYY-MM-DD` → use as-is
- Duration: `N hours` → end = start + N*3600 seconds, `N minutes` → end = start + N*60 seconds

---

### Step 1-B — Emoji Selection (Create Mode)

Analyze the summary text and select the single most fitting emoji to prepend to the title.

| Keywords (Korean/English) | Emoji |
|--------------------------|-------|
| meeting, standup, sync | 💬 |
| sprint, review, retro | 🔄 |
| lunch, dinner, breakfast, cafe, meal | 🍽️ |
| coffee | ☕ |
| workout, gym, run, yoga | 💪 |
| hospital, doctor, clinic, dentist, checkup | 🏥 |
| travel, flight, airport, business trip | ✈️ |
| birthday, anniversary | 🎂 |
| shopping, buy, purchase | 🛍️ |
| lottery, lotto | 🎰 |
| study, lecture, class, learning | 📚 |
| reading, book | 📖 |
| presentation, demo | 🎤 |
| interview | 🤝 |
| cleaning, laundry | 🧹 |
| medicine, pharmacy | 💊 |
| bank, transfer, exchange | 🏦 |
| drinking, bar, beer | 🍺 |
| concert, movie, show, exhibition | 🎭 |
| game | 🎮 |
| wedding | 💍 |
| check, confirm | 🔍 |
| other (no match) | 📌 |

Matching priority: search longer keywords before shorter ones. Prepend the matched emoji to the summary.  
Example: `buy lottery` → `🎰 buy lottery`, `team meeting` → `💬 team meeting`

---

### Step 2 — Confirm Parsed Result (Create Mode)

Show the extracted fields to the user and ask for confirmation:

```
📅 Confirm event to create

  Title:    💬 Team meeting
  Start:    2026-04-26T14:00:00+09:00  (tomorrow at 2pm KST)
  End:      2026-04-26T15:00:00+09:00  (1 hour)
  Location: (none)
  Notes:    (none)
  Meet:     No
  Calendar: primary

Create this event? (y/n)
```

If user responds `y` / `yes` → proceed to Step 3  
If user requests changes → update the relevant field and confirm again  
If user cancels → abort

---

### Step 3 — Create Event

Construct and run the gws command with the confirmed fields:

```bash
gws calendar +insert \
  --summary "<SUMMARY>" \
  --start "<START_RFC3339>" \
  --end "<END_RFC3339>" \
  [--location "<LOCATION>"] \
  [--description "<DESCRIPTION>"] \
  [--attendee "<EMAIL1>"] \
  [--attendee "<EMAIL2>"] \
  [--meet] \
  [--calendar "<CAL_ID>"]
```

On success, extract the event link (`htmlLink`) from the result and display:

```
✅ Event created successfully!

  Title:  Team meeting
  Start:  2026-04-26 14:00 KST
  End:    2026-04-26 15:00 KST
  Link:   https://calendar.google.com/event?eid=...
```

On failure, pass the error message and cause to the user.

---

### Step 4 — View Events

In view mode, run the following command:

```bash
gws calendar +agenda --today --timezone Asia/Seoul --format table
# or --tomorrow / --week / --days N
```

Show the results to the user as-is.

```
📅 Today's events (2026-04-25, KST)

  10:00  Team standup          30min
  14:00  Project review        1 hour
  ...
```

If no events: `📭 No events scheduled for today.`
