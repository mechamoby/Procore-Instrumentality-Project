# CC-2.6 Signal Deduplication — Test Results

```
========================================================================
CC-2.6 SIGNAL DEDUPLICATION TEST RESULTS
Executed: 2026-03-12T09:33:30.633044
Test project ID: 0827cef6-4a29-4b9b-9c51-b77c8ec88908
========================================================================

[PASS] 1. Exact duplicate rejected
       First signal: c4c4288c-59c8-4ed3-934b-1879a597ab69
       Second signal: None
       Signal count: 1

[PASS] 2. Same source, different signal type → both accepted
       Signal 1 (rfis_overdue): fc3418bc-b6f5-4ae4-a248-3ef285168be4
       Signal 2 (submittals_overdue): 4feae4b2-1f3f-4374-a3fc-5f7fd5c10c64
       Signal count: 2

[PASS] 3. Different source, same signal type → both accepted
       Signal 1: dd5246cb-10e6-4770-8b1d-3ac036b4120f
       Signal 2: 9d394811-8a8a-48f2-b611-dca1bc21bddd
       Signal count: 2

[PASS] 4. Time window boundary (61 min) → second signal accepted
       Signal 1 (backdated 61min): 564080d2-4f24-41b7-bceb-e2438a3c7af7
       Signal 2 (current): 5e9b184e-5466-4699-b5af-89247dc735d4
       Signal count: 2

[PASS] 5. Cross-project isolation
       Signal 1 (project A): 16cb083a-665f-4ebd-b71a-aafe485fdd16
       Signal 2 (project B): a53f5919-402c-4c85-a108-33e0d8453ab5
       Count A: 1, Count B: 1
       Cross-project isolation: WORKING

[PASS] 6. Path A vs Path B dedup (webhook then document pipeline)
       Path A signal: 99cc36c6-2977-43bc-ad36-38484fb248cf
       Path B result: 99cc36c6-2977-43bc-ad36-38484fb248cf
       Signal count: 1 (correctly deduped)
       Context merged: True
       Final context keys: ['path', 'analysis', 'days_overdue']

[PASS] 6b. Context merge on dedup (bonus test)
       Original signal: a5ecdbf6-9a46-4b00-a961-a6c8ad0f89d7
       Dedup returned: a5ecdbf6-9a46-4b00-a961-a6c8ad0f89d7
       Context after merge: {
         "source": "webhook",
         "assignee": "Smith",
         "rfi_number": 42
       }
       Signal count: 1

------------------------------------------------------------------------
TOTAL: 7 tests | 7 passed | 0 failed
========================================================================
```
