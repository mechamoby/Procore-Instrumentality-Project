# MAGI Research Report: PM Document Management
## Best Practices, Industry Standards, Types & Tricks
> Compiled: 2026-02-25 01:00 AM
> Sources: Procore Library, CSI MasterFormat 2020, Autodesk, ProjectManager, Pericent, StruxHub, GSourceData, NSPE, Florida Statutes

---

## 1. Complete Document Types in Construction

### Pre-Construction Documents
- **Bid packages** — Invitation to bid, instructions to bidders, bid forms
- **Estimates** — Cost estimates, quantity takeoffs, bid tabulations
- **Contracts** — Prime contract, subcontracts, purchase orders (AIA standard forms: A101, A201, etc.)
- **Insurance certificates** — COIs from all parties, builders risk
- **Bonds** — Performance bonds, payment bonds, bid bonds
- **Permits** — Building permits, environmental permits, zoning approvals, NOC (Notice of Commencement)
- **Surveys & geotechnical** — Site surveys, soil boring reports, environmental assessments

### Design Documents
- **Architectural drawings** — Plans, elevations, sections, details
- **Engineering drawings** — Structural, mechanical, electrical, plumbing, fire protection (MEPF)
- **Specifications** — Project manual organized by CSI MasterFormat divisions
- **Addenda** — Pre-bid clarifications/modifications to contract documents
- **ASIs (Architect's Supplemental Instructions)** — Post-bid design clarifications that don't affect cost/time
- **Bulletins** — Design revisions issued by the architect (some firms use interchangeably with ASIs)

### Construction Phase Documents
- **Submittals** (three categories):
  - **Action submittals** — Require architect review/approval: shop drawings, product data, samples, mockups, engineering calculations, product cutsheets, color charts
  - **Informational submittals** — For record only: test reports, certificates, manufacturer instructions, field measurements
  - **Closeout submittals** — End of project: warranties, O&M manuals, as-built drawings, attic stock lists, LEED documentation
- **RFIs (Requests for Information)** — Formal questions to design team about design intent, conflicts, or missing info
- **Transmittals** — Cover sheets documenting formal transfer of documents between parties
- **Change Orders** — CORs (Change Order Requests), PCOs (Potential Change Orders), CO packages, bulletins with cost impact
- **Daily Reports/Logs** — Weather, manpower, work performed, delays, visitors, safety observations
- **Meeting Minutes** — OAC meetings, subcontractor coordination, safety meetings, internal
- **Inspection Reports** — Third-party testing, municipal inspections, special inspections (concrete, steel, fireproofing)
- **Safety Documents** — Safety plans, toolbox talks, incident reports, OSHA logs, JSAs/JHAs
- **Schedule** — Baseline CPM schedule, monthly updates, look-aheads (2-week, 3-week), recovery schedules
- **Photos** — Progress photos (typically daily), drone footage, time-lapse
- **Correspondence** — Formal letters, email chains, notices (especially regarding delays, claims, or disputes)

### Financial Documents
- **Pay Applications** — AIA G702/G703 or equivalent, schedule of values
- **Invoices** — Subcontractor invoices, material invoices
- **Budget** — Original budget, cost-to-complete, forecast
- **Lien Waivers** — Conditional/unconditional, partial/final from subs and suppliers
- **Tax documents** — Sales tax exemption certificates, material tax refund invoices

### Closeout Documents
- **Warranties** — Manufacturer warranties, contractor warranties (typically 1-year general)
- **O&M Manuals** — Operation and maintenance manuals for building systems
- **As-Built Drawings** — Marked-up drawings reflecting actual field conditions
- **Punchlist** — Deficiency lists with completion tracking
- **Final lien waivers** — From all subs and suppliers
- **Certificate of Occupancy** — From local building department
- **Attic stock** — Spare materials inventory (flooring, ceiling tiles, paint)
- **Training records** — System training for building operators
- **Commissioning reports** — Functional performance testing of building systems
- **LEED/sustainability docs** — If pursuing green certification

---

## 2. CSI MasterFormat 2020 — Current Standard

Our architecture uses the 1995 16-Division format. The **current industry standard is MasterFormat 2020** with 50 divisions (unchanged since 2004 expansion). Key differences:

### Divisions Relevant to Mid-Size GC (Multifamily)

**Procurement & General:**
- Div 00 — Procurement and Contracting Requirements
- Div 01 — General Requirements

**Facility Construction (unchanged):**
- Div 02 — Existing Conditions (was "Site Construction" in 1995)
- Div 03 — Concrete
- Div 04 — Masonry
- Div 05 — Metals
- Div 06 — Wood, Plastics, and Composites (was "Wood and Plastics")
- Div 07 — Thermal and Moisture Protection
- Div 08 — Openings (was "Doors and Windows")
- Div 09 — Finishes
- Div 10 — Specialties
- Div 11 — Equipment
- Div 12 — Furnishings
- Div 13 — Special Construction
- Div 14 — Conveying Equipment (was "Conveying Systems")

**Facility Services (NEW — was all under Div 15/16):**
- **Div 21 — Fire Suppression** ← Critical for multifamily
- **Div 22 — Plumbing** ← Critical
- **Div 23 — HVAC** ← Critical
- Div 25 — Integrated Automation
- **Div 26 — Electrical** ← Critical
- **Div 27 — Communications** (low-voltage, data, telecom)
- **Div 28 — Electronic Safety and Security** (fire alarm, access control, CCTV)

**Site and Infrastructure:**
- **Div 31 — Earthwork** ← Common on multifamily
- **Div 32 — Exterior Improvements** (paving, landscaping, fencing)
- **Div 33 — Utilities** (storm, sanitary, water, gas)

**Process Equipment (Div 40-48):** Not relevant for building construction — skip.

### Impact on Our Architecture
Our current spec folder uses Div 00-17 (1995 format). We should update to include at minimum:
- Div 21 (Fire Suppression) — separate from Div 15 Mechanical
- Div 22 (Plumbing) — separate from Div 15 Mechanical
- Div 23 (HVAC) — separate from Div 15 Mechanical
- Div 26 (Electrical) — replaces Div 16
- Div 31 (Earthwork)
- Div 32 (Exterior Improvements)
- Div 33 (Utilities)

**However:** Many mid-size GCs still mentally use the old 16-division format. Our system should **store using 2020 format** but **display using whatever the client is familiar with**. This is a configuration item per client.

---

## 3. Best Practices — Synthesized

### Document Numbering & Naming
- **Sequential numbering is sacred** — SUB-001, RFI-001, CO-001. Never reuse numbers. Never skip. Gaps indicate deleted items (document the deletion).
- **Include revision history in filename** — `r1`, `r2` not `v1`, `v2` (construction convention is "revision" not "version")
- **Date format: YYYY-MM-DD** — universal, sortable, unambiguous (not MM/DD/YYYY which invites confusion)
- **Spec section reference in submittals** — Always tag the CSI spec section: `SUB-007-084413-storefront-glazing`. This is how architects think about submittals.

### Version Control
- **Never overwrite** — Every revision creates a new file. Old version moves to `_Archive/` or gets a superseded flag.
- **Revision log** — Every document should have a metadata record of who changed what and when.
- **Single source of truth** — One canonical location per document. Cross-references (symlinks or DB pointers), never copies.
- **Drawing revision tracking** — Drawings use revision clouds + revision blocks. Track delta between revisions for AI analysis.

### Workflow Status Tracking
- **Standard submittal workflow:** Draft → Submitted → Under Review → Approved / Approved as Noted / Revise & Resubmit / Rejected
- **Standard RFI workflow:** Draft → Open → Answered → Closed (with optional "Void" status)
- **Change Order workflow:** PCO (Potential) → COR (Request) → CO (Approved) / Rejected
- **Ball-in-court tracking** — At any point, know whose action is required. Critical for accountability.

### Retention Requirements
- **Florida statute of repose for construction defects: 10 years** from completion (4-year statute of limitations within that window)
- **Federal contractors:** 3-6 years depending on document type
- **Best practice recommendation (NSPE):** Retain for statute of repose + 3 years = **13 years minimum in Florida**
- **NERV implication:** Storage strategy must plan for 10-15 years of document retention per project. Archived projects should be cold-storable but retrievable.

### Document Control Officer Role
- Large projects typically have a dedicated document control person
- **NERV's EVA replaces this role** — automated classification, filing, distribution, version control
- Key responsibilities EVA handles: receiving/logging incoming docs, distributing to correct parties, maintaining logs, tracking status, ensuring current versions are accessible

### Common PM Pain Points (What EVA Solves)
1. **"Where's the latest drawing?"** → `Current Set` folder + drawing log with revision tracking
2. **"Has the submittal been reviewed?"** → Status subfolders + automated notifications
3. **"When did we send that RFI?"** → Timestamped DB records + email trail
4. **"Who's responsible for this?"** → Ball-in-court tracking in every workflow
5. **"Are we missing any closeout items?"** → Automated closeout checklist generation from spec sections
6. **"What did we agree to in that meeting?"** → Meeting minutes indexed and searchable
7. **"How much have we spent vs budget?"** → Financial tracking with pay app + CO integration
8. **"Is this sub's insurance current?"** → Certificate expiration tracking with auto-alerts

### Pro Tips & Tricks
- **Transmittal for everything** — Even if sending via email, attach a transmittal form. Creates a paper trail that holds up in court.
- **RFI as a defense mechanism** — If design is ambiguous, always RFI it. Documents that you asked, protects against claims.
- **Contemporaneous documentation** — Daily logs written same-day are 10x more valuable legally than reconstructed ones. Time-stamping is critical.
- **Photo everything** — Before covering work (underground, framing, MEP rough-in), photo it. Procore has a photo log tool, but NERV should also archive these with metadata.
- **Close the loop** — Every submittal, RFI, and CO should have a clear closed/resolved status. Open items at closeout = problems.
- **Spec section cross-reference** — Tag every submittal to its spec section. At closeout, run a report: "all spec sections requiring submittals — are they all approved?" This catches missing items weeks before the architect asks.

---

## 4. Recommendations for NERV Architecture Updates

Based on this research, the following updates to `NERV-DATA-ARCHITECTURE.md` are recommended:

### Schema Updates
1. **Add `document_embeddings` table** — pgvector for semantic search
2. **Add `transmittals` table** — Formal document transfer tracking
3. **Add `vendor_performance` table** — Track sub reliability across projects
4. **Add `lessons_learned` table** — Tagged insights searchable by trade/category
5. **Add `bid_history` table** — Historical pricing for estimation intelligence
6. **Add `insurance_certificates` table** — Expiration tracking with auto-alerts
7. **Add `punchlist_items` table** — Individual item tracking with completion status
8. **Add `closeout_checklist` table** — Auto-generated from spec sections
9. **Add `document_versions` table** or `parent_document_id` to documents — Version chain tracking
10. **Add `ball_in_court` field** to submittals, RFIs, COs — Whose action is pending

### Folder Structure Updates
1. **Update CSI divisions to MasterFormat 2020** — At minimum add Div 21-23, 26-28, 31-33
2. **Add `Transmittals/` folder** under Correspondence or as its own top-level
3. **Add `Closeout/Commissioning/` subfolder**
4. **Add `Closeout/Attic Stock/` subfolder**
5. **Add `Closeout/Training Records/` subfolder**
6. **Rename submittal status "Under Review" to "Submitted"** — Match Procore's workflow labels for familiarity

### Naming Convention Updates
1. **Add `ASI` category code** — Architect's Supplemental Instructions
2. **Add `BUL` category code** — Bulletins
3. **Add `TRN` category code** — Transmittals
4. **Add `PLI` category code** — Punchlist Items
5. **Include spec section in submittal filenames** — `{Project}-SUB-{Seq}-{SpecSection}-{Desc}-{Date}-{Rev}.pdf`

### Configuration Items
1. **CSI format preference per client** — 1995 (16-div) vs 2020 (50-div) display
2. **Submittal workflow stages per client** — Some use 4 statuses, some use 6
3. **Document retention policy per client** — Default 13 years for Florida

---

## Sources
- Procore Library: Document Control Best Practices, Submittals Guide, RFI Guide
- CSI MasterFormat 2020 (via Wikipedia division listing)
- Autodesk Construction Blog: Document Management Best Practices
- ProjectManager: Construction Document Management Guide
- NSPE: Document Retention Guidelines White Paper
- Florida Statutes: Statute of Repose (10 years), Statute of Limitations (4 years)
- GSourceData: Construction Documents Types, Tools & Best Practices
- Pericent: Document Management Best Practices for Construction Industry
