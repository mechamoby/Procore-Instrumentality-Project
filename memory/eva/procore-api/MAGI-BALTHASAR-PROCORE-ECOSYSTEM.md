# MAGI BALTHASAR — Procore Desktop Apps + Data Tools Deep Dive
## Business/Integration Opportunity Analysis

*Research Date: 2026-02-24*  
*Objective: Assess non-AI Procore apps for EVA/SEELE integration opportunities*

---

## 🔧 DESKTOP APPS

### 1. PROCORE IMPORTS — Bulk Data Import Tool

**📋 Features & Data Types:**
- **Free Windows desktop application** (Windows 10+ required)
- Supports bulk import of:
  - Contacts
  - Cost codes & cost types
  - Punch items
  - Submittals
  - Locations (multi-tiered)
  - Segment items (Work Breakdown Structure)
- **File Formats**: XLSX and CSV (UTF-8) templates
- Template-based approach with pre-defined column structures
- Requires 'Admin' level permissions

**💰 Pricing:** FREE

**👥 User Sentiment:** 
- Well-regarded for time-saving bulk operations
- Some users note Windows-only limitation
- Praised for preventing one-by-one manual entry

**🔗 EVA Integration Opportunities:**
- **HIGH POTENTIAL**: Could serve as alternative to REST API for pushing EVA-processed data back into Procore
- Templates are standardized — EVA could generate compliant CSV/XLSX files
- Particularly valuable for seeding new projects with AI-processed historical data
- Could automate cost code standardization across projects
- **Limitation**: Requires Windows environment and manual file transfer

**🔧 Technical Details:**
- Desktop-only, no API access
- Converts all data to CSV (UTF-8) format internally
- Template validation before import
- Admin permissions required for execution

---

### 2. PROCORE EXTRACTS — Data Extraction Tool

**📋 Features:**
- **Free Windows desktop application**
- Bulk download of project data from multiple Procore tools
- Customizable extraction by tool type
- Direct export to local computer
- **Note**: Being superseded by "Data Extracts 2.0" (web-based)

**💰 Pricing:** FREE

**👥 User Sentiment:**
- Users appreciate bulk data access
- Some frustration with Windows-only limitation
- Migration to web-based version seen as improvement

**🔗 EVA Integration Opportunities:**
- **MODERATE POTENTIAL**: Could be onboarding tool similar to Drive
- Less appealing than Drive due to desktop requirement
- **Better for**: Bulk historical data extraction for AI training
- **Worse than Drive for**: Real-time NERV seeding (requires manual process)
- Could supplement API-based data collection with bulk exports

**🔧 Technical Details:**
- Windows desktop application
- No API hooks available
- Manual extraction process
- Being replaced by web-based Data Extracts 2.0

---

### 3. PROCORE BIM PLUGIN — CAD Integration

**📋 Features:**
- **Free Windows plugin** for Autodesk software
- **Supported Applications:**
  - Navisworks Manage/Simulate (2019-2025)
  - Revit (2019-2025)
  - AutoCAD (2019-2025)
- **Core Functions:**
  - File management (open/save/upload to Procore Documents)
  - Coordination issue management directly in CAD software
  - Clash detection integration
  - Direct export from CAD to Procore Documents tool

**💰 Pricing:** FREE

**👥 User Sentiment:**
- Well-received by BIM teams
- Streamlines CAD-to-Procore workflows
- Reduces risk of rework through better coordination

**🔗 EVA Integration Opportunities:**
- **MODERATE POTENTIAL**: Limited direct API access
- Could monitor Documents tool for BIM file uploads via API
- EVA could analyze coordination issues created through plugin
- **Indirect Integration**: Process files after they're uploaded to Documents
- No direct plugin API hooks identified

**🔧 Technical Details:**
- Windows-only installation
- Two separate plugin types (being consolidated)
- Integrates with Procore's Documents and Coordination Issues tools
- No documented API access to plugin functions

---

### 4. PROCORE VDC PLUGIN — Legacy BIM Tool

**📋 Features:**
- **Legacy plugin** - still active but being deprecated
- Model publishing capabilities
- Settings management for BIM workflows
- **Status**: Functionality being migrated to unified BIM Plugin

**💰 Pricing:** FREE

**👥 User Sentiment:**
- Users understanding migration to new BIM Plugin
- Some workflow disruption during transition

**🔗 EVA Integration Opportunities:**
- **LOW POTENTIAL**: Being deprecated
- Focus should be on new unified BIM Plugin instead
- No new development recommended on this tool

**🔧 Technical Details:**
- Legacy Windows plugin
- Model publish and settings features moving to new BIM Plugin
- No API access
- **Transition Timeline**: Active until BIM Plugin consolidation complete

---

## 📊 DATA & INTEGRATION TOOLS

### 5. PROCORE DATA EXTRACT — Azure SQL Pipeline

**📋 Features:**
- **Managed Azure SQL Database integration**
- Ready-to-use SQL database with Procore data
- Enables custom reporting with any SQL-compliant tool
- **Data Pipeline**: Hosted and managed by Procore
- Full company data access across all projects

**💰 Pricing:** **PREMIUM FEATURE** (contact Procore for pricing)

**👥 User Sentiment:**
- Highly valued by analytics teams
- Preferred over REST API for bulk analytics
- Enables sophisticated BI/reporting solutions

**🔗 EVA Integration Opportunities:**
- **VERY HIGH POTENTIAL**: Could replace REST API for bulk data access
- SQL access provides better performance for large datasets
- Ideal for NERV training data preparation
- **Advantages over REST API:**
  - Bulk data access without rate limits
  - SQL queries for complex data relationships
  - Better for historical data analysis
- **Use Cases:**
  - Feed NERV with comprehensive project histories
  - Real-time analytics pipeline
  - Custom reporting for EVA insights

**🔧 Technical Details:**
- Microsoft Azure SQL Database
- SQL-compliant access
- Managed service (Procore handles infrastructure)
- Enterprise-grade security and performance
- **Alternative**: New Analytics 2.0 uses Delta Share format

---

### 6. APP MARKETPLACE — Integration Ecosystem

**📋 Features:**
- **500+ integrations** across 25+ categories
- Categories include:
  - ERP & Accounting
  - Business Intelligence
  - CRM
  - Drone Technology
  - Document Management
  - Project Management
  - Safety & Quality
  - Field Management

**💰 Revenue Model:** 
- Partner revenue sharing (terms not publicly disclosed)
- Freemium and subscription models supported

**👥 User Sentiment:**
- Strong ecosystem adoption
- Easy discovery and installation
- Embedded Experience features well-received

**🔗 EVA Integration Opportunities:**
- **VERY HIGH POTENTIAL**: Prime distribution channel for SEELE/EVA
- **Path to Market:**
  - Apply for Technology Partner Program
  - Develop marketplace-ready integration
  - Leverage Procore's customer base
- **Requirements** (need to verify):
  - Partner program application
  - Technical certification
  - Revenue sharing agreement
  - Support and maintenance commitments

**🔧 Technical Details:**
- **Integration Types:**
  - API-based data exchange
  - Embedded Experience (UI integration)
  - Service Account authentication
- OAuth 2.0 Client Credentials support
- Client certification process required
- Marketplace listing guidelines and review process

---

## 💳 PAYMENTS

### 7. PROCORE PAY — Lien Waiver Automation

**📋 Features:**
- **Lien waiver automation** (powered by Levelset acquisition)
- Subcontractor payment processing
- **Core Functions:**
  - Automated lien waiver generation
  - Digital signature collection
  - Payment application streamlining
  - Sworn statement processing
  - Sub-tier payment tracking

**💰 Pricing:** **PREMIUM FEATURE** (subscription-based, pricing not disclosed)

**👥 User Sentiment:**
- Highly valued for reducing administrative burden
- Strong adoption among GCs for payment streamlining
- Positive feedback on Levelset integration quality

**🔗 EVA Integration Opportunities:**
- **MODERATE TO HIGH POTENTIAL**: Specialized but valuable niche
- **AI Enhancement Opportunities:**
  - Intelligent lien waiver document processing
  - Automated compliance checking
  - Predictive payment risk analysis
  - Anomaly detection in payment applications
- **API Access**: Limited documentation found - would need investigation
- **Value Add**: EVA could enhance document intelligence and risk assessment

**🔧 Technical Details:**
- Integrated with Procore's Invoice Management
- Leverages Levelset (Procore subsidiary) infrastructure
- **Document Formats**: PDF generation and processing
- **Compliance**: State-specific lien waiver requirements
- **Integration Points**: 
  - Subcontractor Invoicing tool
  - Company Payments tool
  - Project-level payment workflows

---

## 🚀 STRATEGIC RECOMMENDATIONS

### HIGH-PRIORITY OPPORTUNITIES

1. **Procore Data Extract (Azure SQL)**
   - **Impact**: High
   - **Effort**: Medium
   - **ROI**: Very High
   - Replace REST API limitations with SQL-based bulk access

2. **App Marketplace Partnership**
   - **Impact**: Very High  
   - **Effort**: High
   - **ROI**: Very High
   - Direct path to 13M+ Procore users

3. **Procore Imports Integration**
   - **Impact**: Medium
   - **Effort**: Low
   - **ROI**: High
   - EVA-generated CSV/XLSX templates for data push-back

### MEDIUM-PRIORITY OPPORTUNITIES

4. **Procore Pay Enhancement**
   - **Impact**: Medium
   - **Effort**: Medium
   - **ROI**: Medium
   - Specialized but high-value niche

5. **BIM Plugin Monitoring**
   - **Impact**: Low
   - **Effort**: Low
   - **ROI**: Medium
   - Indirect integration via Documents API

### NEXT STEPS

1. **Immediate**: Research Data Extract pricing and access requirements
2. **Short-term**: Apply for Procore Technology Partner Program
3. **Medium-term**: Develop marketplace-ready MVP integration
4. **Long-term**: Full ecosystem integration across multiple tools

---

*Analysis complete. Tools researched represent significant integration opportunities, with Data Extract and Marketplace partnership showing highest potential ROI.*