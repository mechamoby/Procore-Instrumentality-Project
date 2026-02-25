# Procore Webhook Resources — CONFIRMED from Sandbox API
> Queried: 2026-02-24 from sandbox.procore.com
> Company ID: 4281379 | Project ID: 316469

## How to Read This
- `except: []` = supports ALL event types (create, update, delete)
- `except: ['delete']` = supports create + update only (no delete webhook)
- `except: ['create', 'delete']` = supports update only

---

## COMPANY-LEVEL Resources (25 total)

| Resource | Events Supported | NERV Priority |
|----------|-----------------|---------------|
| Bids | update only | Low |
| Change Order Change Reasons | create, update, delete | Low |
| Change Types | create, update, delete | Low |
| Company File Versions | create, update, delete | Medium |
| Company Files | create, update, delete | Medium |
| Company Folders | create, update, delete | Low |
| Company Insurances | create, update, delete | Medium |
| Company Users | create, update | Medium |
| Company Vendors | create, update | Medium |
| Departments | create, update, delete | Low |
| ERP Requests | create, update, delete | Low |
| Form Templates | create, update, delete | Low |
| Line Item Types | create, update, delete | Low |
| Offices | create, update, delete | Low |
| Programs | create, update, delete | Low |
| Project Bid Types | create, update, delete | Low |
| Project Owner Types | create, update, delete | Low |
| Project Regions | create, update, delete | Low |
| Project Stages | create, update, delete | Low |
| Project Types | create, update, delete | Low |
| **Projects** | **create, update** | **HIGH** |
| Standard Cost Code Lists | create only | Low |
| Standard Cost Codes | create, update, delete | Low |
| Timecard Time Types | create, delete | Low |
| Trades | create, delete | Low |

## PROJECT-LEVEL Resources (88 total)

### 🔴 CRITICAL — Core Agent Pipeline

| Resource | Events Supported | Agent | Notes |
|----------|-----------------|-------|-------|
| **Submittals** | create, update, delete | EVA-01 | ✅ CONFIRMED |
| **Submittal Packages** | create, update, delete | EVA-01 | ✅ CONFIRMED |
| **RFIs** | create, update, delete | EVA-02 | ✅ CONFIRMED |
| **RFI Replies** | create, update, delete | EVA-02 | ✅ CONFIRMED |
| **Daily Logs** | create, update, delete | EVA-00 | ✅ CONFIRMED |
| **Daily Log/Entries** | create, update, delete | EVA-00 | ✅ CONFIRMED |
| **Daily Construction Report Logs** | create, update, delete | EVA-00 | ✅ CONFIRMED |

### 🟠 HIGH — Active Monitoring

| Resource | Events Supported | Use Case |
|----------|-----------------|----------|
| **Change Events** | create, update, delete | CO tracking |
| **Change Event Line Items** | create, update, delete | CO cost detail |
| **Change Order Packages** | create, update, delete | CO package tracking |
| **Change Order Requests** | create, update, delete | COR pipeline |
| **Potential Change Orders** | create, update, delete | PCO pipeline |
| **Potential Change Order Line Items** | create, update, delete | PCO detail |
| **Payment Applications** | create, update, delete | Pay app tracking |
| **Punch Items** | create, update, delete | Closeout tracking |
| **Meetings** | create, update, delete | Meeting minutes |
| **Meeting Topics** | create, update, delete | Agenda tracking |
| **Meeting Attendees** | create, update, delete | Attendance tracking |
| **Incidents** | create, update, delete | Safety tracking |
| **Inspection Checklists** | create, update | Quality/compliance |
| **Inspection Logs** | create, update, delete | Field inspections |

### 🟡 MEDIUM — Data Enrichment

| Resource | Events Supported | Use Case |
|----------|-----------------|----------|
| Drawings | create, update, delete | Revision tracking (metadata) |
| Drawing Sets | create, update, delete | Set management |
| Drawing Uploads | create, update, delete | New drawing detection |
| Drawing Areas | create, update, delete | Area classification |
| Project Files | create, update, delete | Document sync |
| Project File Versions | create, update, delete | Version tracking |
| Project Folders | create, update, delete | Folder structure sync |
| Specification Sections | create, update | Spec cross-reference |
| Specification Section Revisions | create, update, delete | Spec revision tracking |
| Specification Sets | create, update, delete | Spec set tracking |
| Specification Areas | create, update, delete | Spec organization |
| Specification Section Divisions | create, update, delete | CSI division mapping |
| Images | create, update, delete | Photo sync |
| Image Categories | create, update, delete | Photo organization |
| BIM Models | create, update, delete | BIM tracking |
| BIM Model Revisions | create, update, delete | BIM version tracking |
| BIM File Extractions | create, update, delete | BIM data extraction |
| Coordination Issues | create, update, delete | BIM coordination |
| Coordination Issue Activities | create, update, delete | Coordination tracking |

### 🟢 LOW — Nice to Have

| Resource | Events Supported | Use Case |
|----------|-----------------|----------|
| Accident Logs | create, update, delete | Safety records |
| Safety Violation Logs | create, update, delete | Safety compliance |
| Budget Line Items | create, update, delete | Budget tracking |
| Budget Changes | create, update, delete | Budget modifications |
| Budget Change Adjustments | create, update, delete | Budget adjustments |
| Budget Change Adjustment Line Items | create, update, delete | Budget detail |
| Budget Change Production Quantities | create, update, delete | Production tracking |
| Budget Modifications | create, update, delete | Budget mods |
| Budget View Snapshots | create only | Budget snapshots |
| Call Logs | create, update, delete | Communication log |
| Cost Codes | create, update, delete | Cost code management |
| Contract Payments | create, update, delete | Payment tracking |
| Delivery Logs | create, update, delete | Material delivery |
| Direct Costs | create, update, delete | Direct cost tracking |
| Direct Cost Line Items | create, update, delete | Direct cost detail |
| Company Direct Cost Line Items | create, update, delete | Company cost detail |
| Draw Requests | create, update, delete | Draw requests |
| Dumpster Logs | create, update, delete | Waste management |
| Equipment Logs | create, update, delete | Equipment tracking |
| File Versions | create, update, delete | File versioning |
| Forms | create, update, delete | Custom forms |
| Generic Tool Items | create, update, delete | Custom tools |
| Locations | create, update, delete | Location management |
| Manpower Logs | create, update, delete | Labor tracking |
| Markup Layers | create, update | Drawing markups |
| Meeting Categories | create, update, delete | Meeting org |
| Notes Logs | create, update, delete | Field notes |
| Observation Items | create, update, delete | Safety observations |
| Observation Item Response Logs | create only | Observation responses |
| Pdf Download Pages | create, update, delete | PDF tracking |
| Plan Revision Logs | create, update, delete | Plan revisions |
| Prime Contracts | create, update, delete | Prime contract tracking |
| Prime Contract Line Items | create, update, delete | Prime contract detail |
| Productivity Logs | create, update, delete | Productivity tracking |
| Project Dates | create, update, delete | Milestone tracking |
| Project Insurances | create, update, delete | Insurance tracking |
| Project Users | create, update, delete | User management |
| Project Vendors | create, update, delete | Vendor management |
| Purchase Order Contracts | create, update, delete | PO tracking |
| Purchase Order Contract Line Items | create, update, delete | PO detail |
| Quantity Logs | create, update, delete | Quantity tracking |
| RFQ Quotes | create, update | Quote tracking |
| RFQ Responses | create, update | Response tracking |
| RFQs | create, update, delete | RFQ management |
| Site Instructions | create, update, delete | Field instructions |
| Sub Jobs | create, update, delete | Sub job tracking |
| Task Items | create, update | Task detail |
| Tasks | create, update, delete | Task management |
| Timecard Entries | create, update, delete | Time tracking |
| ToDos | create, update, delete | Action items |
| Visitor Logs | create, update, delete | Site visitor tracking |
| Waste Logs | create, update, delete | Waste tracking |
| Weather Logs | create, update | Weather records |
| Work Logs | create, update, delete | Work records |
| Work Order Contracts | create, update, delete | Work order tracking |
| Work Order Contract Line Items | create, update, delete | Work order detail |

---

## Summary

**Total webhook-enabled resources: 113** (25 company + 88 project)

### Coverage vs NERV Needs

| NERV Feature | Webhook Resource | Status |
|-------------|-----------------|--------|
| Submittal pipeline (EVA-01) | Submittals, Submittal Packages | ✅ FULL |
| RFI pipeline (EVA-02) | RFIs, RFI Replies | ✅ FULL |
| Daily log processing | Daily Logs, Daily Log/Entries, Daily Construction Report Logs | ✅ FULL |
| Change order tracking | Change Events, Change Order Packages, CORs, PCOs | ✅ FULL |
| Pay app tracking | Payment Applications | ✅ FULL |
| Meeting minutes | Meetings, Meeting Topics, Meeting Attendees | ✅ FULL |
| Safety/incidents | Incidents, Accident Logs, Safety Violation Logs, Observations | ✅ FULL |
| Inspections | Inspection Checklists, Inspection Logs | ✅ FULL |
| Drawing revisions | Drawings, Drawing Sets, Drawing Uploads | ✅ FULL |
| BIM models | BIM Models, BIM Model Revisions, BIM File Extractions | ✅ FULL |
| Document sync | Project Files, Project File Versions, Project Folders | ✅ FULL |
| Spec tracking | Specification Sections, Sets, Revisions, Divisions | ✅ FULL |
| Closeout/punchlist | Punch Items | ✅ FULL |
| Budget monitoring | Budget Line Items, Changes, Modifications | ✅ FULL |

### 🎯 Bottom Line
**Every single feature in our data architecture has webhook coverage.** Zero gaps. The super uploads a daily log from the field → NERV knows in seconds.
