# Procore REST API Deep Dive Research

**Research Date:** February 17, 2026
**Researcher:** Paper Moby (Subagent)
**Task:** Comprehensive analysis of ALL Procore REST API endpoints for construction project management

---

## Executive Summary

Procore provides a comprehensive REST API architecture with independent resource versioning (v1.x, v2.x, etc.) and extensive coverage of construction project management needs. The API supports both company-level and project-level resources, with robust file upload/download capabilities, webhook notifications, and comprehensive CRUD operations across all major construction tools.

**Key API Architecture:**
- Base URL: `https://api.procore.com/rest/v{api_version}.{resource_version}`
- Authentication: OAuth 2.0 Bearer Token
- Version Format: `v{api_version}.{resource_version}` (e.g., v1.4)
- Content Types: JSON for most operations, multipart/form-data for file uploads

---

## 1. SUBMITTALS API

### Endpoints
- **List Submittals**: `GET /rest/v1.1/projects/{project_id}/submittals`
- **Show Submittal**: `GET /rest/v1.1/projects/{project_id}/submittals/{id}`
- **Create Submittal**: `POST /rest/v1.1/projects/{project_id}/submittals`
- **Update Submittal**: `PATCH /rest/v1.1/projects/{project_id}/submittals/{id}`
- **Delete Submittal**: `DELETE /rest/v1.1/projects/{project_id}/submittals/{id}`

### Data Returned
- Submittal ID, number, title, status
- Due dates, approval workflow steps
- Submittal package information
- Vendor/contractor details
- Location associations
- Related items (specifications, drawings)
- **Attachments metadata** including filenames, URLs, content types

### File/Attachment Download Capabilities
✅ **YES - Full File Download Support**
- Attachments can be downloaded via direct URLs returned in submittal responses
- Supports bulk attachment downloads for entire submittal packages
- File metadata includes: filename, content_type, size, upload date
- Direct links to file storage (S3) with authenticated access
- **Content-Type**: multipart/form-data for uploads
- **Attachment Key Format**: `attachments[]` for multiple files

### Limitations
- Requires appropriate permissions (Submittals tool access)
- File downloads are authenticated (require valid OAuth token)
- Large file downloads may have timeout considerations
- Webhook support available for real-time notifications

---

## 2. WEBHOOKS API

### Webhook Architecture
✅ **COMPREHENSIVE WEBHOOK SUPPORT**

### Core Endpoints
- **Create Hook**: `POST /rest/v1.0/webhooks/hooks`
- **List Hooks**: `GET /rest/v1.0/webhooks/hooks`
- **Show Hook**: `GET /rest/v1.0/webhooks/hooks/{hook_id}`
- **Update Hook**: `PATCH /rest/v1.0/webhooks/hooks/{hook_id}`
- **Delete Hook**: `DELETE /rest/v1.0/webhooks/hooks/{hook_id}`

### Trigger Management
- **Add Trigger**: `POST /rest/v1.0/webhooks/hooks/{hook_id}/triggers`
- **List Triggers**: `GET /rest/v1.0/webhooks/hooks/{hook_id}/triggers`
- **Delete Trigger**: `DELETE /rest/v1.0/webhooks/hooks/{hook_id}/triggers/{trigger_id}`

### Delivery Monitoring
- **List Deliveries**: `GET /rest/v1.0/webhooks/hooks/{hook_id}/deliveries`
- **Show Delivery**: `GET /rest/v1.0/webhooks/hooks/{hook_id}/deliveries/{delivery_id}`

### Real-Time Notifications Support
✅ **YES - Full Real-Time Support for:**
- **Drawings/Submittals Upload Events**: create, update, delete events
- **Drawing Revisions**: New revision notifications
- **Submittal Status Changes**: Approval workflow updates
- **Document Uploads**: File attachment notifications
- **All Supported Resources**: RFIs, Change Orders, Observations, Daily Logs, Photos, etc.

### Event Types Supported
- **create**: New resource creation
- **update**: Resource modifications
- **delete**: Resource deletion
- **Custom events**: Some resources support additional event types

### Webhook Payload Formats
**v2.0 (Legacy)**:
```json
{
  "id": 123456789,
  "ulid": "0A1B2C3D4F5G6H7I8J9K0LMN",
  "timestamp": "2025-02-06T23:34:12.246562Z",
  "event_type": "create",
  "resource_name": "Submittals",
  "resource_id": 54321,
  "company_id": 1357908642,
  "project_id": 2468013579,
  "user_id": 987654321
}
```

**v4.0 (Current)**:
```json
{
  "id": "01JMYXMZRBVKK0PC6XS8SA4QRE",
  "timestamp": "2025-02-25T16:04:43.619085Z",
  "reason": "create",
  "resource_type": "Submittals",
  "resource_id": "54321",
  "company_id": "8",
  "project_id": "6778",
  "user_id": "5447"
}
```

### Limitations
- Requires HTTPS endpoint
- 5-second timeout for webhook responses
- Must return 2xx status codes
- Retry mechanism with exponential backoff
- 12-hour maximum retry window

---

## 3. SPECIFICATIONS API

### Status
❌ **COMING SOON** - Not yet available via REST API

### Current Information
- Specifications tool exists in Procore UI
- Manages project specifications and revisions
- Ensures team access to current spec versions
- **API Status**: Documentation shows "Coming Soon!"
- **Workaround**: May be accessible through Documents API as uploaded files

### Expected Future Capabilities
- List project specifications
- Manage spec revisions
- Download specification documents
- Version control and approval workflows

---

## 4. OBSERVATIONS / INSPECTIONS API

### Observations Tool
✅ **FULL API SUPPORT**

#### Endpoints
- **List Observations**: `GET /rest/v1.0/projects/{project_id}/observations`
- **Show Observation**: `GET /rest/v1.0/projects/{project_id}/observations/{id}`
- **Create Observation**: `POST /rest/v1.0/projects/{project_id}/observations`
- **Update Observation**: `PATCH /rest/v1.0/projects/{project_id}/observations/{id}`
- **Delete Observation**: `DELETE /rest/v1.0/projects/{project_id}/observations/{id}`

#### Data Returned
- Observation ID, title, description, status
- Assignment details (assignee, company)
- Due dates and priority levels
- Location information
- Photos and file attachments
- Quality/safety categories
- Response tracking

### Inspections Tool (Checklists)
✅ **FULL API SUPPORT**

#### Endpoints
- **List Checklists**: `GET /rest/v1.0/projects/{project_id}/checklists`
- **Show Checklist**: `GET /rest/v1.0/projects/{project_id}/checklists/{id}`
- **Create Checklist**: `POST /rest/v1.0/projects/{project_id}/checklists`
- **Update Checklist**: `PATCH /rest/v1.0/projects/{project_id}/checklists/{id}`

#### Data Returned
- Comprehensive inspection checklists
- Template-based inspections
- Question/answer structures
- Pass/fail criteria
- Signature capture
- Photo documentation

### File/Attachment Support
✅ **YES** - Both tools support file attachments and photo documentation

---

## 5. DAILY LOGS API

### Comprehensive Daily Log System
✅ **FULL API SUPPORT** - Multiple specialized log types

### Core Daily Log Types & Endpoints

#### Accident Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/accident_logs`
- **Data**: Incident details, parties involved, photos, time/date

#### Call Logs  
- **Endpoint**: `/rest/v1.0/projects/{project_id}/call_logs`
- **Data**: Call participants, topics, duration, follow-up items

#### Daily Construction Report Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/daily_construction_report_logs`
- **Data**: Worker counts, hours worked by vendor/trade, productivity metrics

#### Delivery Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/delivery_logs`
- **Data**: Shipment tracking, delivery contents, tracking numbers

#### Equipment Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/equipment_logs`
- **Data**: Equipment usage, inspection status, cost codes, operating hours

#### Inspection Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/inspection_logs`
- **Data**: Third-party inspections, results, inspector details

#### Manpower Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/manpower_logs`
- **Data**: Worker counts by company, hours worked, cost codes

#### Notes Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/notes_logs`
- **Data**: Miscellaneous daily observations, issue tracking

#### Productivity Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/productivity_logs`
- **Data**: Material installation vs. delivery, progress tracking

#### Safety Violation Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/safety_violation_logs`
- **Data**: Safety incidents, violations, corrective actions, photos

#### Weather Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/weather_logs`
- **Data**: Weather conditions, delays, impact on work

#### Work Logs
- **Endpoint**: `/rest/v1.0/projects/{project_id}/work_logs`
- **Data**: Scheduled vs. actual work, resource allocation

### File/Attachment Support
✅ **YES** - All log types support photo and file attachments

---

## 6. PHOTOS API

### Core Endpoints
✅ **FULL API SUPPORT**

#### Image Management
- **List Images**: `GET /rest/v1.0/projects/{project_id}/images`
- **Show Image**: `GET /rest/v1.0/projects/{project_id}/images/{id}`
- **Create Image**: `POST /rest/v1.0/projects/{project_id}/images`
- **Update Image**: `PATCH /rest/v1.0/projects/{project_id}/images/{id}`
- **Delete Image**: `DELETE /rest/v1.0/projects/{project_id}/images/{id}`

#### Image Categories
- **List Categories**: `GET /rest/v1.0/projects/{project_id}/image_categories`
- **Create Category**: `POST /rest/v1.0/projects/{project_id}/image_categories`

### Data Returned
- Image metadata (filename, size, dimensions, upload date)
- Direct download URLs
- Thumbnail URLs
- Image categories and tags
- Location associations
- GPS coordinates (if available)
- Camera/device information

### File Download Capabilities
✅ **YES - Direct Image Downloads**
- **Content-Type**: multipart/form-data for uploads
- **Upload Key Format**: `image[data]` for single image uploads
- High-resolution image access
- Thumbnail generation
- Batch download capabilities
- Multiple format support (JPEG, PNG, etc.)

### Limitations
- File size limits apply
- Authentication required for access
- Storage quotas may apply

---

## 7. SCHEDULE API

### Core Scheduling Resources
✅ **FULL API SUPPORT**

#### Calendar Events
- **Endpoints**: `/rest/v1.0/projects/{project_id}/calendar_events`
- **Data**: Event scheduling, milestones, deadlines

#### Tasks
- **Endpoints**: `/rest/v1.0/projects/{project_id}/tasks`
- **Data**: Work breakdown structure, task dependencies, progress tracking

#### ToDos
- **Endpoints**: `/rest/v1.0/projects/{project_id}/todos`
- **Data**: Action items, assignments, due dates

#### Schedule Integration
- **Endpoints**: `/rest/v1.0/projects/{project_id}/schedule_integration`
- **Data**: Third-party schedule integration (Primavera, MS Project)

#### Requested Changes
- **Endpoints**: `/rest/v1.0/projects/{project_id}/requested_changes`
- **Data**: Schedule modification requests, impact analysis

### Data Returned
- Task IDs, names, descriptions
- Start/end dates, durations
- Dependencies and predecessors
- Resource assignments
- Progress percentages
- Critical path information
- Baseline comparisons

### File/Attachment Support
✅ **LIMITED** - Supporting documents can be attached to tasks and events

### Limitations
- Complex scheduling logic may require specialized tools
- Real-time updates depend on integration setup
- Limited Gantt chart data via API

---

## 8. BUDGET/COST API

### Comprehensive Financial Management
✅ **EXTENSIVE API SUPPORT**

#### Budget Management
- **Budget Line Items**: `/rest/v1.0/projects/{project_id}/budget_line_items`
- **Budget Modifications**: `/rest/v1.0/projects/{project_id}/budget_modifications`
- **Budget Changes**: `/rest/v1.0/projects/{project_id}/budget_changes`
- **Budget Views**: `/rest/v1.0/projects/{project_id}/budget_views`
- **Budget Details**: `/rest/v1.0/projects/{project_id}/budget_details`

#### Cost Tracking
- **Direct Costs**: `/rest/v1.0/projects/{project_id}/direct_costs`
- **Contract Payments**: `/rest/v1.0/projects/{project_id}/contract_payments`
- **Draw Requests**: `/rest/v1.0/projects/{project_id}/draw_requests`

### Data Returned
- Budget line items with cost codes
- Original, revised, and forecasted amounts
- Committed costs and change orders
- Variance analysis
- Cash flow projections
- Cost-to-complete estimates
- Approval workflows and status

### File/Attachment Support
✅ **YES** - Financial documents, receipts, invoices can be attached

### Limitations
- Requires proper financial permissions
- Complex budget structures may need specialized handling
- Real-time cost updates depend on integration frequency

---

## 9. DIRECTORY API (Company/Project Directory)

### Project-Level Directory
✅ **FULL API SUPPORT**

#### Project Users (Contacts)
- **Endpoints**: `/rest/v1.0/projects/{project_id}/project_users`
- **Data**: User profiles, contact information, roles, permissions

#### Project Vendors
- **Endpoints**: `/rest/v1.0/projects/{project_id}/project_vendors`
- **Data**: Vendor/contractor information, trades, contact details

#### Project Vendor Insurances
- **Endpoints**: `/rest/v1.0/projects/{project_id}/project_vendor_insurances`
- **Data**: Insurance policies, expiration dates, compliance status

### Data Returned
- Complete contact databases
- User roles and permissions
- Company information
- Insurance and certification status
- Trade classifications
- Contact preferences

### File/Attachment Support
✅ **YES** - Insurance documents, certifications, licenses can be attached

### Limitations
- Privacy controls may limit data access
- Permission-based data filtering applies

---

## 10. CHANGE EVENTS / CHANGE ORDERS API

### Change Management System
✅ **COMPREHENSIVE API SUPPORT**

#### Change Events
- **Endpoints**: `/rest/v1.0/projects/{project_id}/change_events`
- **Data**: Potential cost impacts, change tracking, approval workflows

#### Change Orders
- **Potential Change Orders**: `/rest/v1.0/projects/{project_id}/potential_change_orders`
- **Change Order Requests**: `/rest/v1.0/projects/{project_id}/change_order_requests`
- **Change Order Packages**: `/rest/v1.0/projects/{project_id}/change_order_packages`

#### Supporting Resources
- **Change Types**: `/rest/v1.0/projects/{project_id}/change_types`
- **Change Order Reasons**: `/rest/v1.0/projects/{project_id}/change_order_change_reasons`
- **Change Order Statuses**: `/rest/v1.0/projects/{project_id}/change_order_statuses`

### Data Returned
- Change order details and status
- Cost impacts and justifications
- Approval workflows and signatures
- Related drawings and specifications
- Time impact analysis
- Vendor/contractor involvement

### File/Attachment Support
✅ **YES** - Supporting documents, drawings, specifications, photos

### Limitations
- Complex approval workflows may require careful state management
- Financial data access requires appropriate permissions

---

## ADDITIONAL KEY APIS

### RFIs (Request for Information)
✅ **Full Support**: `/rest/v1.0/projects/{project_id}/rfis`
- Question/response tracking, attachments, approval workflows

### Drawings Management
✅ **Full Support**: Multiple endpoints for drawings, revisions, uploads, areas, sets
- PDF upload/download, revision tracking, markup support

### Documents Management  
✅ **Full Support**: Project folders and files with full CRUD operations
- File organization, version control, access permissions

### Timecards & Timecard Entries
✅ **Full Support**: Employee time tracking and payroll integration

### Punch Lists & Punch Items
✅ **Full Support**: Quality control and closeout management

### Meetings & Meeting Topics
✅ **Full Support**: Meeting management with agenda/minutes and file attachments

---

## FILE UPLOAD/DOWNLOAD ARCHITECTURE

### Direct File Upload System
✅ **ROBUST S3-BASED ARCHITECTURE**

#### Upload Process
1. **Create Upload**: `POST /rest/v1.1/companies/{company_id}/uploads`
2. **Direct S3 Upload**: Use returned URL and headers
3. **Complete Upload**: `PATCH /rest/v1.1/companies/{company_id}/uploads/{uuid}`
4. **Associate with Resource**: Use upload_id in resource creation

#### Supported Features
- **Segmented Uploads**: For large files (5MB+ segments)
- **Non-segmented Uploads**: For smaller files
- **Multiple File Formats**: PDF, images, documents, videos
- **Metadata Preservation**: Filename, content-type, checksums
- **Direct Download URLs**: Authenticated access to files

#### Content-Type Requirements
- **Uploads**: `multipart/form-data`
- **JSON Responses**: `application/json`

---

## WEBHOOK RESOURCE COVERAGE

### Confirmed Webhook Support For:
- ✅ Submittals (create, update, delete)
- ✅ Drawings & Drawing Revisions
- ✅ RFIs 
- ✅ Change Orders & Change Events
- ✅ Observations
- ✅ Daily Logs (all types)
- ✅ Photos/Images
- ✅ Documents
- ✅ Budget Changes
- ✅ Meeting Topics
- ✅ Directory Changes
- ✅ Schedule Tasks
- ✅ Punch Items

### Webhook Configuration
- **Scope**: Company-level or Project-level
- **Namespacing**: Required for app isolation
- **Retry Logic**: Exponential backoff up to 12 hours
- **Delivery Monitoring**: Full audit trail available
- **Security**: HTTPS required, custom headers supported

---

## AUTHENTICATION & SECURITY

### OAuth 2.0 Implementation
- **Authorization**: Bearer token required
- **Scopes**: Tool-specific permissions
- **Company Context**: `Procore-Company-Id` header required
- **Rate Limiting**: Standard API rate limits apply
- **Data Privacy**: Permission-based access control

---

## LIMITATIONS & CONSIDERATIONS

### Current Limitations
1. **Specifications API**: Not yet available (coming soon)
2. **Large File Handling**: Segment-based uploads required for large files
3. **Real-time Updates**: Webhook delivery latency (typically < 5 seconds)
4. **Permission Dependencies**: Tool access required for API endpoints
5. **Rate Limiting**: Standard API throttling applies

### Best Practices
1. **Webhook Idempotency**: Handle duplicate deliveries
2. **File Management**: Use direct S3 uploads for performance
3. **Error Handling**: Implement proper retry logic
4. **Security**: Rotate OAuth tokens regularly
5. **Monitoring**: Use delivery endpoints for webhook debugging

---

## CONCLUSIONS

### Overall Assessment
Procore provides a **comprehensive and mature REST API** covering virtually all aspects of construction project management. The API architecture is well-designed with independent resource versioning, robust file handling, and extensive webhook support for real-time integrations.

### Key Strengths
1. **Complete Coverage**: APIs available for all major construction tools
2. **File Management**: Sophisticated upload/download with S3 integration
3. **Real-time Capabilities**: Comprehensive webhook system
4. **Documentation**: Well-documented with examples and tutorials
5. **Scalability**: Enterprise-ready architecture

### Integration Readiness
**READY FOR FULL INTEGRATION** - All requested functionality is available through well-documented APIs with the exception of Specifications (coming soon, workaround available through Documents API).

**Recommended Integration Approach:**
1. Start with core endpoints (Projects, Documents, Photos)
2. Implement webhook listeners for real-time updates
3. Add specialized tools (Submittals, RFIs, Daily Logs) incrementally
4. Use direct file uploads for optimal performance
5. Monitor API usage and implement appropriate caching strategies

---

*Research completed: February 17, 2026*
*Source Documentation: https://procore.github.io/documentation/ and https://developers.procore.com/*