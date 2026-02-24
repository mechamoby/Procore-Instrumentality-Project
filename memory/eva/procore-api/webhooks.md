# Webhooks API Documentation
> Status: **UNEXPLORED** - Authentication needed for testing
> Priority: **HIGH** - Critical for real-time EVA integrations

## Overview
Webhooks enable real-time notifications when objects change in Procore. This is essential for EVA to respond immediately to events like:
- New RFI created → Auto-draft response
- Submittal approved → Notify project team  
- Daily log submitted → Analyze and flag issues
- Safety incident reported → Immediate escalation

## Expected Endpoints

### List Webhooks
```
GET /rest/v1.0/companies/{company_id}/webhooks
GET /rest/v1.0/projects/{project_id}/webhooks
```

### Create Webhook
```
POST /rest/v1.0/companies/{company_id}/webhooks
Content-Type: application/json

{
  "webhook": {
    "destination_url": "https://eva.ai/webhooks/procore",
    "event_type": "Daily Log.Created",
    "active": true,
    "secret_key": "webhook_secret_for_verification"
  }
}
```

### Update Webhook
```
PATCH /rest/v1.0/companies/{company_id}/webhooks/{id}
```

### Delete Webhook
```
DELETE /rest/v1.0/companies/{company_id}/webhooks/{id}
```

### Test Webhook
```
POST /rest/v1.0/companies/{company_id}/webhooks/{id}/test
```

## Expected Event Types
Based on our priorities for EVA:

### Daily Logs
- `Daily Log.Created`
- `Daily Log.Updated` 
- `Daily Log.Deleted`

### RFIs
- `RFI.Created`
- `RFI.Updated`
- `RFI.Answered`
- `RFI.Closed`

### Submittals  
- `Submittal.Created`
- `Submittal.Updated`
- `Submittal.Approved`
- `Submittal.Rejected`
- `Submittal.Returned`

### Inspections
- `Inspection.Created`
- `Inspection.Completed`
- `Inspection.Failed`

### Safety
- `Observation.Created` (safety incidents)
- `Accident.Created`

### Change Management
- `Change Order.Created`
- `Change Order.Approved`
- `Potential Change Order.Created`

### Documents
- `Document.Created`
- `Document.Updated`

## Expected Webhook Payload Structure
```json
{
  "webhook_id": 12345,
  "event_type": "Daily Log.Created", 
  "timestamp": "2026-02-19T08:30:00Z",
  "company_id": 4281379,
  "project_id": 316469,
  "object_type": "Daily Log",
  "object_id": 67890,
  "object": {
    "id": 67890,
    "date": "2026-02-19",
    "weather": "Sunny, 65°F",
    "created_by": {
      "id": 174986,
      "name": "John Superintendent"
    },
    "created_at": "2026-02-19T08:30:00Z",
    ...
  },
  "changes": {
    "weather": {
      "from": null,
      "to": "Sunny, 65°F"
    }
  }
}
```

## Webhook Security
- **Signature Verification** - Procore likely signs webhook payloads
- **Secret Key** - Shared secret for HMAC verification  
- **IP Whitelisting** - Restrict to Procore's webhook servers
- **HTTPS Required** - Only HTTPS destinations allowed

## EVA Integration Architecture

### Webhook Handler Service
```
POST /webhooks/procore
- Verify webhook signature
- Parse event type and payload
- Route to appropriate EVA service
- Return 200 OK quickly (< 5s)
```

### Event Processing Pipeline
1. **Immediate Response** - Acknowledge webhook (< 5s)
2. **Queue Processing** - Async processing of events
3. **AI Analysis** - Run AI models on event data
4. **Action Triggers** - Execute EVA automations
5. **Error Handling** - Retry failed processing

### Priority Event Handlers

**Daily Log.Created**
- Extract weather, progress, issues
- Flag potential delays or problems
- Update project dashboards
- Trigger progress analysis

**RFI.Created**  
- Analyze RFI content for category/urgency
- Auto-draft response suggestions
- Notify relevant team members
- Update response time metrics

**Submittal.Approved**
- Update project schedules
- Notify procurement team
- Trigger next phase activities
- Update compliance tracking

## Testing Strategy

### Phase 1: Basic Webhook Setup
1. Create webhook for Daily Log.Created
2. Verify payload structure and format
3. Test signature verification
4. Confirm retry behavior

### Phase 2: Event Coverage
1. Test all priority event types
2. Document payload differences
3. Identify which events include full object vs. just ID
4. Test batch/bulk operation events

### Phase 3: Production Readiness  
1. Load testing with high-volume events
2. Error handling and retry logic
3. Rate limiting and throttling
4. Monitoring and alerting

## Configuration Management
```json
{
  "webhook_configs": {
    "daily_logs": {
      "events": ["Daily Log.Created", "Daily Log.Updated"],
      "enabled": true,
      "destination": "https://eva.ai/webhooks/daily-logs"
    },
    "rfis": {
      "events": ["RFI.Created", "RFI.Answered"],  
      "enabled": true,
      "destination": "https://eva.ai/webhooks/rfis"
    }
  }
}
```

## Rate Limiting Considerations
- Webhook delivery rate limits
- Retry policies for failed deliveries
- Backoff strategies for high-volume events
- Circuit breakers for failing endpoints

## Monitoring & Observability
- Webhook delivery success rates
- Processing latency metrics  
- Event volume monitoring
- Failed delivery alerting
- Signature verification failures

## Known Gotchas (to investigate)
1. **Webhook Ordering** - Are events guaranteed in chronological order?
2. **Duplicate Events** - Idempotency handling required?
3. **Partial Updates** - What's included in change deltas?
4. **Bulk Operations** - Single webhook or multiple for bulk changes?
5. **User Context** - Is the triggering user included in payloads?
6. **Permissions** - Do webhooks respect user permissions for data access?

## Next Steps (once auth restored)
1. Create test webhook for Daily Log events
2. Trigger events in sandbox and capture payloads  
3. Document actual payload structures
4. Test webhook signature verification
5. Build EVA webhook handler service
6. Implement priority event processors