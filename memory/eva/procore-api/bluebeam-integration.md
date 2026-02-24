# Bluebeam Revu Integration Research
**Research Date:** 2026-02-19  
**Purpose:** EVA-01 Submittal Agent — determine how to handle PDF stamping before Procore upload  
**Researcher:** MAGI Research Sprint (magi-bluebeam subagent)

---

## TL;DR (Executive Summary)

**Bluebeam does NOT have a server-side REST API for applying stamps to PDFs.** The Studio API handles collaborative Sessions and Projects (think cloud storage/collaboration), but there is no `/stamp-this-pdf` endpoint. Stamps are fundamentally a desktop Revu operation.

**Best path for EVA-01 today:** Programmatic stamping via Python (PyMuPDF + reportlab). The result is legally and professionally equivalent to a Bluebeam stamp. This is Option A.

**Fallback:** Option C — EVA-01 prepares the PDF, PM stamps it manually in Bluebeam, then confirms back to EVA-01 for upload. This requires human-in-loop but preserves Bluebeam stamps exactly.

---

## 1. Bluebeam API / SDK Landscape

### 1.1 Bluebeam Studio REST API ✅ (Exists but limited scope)

**Base URL:** `https://api.bluebeam.com/publicapi/v1/`  
**Auth:** OAuth 2.0 (authorization code flow, requires BBID account)  
**Docs:** `https://developers.bluebeam.com` | `https://support.bluebeam.com/developer/`  
**Access:** Must request via form (24-48hr review). Available in US, AU, DE, UK, SE.

The API has **three functional areas**:

#### Studio Sessions API
A "digital conference room" for collaborative PDF markup. Workflow:
1. Create Session (`POST /sessions`)
2. Upload PDF to Session (3-step: metadata → AWS S3 PUT → confirm)
3. Add users (invite or add via email)
4. Finalize: create Snapshot (merges markups + PDF), download, close Session

**Stamp via Sessions?** ❌ No. Sessions allow humans to apply markups collaboratively in Revu. The API can initiate/finalize sessions and retrieve the marked-up PDF snapshot, but cannot programmatically apply a stamp on the server. The stamp would need to be applied by a human Revu user during the session.

#### Studio Projects API
Cloud document storage (like Google Drive for Bluebeam files).

**File Jobs:** The legacy Bluebeam Developer Network docs (now archived at bbdn.bluebeam.com) mentioned that Studio Projects had "File Jobs" for server-side processing tasks including: "converting to PDF, adding a stamp, or rotating pages." **However:**
- The BBDN site now returns 404 for most content (legacy platform)
- This functionality was tied to having Revu installed on a client machine that processes jobs — it was NOT a pure server-side operation
- The new Developer Portal (`developers.bluebeam.com`) does not document a stamp job endpoint
- Current Studio Projects API focuses on file management, not PDF processing

**Conclusion on Jobs API:** Uncertain/deprecated. The stamp job functionality described in legacy docs likely required a Revu client to execute. Not a viable server-side API path.

#### Studio Projects - New Platform (2024)
Bluebeam migrated to a new API platform in 2024. Old routes:
- `https://studioapi.bluebeam.com:443/publicapi/v1` → now `https://api.bluebeam.com/publicapi/v1`

The new platform appears to focus on Sessions + Projects file management + OAuth. No new stamp/processing endpoint has been documented.

### 1.2 Bluebeam JavaScript API ❌ (Not useful for EVA-01)

Bluebeam supports PDF-embedded JavaScript (per Adobe PDF spec). This allows:
- Interactive dynamic stamps (auto-fill date, prompt for user input)
- Form field automation within Revu

This is **not a REST API** and requires Revu to execute. Useful for creating smart stamp templates for human users, not for server-side automation.

### 1.3 Bluebeam Revu Desktop — Command Line ❌ (No PDF processing)

`PbMngr5.exe` offers CLI access for admin functions only:
- License/registration management
- Settings backup/restore
- Gateway seat management

**No CLI for PDF stamping or batch markup application.**

### 1.4 Bluebeam Q (Legacy Server Product) ⚠️ (Discontinued)

Bluebeam Q was a server-side PDF processing product (~2011 era) with:
- Watched folder processing
- Script engine for batch operations (stamps, headers/footers, flatten)
- REST-like API for job submission

**Status: Appears discontinued.** No current downloads, no references to active support. Absorbed or discontinued when Bluebeam pivoted to cloud/Studio. Do not build on this.

### 1.5 Bluebeam Gateway / Bluebeam Cloud

- **Gateway:** Licensing server for on-premise Revu deployments. Not a PDF processing API.
- **Bluebeam Cloud / Bluebeam for Web:** Web-based PDF viewer/markup tool (2024). Still requires human interaction for stamp placement. No automation API.

---

## 2. What Bluebeam's API Actually Enables

| Capability | Via API? | Notes |
|------------|----------|-------|
| Create Studio Session | ✅ | Full CRUD |
| Upload PDF to Session | ✅ | 3-step S3 upload |
| Add/invite users to Session | ✅ | Email-based |
| Apply a stamp to PDF | ❌ | Must be done by human in Revu |
| Flatten markups to PDF content | ❌ | Must be done by human in Revu |
| Download marked-up PDF snapshot | ✅ | Combines markup layer + PDF |
| Convert to PDF, rotate pages (Jobs) | ⚠️ | Documented in legacy BBDN; unclear on current platform |
| Manage Studio Projects/files | ✅ | File CRUD |
| Server-side headless stamping | ❌ | Not available |

---

## 3. Programmatic Stamping — Python Alternatives

These approaches work entirely without Bluebeam and produce standard PDF output.

### 3.1 PyMuPDF (fitz) — **Recommended**

```python
import pymupdf  # pip install pymupdf

doc = pymupdf.open("submittal.pdf")
page = doc[0]  # First page

# Insert stamp image (PNG with transparency)
stamp_rect = pymupdf.Rect(400, 50, 600, 150)  # position on page
page.insert_image(stamp_rect, filename="approval_stamp.png", overlay=True)

# Add text fields
page.insert_text(pymupdf.Point(410, 90), f"Received: {date}", fontsize=9, color=(0,0,0))
page.insert_text(pymupdf.Point(410, 102), f"Submittal #: {number}", fontsize=9)

doc.save("submittal_stamped.pdf")
```

**Capabilities:**
- Insert PNG/JPG image stamp at any position/size
- Add text overlays (date, submittal #, status)
- Insert PDF annotation of type "Stamp" (PDF spec compliant)
- Flatten to content stream (permanent, non-editable)
- Works headless, no GUI required
- Fast: milliseconds per page

**Stamp types supported:**
- `page.insert_image()` — bitmap image (PNG with alpha for transparent background)
- `page.add_stamp_annot()` — standard PDF stamp annotation (APPROVED, DRAFT, etc.)
- `page.insert_text()` or `page.insert_textbox()` — text overlays

### 3.2 reportlab — For creating stamp PDFs

```python
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Create stamp overlay PDF
c = canvas.Canvas("stamp_overlay.pdf")
c.setPageSize((8.5*inch, 11*inch))
c.drawImage("company_logo.png", 5*inch, 9*inch, width=3*inch, height=1.5*inch)
c.setFont("Helvetica-Bold", 12)
c.drawString(5*inch, 8.8*inch, "REVIEWED")
c.drawString(5*inch, 8.6*inch, f"Date: {date}")
c.save()

# Then merge with pypdf
from pypdf import PdfReader, PdfWriter
stamp_pdf = PdfReader("stamp_overlay.pdf")
submittal_pdf = PdfReader("submittal.pdf")
writer = PdfWriter()
for page in submittal_pdf.pages:
    page.merge_page(stamp_pdf.pages[0])
    writer.add_page(page)
with open("stamped.pdf", "wb") as f:
    writer.write(f)
```

### 3.3 pypdf (formerly PyPDF2) — Merge/overlay approach

Good for merging a pre-built stamp PDF over each page of the submittal.

### 3.4 Approach Comparison

| Tool | Use Case | Pros | Cons |
|------|----------|------|------|
| PyMuPDF | All-in-one stamp + text | Fast, flexible, handles complex PDFs | Slightly more code |
| reportlab + pypdf | Stamp as separate PDF | Easy template management | Two-library dependency |
| pdf-lib (JS/Node) | If EVA-01 runs Node | Good for JS environments | Less Python-native |

---

## 4. Legal & Professional Equivalence

### Is the stamp legally required?

**Yes, effectively.** Under AIA A201-2017 (General Conditions), the GC must review and certify submittals before forwarding to the design professional. AIA B101 specifies how design professionals respond. The stamp is:

1. **Contractually required** — AIA contracts establish the stamp as the GC's certification of review
2. **Industry standard** — Without a stamp, the submittal is often returned
3. **Legal record** — The stamp status (Approved / Approved as Noted / Revise and Resubmit / Rejected) becomes part of the contract record
4. **Not a government seal** — It's a professional/business stamp, not a licensed engineer's PE seal. No regulatory body specifies the exact format.

### Is a programmatic stamp equivalent to a Bluebeam stamp?

**Yes, for all practical and legal purposes**, provided:
- The stamp contains the required content (company name, authorized signature image, date, submittal #, review status)
- It is permanently embedded (flattened into content, not just an annotation layer)
- It matches the visual format the GC's clients expect

Bluebeam stamps are PDF annotations internally — there is nothing proprietary about the stamp format. A PyMuPDF-generated stamp with the same content is legally identical.

**Caveat:** Some GCs have specific stamp *templates* they've shared with their supply chain. EVA-01 should be able to replicate these exactly as PNG overlays.

---

## 5. What GCs Actually Use

### Bluebeam Revu — Dominant in AEC/Construction

- **Market position:** The de facto standard PDF tool in US construction/AEC. Extremely high penetration among GCs and subcontractors.
- **Common versions in 2024-2026:** Revu 20, Revu 21 (subscription), Revu 2024. Many firms still on Revu 20 (perpetual license, end-of-life support).
- **Why it dominates:** Measurement tools, batch stamp/markup, Studio collaboration, Procore/Autodesk integrations, custom stamps — all purpose-built for construction.

### Other Tools in Use

| Tool | Usage | Stamp Capable? |
|------|-------|---------------|
| Adobe Acrobat Pro | Common fallback, smaller firms | Yes (custom stamps) |
| Autodesk Docs / BIM 360 | Large GCs on Autodesk stack | Limited stamp tools |
| PlanGrid (Autodesk) | Field-focused, less common for submittals | Basic |
| Procore native PDF | Within Procore itself | Very limited |
| Foxit PDF | Some firms, cheaper alternative | Yes |

**Bottom line:** Bluebeam is primary, Adobe Acrobat is common fallback. Both accept any standard PDF stamp.

---

## 6. Recommended Integration Options for EVA-01

### Option A: EVA-01 Stamps Programmatically ✅ **RECOMMENDED**

**How:** EVA-01 uses PyMuPDF to overlay a pre-designed stamp image (PNG) on the first page of each submittal PDF before uploading to Procore.

**Stamp content (auto-populated by EVA-01):**
- Company logo / approval stamp image (PNG, provided once by client)
- PM name / signature image (from PM profile)
- Date received (auto-filled)
- Submittal number (from EVA-01's submittal log)
- Review status (Approved / Approved as Noted / Revise & Resubmit / Rejected)

**Pros:**
- Fully automated, no human in loop
- Works immediately, no Bluebeam subscription needed
- Legally equivalent
- Fast (< 1 second per PDF)
- Can match client's existing stamp template exactly

**Cons:**
- Requires one-time setup of stamp template per client
- PM needs to verify stamp looks correct the first time

**Implementation complexity:** Low (1-2 days of dev)

---

### Option B: EVA-01 via Bluebeam API → Stamped PDF ❌ **NOT VIABLE**

Bluebeam's Studio API does not expose a server-side stamp endpoint. Would require human interaction in Revu.

---

### Option C: EVA-01 Orchestrates PM Stamp in Bluebeam ⚠️ **FALLBACK**

**How:** EVA-01:
1. Downloads/receives submittal PDF
2. Prepares a Studio Session with the PDF
3. Notifies PM ("Please open this session in Bluebeam and apply your approval stamp")
4. PM opens in Bluebeam, applies stamp, saves
5. EVA-01 polls the Session for a finalized snapshot
6. EVA-01 downloads the stamped PDF and uploads to Procore

**Pros:**
- Uses actual Bluebeam stamps (100% client familiarity)
- No stamp replication needed

**Cons:**
- Requires human PM action for every submittal
- Latency: PM must manually open Bluebeam (kills automation goal)
- Requires client to have active Bluebeam subscription + Studio
- EVA-01 must manage Studio Session lifecycle
- PM might forget/delay; EVA-01 needs follow-up logic

**Use when:** Client explicitly requires Bluebeam stamps and won't accept programmatic alternative.

---

### Option D: Bluebeam Studio Webhook/Automation ❌ **NOT VIABLE**

Bluebeam does not offer outbound webhooks or event-driven automation from Studio. No pub/sub or callback system documented.

---

### Option E: Hybrid — PM Pre-signs Stamp Template ✅ **PRACTICAL VARIANT**

One-time setup: PM signs a stamp image (physical signature → scan → PNG, or digital signature image). EVA-01 stores this signed stamp PNG per PM.

Then Option A runs fully automatically using the pre-signed stamp image. This is the cleanest approach and can be launched immediately.

---

## 7. Implementation Plan for EVA-01 (Option A)

### Step 1: Stamp Template Setup (Per Client)

Client provides (or EVA-01 requests during onboarding):
- Company logo PNG (transparent background preferred)
- PM's signature image (PNG)
- Desired stamp dimensions and position (default: upper-right of first page)
- Status options used (Approved / A as Noted / R&R / Rejected)

Store in EVA-01's profile store: `/memory/eva/clients/{client_id}/stamp-config.json`

### Step 2: Stamp Application Function

```python
# eva_stamp.py
import pymupdf
from datetime import date
from pathlib import Path

def apply_submittal_stamp(
    pdf_path: str,
    output_path: str,
    stamp_image_path: str,   # PNG of the overall stamp background
    signature_image_path: str,  # PM signature PNG
    submittal_number: str,
    review_status: str,  # "APPROVED", "APPROVED AS NOTED", "REVISE & RESUBMIT", "REJECTED"
    pm_name: str,
    stamp_position: tuple = (420, 30, 590, 140),  # (x0, y0, x1, y1) on first page
):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    
    rect = pymupdf.Rect(*stamp_position)
    
    # Draw stamp background/border box
    page.draw_rect(rect, color=(0.2, 0.2, 0.6), width=2)
    
    # Insert company stamp image
    stamp_rect = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 40)
    page.insert_image(stamp_rect, filename=stamp_image_path, overlay=True)
    
    # Insert signature
    sig_rect = pymupdf.Rect(rect.x0 + 5, rect.y0 + 45, rect.x0 + 80, rect.y0 + 75)
    page.insert_image(sig_rect, filename=signature_image_path, overlay=True)
    
    # Insert text fields
    text_x = rect.x0 + 5
    page.insert_text(pymupdf.Point(text_x, rect.y0 + 80), f"Status: {review_status}", fontsize=8, color=(0.8, 0, 0))
    page.insert_text(pymupdf.Point(text_x, rect.y0 + 92), f"Submittal #: {submittal_number}", fontsize=8)
    page.insert_text(pymupdf.Point(text_x, rect.y0 + 104), f"Date: {date.today().strftime('%m/%d/%Y')}", fontsize=8)
    page.insert_text(pymupdf.Point(text_x, rect.y0 + 116), f"Reviewed by: {pm_name}", fontsize=8)
    
    doc.save(output_path)
    doc.close()
```

### Step 3: Integration into EVA-01 Workflow

```
Submittal email arrives
  → EVA-01 extracts PDF attachment
  → EVA-01 logs submittal (number, date, status)
  → EVA-01 calls apply_submittal_stamp() with PM's stored stamp config
  → EVA-01 uploads stamped PDF to Procore (using existing Procore API integration)
  → EVA-01 notifies PM: "Submittal #X stamped and uploaded to Procore ✅"
```

---

## 8. What's Possible Today vs. What Needs Vendor Support

### Today (No Bluebeam Needed)
- ✅ Programmatic stamp application (PyMuPDF)
- ✅ Custom stamp templates matching client's Bluebeam stamps visually
- ✅ Auto-fill date, submittal number, PM name
- ✅ Status overlay (Approved/Rejected/etc.)
- ✅ Flatten to PDF content (permanent)
- ✅ Works with any PDF viewer, not Bluebeam-specific

### Requires Bluebeam Subscription
- ⚙️ Option C workflow (PM manually stamps in Revu)
- ⚙️ Studio Session management (if client insists on Bluebeam-native stamps)

### Would Need Bluebeam to Build (Not Feasible Today)
- ❌ True server-side Bluebeam stamp via API
- ❌ Webhook notifications from Bluebeam when stamp is applied

### Possible Future Path (Contact Bluebeam)
- 📧 `integrations@bluebeam.com` — could request a partner integration with server-side stamp capability
- Bluebeam has a formal partner program; a "stamp via API" endpoint would likely need them to build it as a product feature
- Timeline: Unknown, likely 6-18 months if they're interested

---

## 9. Key References

| Resource | URL |
|----------|-----|
| Bluebeam Developer Portal | https://developers.bluebeam.com |
| Studio Session API Guide | https://support.bluebeam.com/developer/studio-session-guide.html |
| Bluebeam Developer Getting Started | https://support.bluebeam.com/developer/getting-started-dev-portal.html |
| Develop Integrations Overview | https://support.bluebeam.com/integrations/develop-integrations.html |
| Bluebeam JS API | https://support.bluebeam.com/developer/javascript/javascript.html |
| Bluebeam Submittal Tracking (Cloud) | https://support.bluebeam.com/articles/how-to-track-submittals-in-bluebeam-cloud/ |
| PyMuPDF Docs (Annotations) | https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html |
| AIA Submittal Legal Reference | https://www.allensworthlaw.com/legal-updates/submittal-considerations-for-design-professionals/ |
| AIA A201 Contractor Submittal Obligations | https://learn.aiacontracts.com/articles/6480362-does-a-contractor-need-to-review-its-subcontractors-submittals/ |
| Developer Contact | integrations@bluebeam.com |

---

## Appendix: Bluebeam Studio API Auth Flow (For Option C)

If implementing Option C (PM stamps in Studio), EVA-01 needs:

1. Register app at `https://developers.bluebeam.com` (OAuth 2.0, client_id + secret)
2. Implement OAuth authorization code flow on behalf of PM's BBID account
3. Call `POST /publicapi/v1/sessions` to create session
4. Upload PDF: POST metadata → PUT to S3 → POST confirm-upload
5. Invite PM via `POST /publicapi/v1/sessions/{id}/invite`
6. Poll `GET /publicapi/v1/sessions/{id}/files/{id}/snapshot` until Status=Complete
7. Download snapshot (marked-up PDF), pass to Procore upload
8. DELETE session to clean up

**Complexity:** Medium-High. OAuth refresh tokens needed for long-running agent. PM must have BBID account.

---

*Research complete. Confidence: High. Sources: Bluebeam official documentation, Developer Network (legacy), AIA contract resources, PyMuPDF documentation, industry community forums.*
