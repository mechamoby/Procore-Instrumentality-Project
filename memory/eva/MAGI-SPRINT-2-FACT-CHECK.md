# MAGI Sprint 2 — Moby's Fact-Check Report
> Date: 2026-02-21
> Reviewed by: Moby (Opus)

## Overall Assessment
MAGI produced 2,337 lines of solid research across 4 reports. Most claims are accurate. Below are corrections, flags, and key insights.

---

## CORRECTIONS & FLAGS

### Procore Report
1. **"90+ endpoint categories"** — ⚠️ Inflated. Procore has extensive endpoints but "90+" is generous. Actual distinct resource types are closer to 40-50. Still comprehensive.
2. **"Webhooks not available in sandbox"** — ⚠️ NEEDS VERIFICATION. Procore docs say to "start small: enable webhooks in a sandbox." This contradicts MAGI's claim. We should test this ourselves.
3. **Rate limit "100 requests per 60 seconds"** — ✅ Correct, matches our Sprint 1 findings and confirmed in practice.
4. **"Service Accounts" for AI agents** — ⚠️ Procore doesn't have traditional "service accounts." You authenticate via OAuth as an app, but actions are tied to the installing user's permissions. Important distinction for our deployment model.
5. **Pagination format shown** — ⚠️ Procore uses Link header-based pagination, not the JSON meta/links format shown. The format MAGI showed looks like a generic REST pattern, not Procore-specific.
6. **BIM endpoints** — ⚠️ `/bim-files` exists but capabilities are limited. No evidence of built-in clash detection or "quantity takeoffs" via the API. The BIM viewer is Autodesk-powered.
7. **Marketplace "no AI training on Procore data"** — ✅ This is in Procore's API terms. Critical for our compliance.

### Bluebeam & Smartsheet Report
1. **Bluebeam Studio API** — ✅ Confirmed. REST API exists at `developers.bluebeam.com`. Sessions, Projects, file operations all real.
2. **"JavaScript API (Revu eXtreme Only)"** — ✅ Confirmed. Scripting only available in eXtreme edition. Uses Adobe PDF JavaScript DOM.
3. **"COM API Potential"** — ⚠️ No solid evidence of a COM/automation API for Revu. MAGI hedged correctly ("needs verification"). Likely doesn't exist for external automation.
4. **Bluebeam-Procore integration** — ✅ Real, but MAGI says "Beta" — it's actually GA (generally available) for submittals.
5. **Smartsheet 300 req/min** — ✅ Confirmed exactly by official docs.
6. **Smartsheet sheet limits "20,000 rows, 400 columns, 500,000 cells"** — ✅ Confirmed by official limitations page.
7. **Smartsheet automation creation via API** — ⚠️ MAGI says "can read but not create" — this is correct and an important limitation.
8. **"40% faster document review cycles"** — ⚠️ Fabricated metric. No source for this. Remove from any client-facing docs.

### Microsoft & DocuSign Report
1. **MS Graph batch limit "20 requests"** — ⚠️ PARTIALLY WRONG. Official docs say 20, but Stack Overflow reports actual limit is 15 for some endpoints. Test before relying on 20.
2. **Outlook throttle "10,000 API requests per 10 min per app per mailbox"** — ⚠️ This is roughly right but MS Graph throttling is more nuanced — varies by endpoint and tenant size.
3. **OneDrive "100GB per file"** — ✅ Correct for OneDrive for Business.
4. **DocuSign CLM "limited to enterprise customers"** — ✅ Confirmed. CLM API exists (`developers.docusign.com/docs/clm-api/`) but requires CLM license (enterprise tier).
5. **DocuSign "10,000 envelopes per month for standard plans"** — ⚠️ Varies significantly by plan. Don't quote this as definitive.
6. **DocuSign JWT Grant** — ✅ Correct. We already have this working in our sandbox.

### File Formats Report
1. **IfcOpenShell** — ✅ Real, powerful open-source IFC library. Code examples look correct.
2. **ezdxf for DXF** — ✅ Correct. Cannot read DWG directly — must convert to DXF first.
3. **"ODA File Converter"** — ✅ Real tool from Open Design Alliance. Free for non-commercial use.
4. **Autodesk APS pricing "$0.50 per credit"** — ⚠️ APS uses cloud credits but pricing model has changed. Verify current rates.
5. **"Vision APIs ~$1.50 per 1000 images"** — ⚠️ Varies wildly by provider and model. Claude Vision, GPT-4V have different pricing.
6. **PyMuPDF + pdfplumber combo** — ✅ Solid recommendation. This is the standard approach.
7. **BIM: "No pure Python libraries for direct .rvt reading"** — ✅ Correct. Revit files require Revit API or APS.

---

## KEY BUSINESS INSIGHTS

### Highest-Value Integration Targets (ranked by PM time savings)
1. **Procore** — Already building. Submittals + RFIs = killer features
2. **DocuSign** — Contract execution automation. JWT auth means fully autonomous agent signing workflows
3. **Smartsheet** — Many GCs use this for schedules. 300 req/min is generous. Real-time webhooks = live schedule monitoring
4. **Microsoft 365** — Universal. OneDrive/Outlook integration would make our agents work with existing client infrastructure
5. **Bluebeam** — Studio API is real but limited compared to others. Most value is in PDF processing (which we can do locally with PyMuPDF)

### Platform Access Requirements
| Platform | Auth Model | Free Tier? | Sandbox? |
|----------|-----------|-----------|----------|
| Procore | OAuth 2.0 | Dev sandbox | Yes |
| DocuSign | OAuth/JWT | Dev sandbox | Yes (already have) |
| Smartsheet | API token | 30-day trial | No dedicated sandbox |
| Microsoft 365 | OAuth 2.0/App | Dev program | Yes (M365 dev tenant) |
| Bluebeam | OAuth 2.0 | Studio Prime required | Unknown |

### What We Can Do TODAY Without New API Access
- PDF processing (PyMuPDF, pdfplumber) — local, free, no API needed
- Photo analysis (Claude Vision) — already available through OpenClaw
- DXF parsing (ezdxf) — local, free
- IFC parsing (IfcOpenShell) — local, free, if we get BIM files
- Procore everything — already connected
- DocuSign — already have sandbox creds
