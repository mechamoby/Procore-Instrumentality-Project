-- =============================================================================
-- SteelSync Intelligence Layer Schema — CC-1.1
-- =============================================================================
--
-- Extends the EVA-00 base schema with tables for signals, synthesis cycles,
-- intelligence items, evidence chains, working memory state, and
-- reinforcement candidates. This is the data foundation for the entire
-- intelligence cycle: signal → synthesis → intelligence item → Command Center.
--
-- Prerequisites: DATABASE-SCHEMA.sql must be applied first (projects table exists)
-- =============================================================================

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE signal_source_type AS ENUM (
    'procore_webhook', 'document_pipeline', 'radar_match', 'manual'
);

CREATE TYPE signal_category AS ENUM (
    'status_change',           -- Category A: RFI/submittal/CO status transitions
    'contradiction',           -- Category B: conflicting data points (synthesis-only)
    'reinforcement',           -- Category C: multiple sources confirming same finding
    'timeline',                -- Category D: schedule/date-related signals
    'actor_pattern',           -- Category E: behavioral patterns (synthesis-only)
    'document_significance',   -- Category D: notable document events
    'cross_project',           -- Category F: patterns across projects (synthesis-only)
    'radar_match'              -- Radar monitoring match
);

CREATE TYPE decay_profile AS ENUM (
    'fast_24h',      -- status changes, routine updates
    'medium_72h',    -- contradictions, moderate concerns
    'slow_7d',       -- reinforced patterns, emerging risks
    'persistent'     -- cross-project correlations, actor patterns
);

CREATE TYPE synthesis_cycle_type AS ENUM (
    'morning_briefing',
    'midday_checkpoint',
    'end_of_day',
    'escalation_review'
);

CREATE TYPE project_health AS ENUM (
    'green', 'yellow', 'red'
);

CREATE TYPE intelligence_item_type AS ENUM (
    'convergence',
    'contradiction',
    'pattern_match',
    'decay_detection',
    'cross_project_correlation',
    'emerging_risk',
    'watch_item'
);

CREATE TYPE intelligence_severity AS ENUM (
    'critical', 'high', 'medium', 'low'
);

CREATE TYPE intelligence_status AS ENUM (
    'new', 'active', 'watch', 'downgraded', 'resolved', 'archived'
);

CREATE TYPE attention_level AS ENUM (
    'immediate', 'today', 'tomorrow_morning', 'this_week', 'monitor'
);

CREATE TYPE evidence_weight AS ENUM (
    'primary', 'supporting', 'circumstantial'
);

CREATE TYPE reinforcement_status AS ENUM (
    'pending', 'promoted', 'discarded'
);

-- =============================================================================
-- SIGNALS TABLE
-- =============================================================================
-- First-class objects generated from ingested data. Each signal is a typed,
-- scored, decaying observation about a project event.

CREATE TABLE signals (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id              UUID NOT NULL REFERENCES projects(id),
    source_type             signal_source_type NOT NULL,
    source_document_id      UUID,                          -- reference to source record
    signal_type             VARCHAR(100) NOT NULL,         -- e.g., 'rfi_became_overdue', 'submittal_rejected'
    signal_category         signal_category NOT NULL,
    summary                 TEXT NOT NULL,
    confidence              DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    strength                DECIMAL(3,2) NOT NULL DEFAULT 1.0 CHECK (strength >= 0.0 AND strength <= 1.0),
    effective_weight        DECIMAL(5,2) DEFAULT 1.0,      -- confidence * strength * source_multiplier * decay_factor
    decay_profile           decay_profile NOT NULL DEFAULT 'medium_72h',
    entity_type             VARCHAR(50),                   -- 'rfi', 'submittal', 'daily_log', etc.
    entity_value            VARCHAR(255),                  -- entity identifier (e.g., RFI number)
    supporting_context_json JSONB,                         -- additional context for synthesis
    last_reinforced_at      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at             TIMESTAMPTZ,
    archived_at             TIMESTAMPTZ,
    synthesis_cycle_id      UUID                           -- FK added after synthesis_cycles table
);

-- =============================================================================
-- SYNTHESIS CYCLES TABLE
-- =============================================================================
-- Tracks each synthesis cycle execution: timing, item counts, health assessment.

CREATE TABLE synthesis_cycles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id),
    cycle_type          synthesis_cycle_type NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    signals_processed   INTEGER DEFAULT 0,
    items_created       INTEGER DEFAULT 0,
    items_updated       INTEGER DEFAULT 0,
    items_resolved      INTEGER DEFAULT 0,
    cycle_summary       TEXT,
    overall_health      project_health,
    model_used          VARCHAR(100),
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    error_log           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Now add the FK from signals to synthesis_cycles
ALTER TABLE signals
    ADD CONSTRAINT fk_signals_synthesis_cycle
    FOREIGN KEY (synthesis_cycle_id) REFERENCES synthesis_cycles(id);

-- =============================================================================
-- INTELLIGENCE ITEMS TABLE
-- =============================================================================
-- First-class outputs of the synthesis pipeline. These are what the PM sees
-- in the Command Center.

CREATE TABLE intelligence_items (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id                  UUID NOT NULL REFERENCES projects(id),
    item_type                   intelligence_item_type NOT NULL,
    title                       VARCHAR(500) NOT NULL,
    summary                     TEXT NOT NULL,
    severity                    intelligence_severity NOT NULL DEFAULT 'medium',
    confidence                  DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status                      intelligence_status NOT NULL DEFAULT 'new',
    first_created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reinforced_at          TIMESTAMPTZ,
    resolved_at                 TIMESTAMPTZ,
    archived_at                 TIMESTAMPTZ,
    synthesis_cycle_id          UUID REFERENCES synthesis_cycles(id),
    source_evidence_count       INTEGER DEFAULT 0,
    recommended_attention_level attention_level NOT NULL DEFAULT 'this_week',
    delivery_channels_json      JSONB                          -- e.g., {"telegram": true, "email": false, "command_center": true}
);

-- =============================================================================
-- INTELLIGENCE ITEM EVIDENCE TABLE
-- =============================================================================
-- Links intelligence items to the signals that produced them. Evidence chain.

CREATE TABLE intelligence_item_evidence (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intelligence_item_id    UUID NOT NULL REFERENCES intelligence_items(id) ON DELETE CASCADE,
    signal_id               UUID NOT NULL REFERENCES signals(id),
    evidence_weight_level   evidence_weight NOT NULL DEFAULT 'supporting',
    added_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes                   TEXT
);

-- =============================================================================
-- WORKING MEMORY STATE TABLE
-- =============================================================================
-- Snapshot of project intelligence state at a point in time. Used by synthesis
-- to track trends and manage the intelligence lifecycle.

CREATE TABLE working_memory_state (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id              UUID NOT NULL REFERENCES projects(id),
    snapshot_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active_item_count       INTEGER DEFAULT 0,
    watch_item_count        INTEGER DEFAULT 0,
    total_signal_count_today INTEGER DEFAULT 0,
    state_json              JSONB          -- tomorrow_watch_list, health_trend, etc.
);

-- =============================================================================
-- REINFORCEMENT CANDIDATES TABLE
-- =============================================================================
-- Potential reinforcement links between signals. The signal generation service
-- writes candidates; synthesis evaluates them.

CREATE TABLE reinforcement_candidates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_signal_id    UUID NOT NULL REFERENCES signals(id),
    source_signal_id    UUID NOT NULL REFERENCES signals(id),
    reason              TEXT NOT NULL,
    confidence          DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status              reinforcement_status NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evaluated_at        TIMESTAMPTZ
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Signals: primary query patterns
CREATE INDEX idx_signals_project_created ON signals(project_id, created_at DESC);
CREATE INDEX idx_signals_project_category ON signals(project_id, signal_category, archived_at)
    WHERE archived_at IS NULL;
CREATE INDEX idx_signals_project_active ON signals(project_id, effective_weight DESC)
    WHERE archived_at IS NULL AND resolved_at IS NULL;
CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_signals_synthesis_cycle ON signals(synthesis_cycle_id)
    WHERE synthesis_cycle_id IS NOT NULL;

-- Signals: JSONB GIN index
CREATE INDEX idx_signals_context_gin ON signals USING GIN (supporting_context_json);

-- Synthesis cycles
CREATE INDEX idx_synthesis_cycles_project ON synthesis_cycles(project_id, started_at DESC);
CREATE INDEX idx_synthesis_cycles_type ON synthesis_cycles(project_id, cycle_type, started_at DESC);

-- Intelligence items: primary query patterns
CREATE INDEX idx_intel_items_project_status ON intelligence_items(project_id, status);
CREATE INDEX idx_intel_items_project_type ON intelligence_items(project_id, item_type, status);
CREATE INDEX idx_intel_items_severity ON intelligence_items(project_id, severity DESC, last_updated_at DESC)
    WHERE status IN ('new', 'active');
CREATE INDEX idx_intel_items_attention ON intelligence_items(recommended_attention_level, project_id)
    WHERE status IN ('new', 'active');
CREATE INDEX idx_intel_items_synthesis_cycle ON intelligence_items(synthesis_cycle_id)
    WHERE synthesis_cycle_id IS NOT NULL;

-- Intelligence items: JSONB GIN index
CREATE INDEX idx_intel_items_channels_gin ON intelligence_items USING GIN (delivery_channels_json);

-- Evidence chain
CREATE INDEX idx_evidence_item ON intelligence_item_evidence(intelligence_item_id);
CREATE INDEX idx_evidence_signal ON intelligence_item_evidence(signal_id);

-- Working memory state
CREATE INDEX idx_working_memory_project ON working_memory_state(project_id, snapshot_at DESC);

-- Working memory: JSONB GIN index
CREATE INDEX idx_working_memory_state_gin ON working_memory_state USING GIN (state_json);

-- Reinforcement candidates
CREATE INDEX idx_reinforcement_target ON reinforcement_candidates(target_signal_id, status);
CREATE INDEX idx_reinforcement_source ON reinforcement_candidates(source_signal_id);
CREATE INDEX idx_reinforcement_pending ON reinforcement_candidates(status, created_at)
    WHERE status = 'pending';

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-update last_updated_at on intelligence_items
CREATE TRIGGER trg_intelligence_items_updated_at
    BEFORE UPDATE ON intelligence_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE signals IS 'First-class signal objects generated from ingested data. Typed, scored, decaying observations about project events.';
COMMENT ON TABLE synthesis_cycles IS 'Tracks each synthesis cycle execution: morning briefing, midday checkpoint, end-of-day, escalation review.';
COMMENT ON TABLE intelligence_items IS 'First-class outputs of the synthesis pipeline. What the PM sees in the Command Center.';
COMMENT ON TABLE intelligence_item_evidence IS 'Evidence chain linking intelligence items to the signals that produced them.';
COMMENT ON TABLE working_memory_state IS 'Point-in-time snapshot of project intelligence state for synthesis trend tracking.';
COMMENT ON TABLE reinforcement_candidates IS 'Potential reinforcement links between signals. Written by signal generation, evaluated by synthesis.';
COMMENT ON COLUMN signals.effective_weight IS 'Computed: confidence * strength * source_multiplier * decay_factor. Updated at write time and during decay sweeps.';
COMMENT ON COLUMN signals.decay_profile IS 'Controls how quickly the signal loses weight: fast_24h, medium_72h, slow_7d, persistent.';
