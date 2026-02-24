# EVA-01 Killer Feature: One-Touch Submittal Creation
> Defined: 2026-02-19 — This is THE feature that sells EVA-01.

## The Scenario
PM is walking the site. Gets an email with a shop drawing PDF from a sub.
Opens Telegram. Sends the PDF to EVA-01.

## The Workflow (One Message In, One Tap to Approve)

### Step 1: PM Sends Submittal (5 seconds)
Two intake channels — same pipeline on the backend:

**Channel A: Email Forward (preferred for older PMs — zero learning curve)**
- PM gets email from sub with shop drawing attached
- PM hits Forward → types `submittals@clientname.nerv.ai` (autocomplete after first use)
- EVA-01 picks up via IMAP, parses email + all attachments
- **Bonus data from email**: sender name/company (auto-fills vendor), subject line (description), email body (spec refs, revision notes), timestamp (received date), multiple attachments in one go

**Channel B: Telegram (preferred for younger/tech-savvy PMs)**
- PM sends PDF directly to EVA-01 in Telegram
- Can include a note ("this is from ABC Mechanical for the RTUs") or just send the file
- Faster for PMs who already have Telegram open

### Step 2: EVA-01 Analyzes & Reports (30-60 seconds, automatic)
- Extract text, metadata, manufacturer info via PyMuPDF
- Identify document type: shop drawing, product data, sample, test report
- Match to spec section from project spec list
- Cross-reference against project drawings (via EVA-00's drawing index)
- Check consistency with specifications
- Flag obvious issues: wrong product, missing pages, incomplete data
- Compare against historical submittals for similar items (via EVA-00)
- Identify responsible contractor/vendor from content or PM's note

### Step 3: EVA-01 Presents Report + Asks for Approval
EVA-01 replies in Telegram with:
- **Document type**: "Shop Drawing — RTU Units"
- **Spec match**: "Section 23 81 00 — Decentralized Unitary HVAC"
- **Vendor**: "ABC Mechanical"
- **Flags**: "All 3 units match schedule on M-401. Lead time not included."
- **Proposed title**: "RTU Shop Drawings"
- **Proposed submittal #**: "V-5-RTU_Shop_Drawings"
- **[Approve ✅]** button — one tap

### Step 4: PM Taps Approve (1 second)
- Single tap on the Approve button in Telegram
- PM can also reply with corrections ("change title to..." or "wrong vendor, it's XYZ")

### Step 5: EVA-01 Stamps & Creates (automatic, ~30 seconds)
- **Stamps PDF**: Applies received stamp (date, submittal number, company mark) programmatically
- **Creates Procore draft submittal** with all fields populated:
  - Title, description, spec section ID
  - Received from, responsible contractor
  - Received date (today)
  - Submittal number
- **Attaches stamped PDF** via `PATCH submittal[attachments][]`
- **Confirms to PM**: "Draft submittal created: [Title] — [Procore link]"
- "Assign reviewers and open for review when ready."

### Step 6: PM Finishes in Procore (1-2 minutes, when convenient)
- Opens Procore link (can be later, doesn't have to be immediate)
- Reviews EVA-01's work
- Assigns reviewers/approvers (API limitation — PM's job)
- Opens submittal for review
- Done. Back to the field.

**Total PM time: ~2 minutes. Previous workflow: 30-45 minutes at a desk.**

## What's Confirmed Working (API-Proven)
- ✅ PDF upload to submittal via `PATCH submittal[attachments][]`
- ✅ Submittal creation with title, description, spec section ID
- ✅ Vendor matching from project vendor list (118 vendors in sandbox)
- ✅ User matching from project user list (554 users in sandbox)
- ✅ Text extraction from PDFs via PyMuPDF ($0, instant)

## What PM Still Does (Can't Be Automated)
- ❌ Assign submittal approvers/reviewers (API limitation)
- ❌ Open submittal for review workflow (API limitation)
- ❌ Final spec section confirmation (agent suggests, PM confirms)
- ❌ Create new spec sections (UI only, no API)

## Why This Sells
- **Time savings**: 30-45 min desk work → 2 min on phone
- **No context switching**: PM doesn't leave the field
- **Consistency**: Every submittal follows the same format
- **History**: EVA-01 learns from past submittals (via EVA-00)
- **Compliance**: Basic review catches obvious errors before architect sees it
- **The pitch**: "Your PM sends a PDF from the field, and 60 seconds later there's a draft submittal in Procore with the shop drawing attached, spec section matched, and a compliance report. All they do is assign reviewers and click submit."

## Technical Pipeline

```
[PM sends PDF via Telegram]          [PM forwards email]
         ↓                                    ↓
[OpenClaw Telegram channel]    [IMAP pickup → parse sender, subject, body]
         ↓                                    ↓
         └──────────── MERGE ─────────────────┘
                        ↓
         [PyMuPDF: extract text, metadata, links]
                        ↓
         [Query EVA-00: match spec section, find related drawings, check history]
                        ↓
         [Generate compliance report]
                        ↓
         [Send report to PM via Telegram/email → [Approve ✅] button]
                        ↓
         [PM taps Approve]
                        ↓
         [Stamp PDF: received date + submittal # + company mark]
                        ↓
         [Rename file: {Project} - {Title} - {Date}.pdf]
                        ↓
         [Procore API: Create submittal draft]
            POST /projects/{id}/submittals
            Body: {title, description, spec_section_id, received_from_id, responsible_contractor_id}
                        ↓
         [Procore API: Attach stamped PDF]
            PATCH /projects/{id}/submittals/{sub_id}
            multipart: submittal[attachments][] = stamped_file.pdf
                        ↓
         [Confirm to PM: "Draft created" + Procore link]
```

## Intake Architecture

### Email Intake (per NERV deployment)
- Each client gets a dedicated email: `submittals@{client}.nerv.ai` (or Gmail alias)
- IMAP polling every 30-60 seconds (or push via webhook if available)
- Parse email: sender → vendor match, subject → title, body → description/notes, timestamp → received date
- Extract ALL attachments (not just first — subs often send multiple files)
- Reply to PM via their preferred channel (Telegram or email reply)

### Telegram Intake
- PM sends file(s) directly to EVA-01 bot
- Optional text message parsed for context
- Inline buttons for approve/reject/edit

### File Naming Standard
All files renamed on intake to: `{Project} - {Title} - {Date}.pdf`
Example: `BTV5 - RTU Shop Drawings - 2026-02-19.pdf`
If multiple files: `BTV5 - RTU Shop Drawings - 2026-02-19 (1 of 3).pdf`

### Stamping
Before upload to Procore, EVA-01 applies received stamp to PDF:
- Company name/logo
- Date received
- Submittal number
- "RECEIVED FOR REVIEW" mark
Method: Programmatic via PyMuPDF overlay (or Bluebeam API if available — MAGI researching)

## Dependencies
- EVA-00 must be running (historical data, spec matching, drawing cross-ref)
- Procore OAuth token must be valid (auto-refresh cron)
- Project spec sections must be pre-loaded (SEELE onboarding task)
- Project vendor list must be synced
- Dedicated email address per deployment (SEELE onboarding task)

## Priority
🔴 **HIGHEST** — This is the feature demo that closes deals.
Build this BEFORE anything else on EVA-01.
