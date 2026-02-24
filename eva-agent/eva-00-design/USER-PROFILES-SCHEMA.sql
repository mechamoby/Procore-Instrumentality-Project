-- =============================================================================
-- USER PROFILES — Multi-User Multi-Project Access Control
-- =============================================================================
-- 
-- This schema enables Katsuragi (and EVAs) to identify who is talking,
-- what role they have, and which projects they can access.
--
-- Flow:
--   1. Telegram message arrives from chat_id 12345
--   2. Katsuragi queries: SELECT * FROM user_profiles WHERE chat_id = '12345'
--   3. Gets back: name, role, active projects, permissions
--   4. Routes request with full context
--
-- Roles:
--   - admin:           Full access, can manage users and all projects
--   - project_manager: Full project access for assigned projects
--   - superintendent:  Field-focused access (daily reports, photos, punch lists)
--   - assistant_pm:    Similar to PM but may have limited approval authority
--   - executive:       Read-only cross-project visibility, dashboards, summaries
--   - subcontractor:   Limited access to their scope on assigned projects
--   - read_only:       View-only access (auditors, consultants, etc.)
-- =============================================================================

CREATE TYPE user_role AS ENUM (
    'admin',
    'project_manager', 
    'superintendent',
    'assistant_pm',
    'executive',
    'subcontractor',
    'read_only'
);

CREATE TYPE user_status AS ENUM (
    'active',
    'inactive',
    'pending_approval',
    'suspended'
);

-- =============================================================================
-- CORE USER TABLE
-- =============================================================================

CREATE TABLE user_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identity
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    
    -- Chat platform identifiers (polymorphic — supports future channels)
    chat_id         TEXT NOT NULL UNIQUE,       -- Telegram user ID (primary identifier)
    chat_platform   TEXT NOT NULL DEFAULT 'telegram',  -- telegram, whatsapp, etc.
    chat_username   TEXT,                       -- @username if available
    
    -- Link to existing contacts/companies tables
    contact_id      UUID REFERENCES contacts(id),
    company_id      UUID REFERENCES companies(id),
    
    -- Global role (highest-level permission)
    role            user_role NOT NULL DEFAULT 'read_only',
    status          user_status NOT NULL DEFAULT 'pending_approval',
    
    -- Procore linkage
    procore_user_id BIGINT,                    -- maps to Procore user for attribution
    
    -- Preferences
    default_project_id UUID REFERENCES projects(id),  -- auto-context when ambiguous
    timezone        TEXT DEFAULT 'America/New_York',
    notification_prefs JSONB DEFAULT '{"submittals": true, "rfis": true, "daily_reports": true, "urgent_only": false}'::jsonb,
    
    -- Metadata
    last_active_at  TIMESTAMPTZ,
    onboarded_at    TIMESTAMPTZ,               -- when they completed first interaction
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(first_name || ' ' || last_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(email, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(chat_username, '')), 'B')
    ) STORED
);

-- =============================================================================
-- PROJECT ACCESS — Which users can access which projects, with what role
-- =============================================================================
-- 
-- A user's global role sets their ceiling. Project-level role can be
-- equal to or lower than their global role (never higher).
--
-- Examples:
--   - PM globally, PM on Project A, superintendent on Project B (helping out in field)
--   - Executive globally → auto-gets read_only on ALL projects (no entry needed)
--   - Subcontractor globally, subcontractor on Projects A and C only
-- =============================================================================

CREATE TABLE user_project_access (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES user_profiles(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    
    -- Project-specific role (ceiling = global role)
    project_role    user_role NOT NULL,
    
    -- Granular permissions (overrides role defaults when set)
    can_create_submittals   BOOLEAN,    -- NULL = inherit from role
    can_approve_submittals  BOOLEAN,
    can_create_rfis         BOOLEAN,
    can_create_daily_reports BOOLEAN,
    can_view_financials     BOOLEAN,
    can_manage_users        BOOLEAN,
    
    -- Scope limits for subcontractors
    scope_spec_sections     TEXT[],     -- e.g., ['03 30 00', '03 35 00'] for concrete sub
    scope_trades            TEXT[],     -- e.g., ['Concrete', 'Rebar']
    scope_company_id        UUID REFERENCES companies(id),  -- their company on this project
    
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    granted_by      UUID REFERENCES user_profiles(id),
    granted_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, project_id)
);

-- =============================================================================
-- ROLE PERMISSION DEFAULTS
-- =============================================================================
-- Reference table: what each role can do by default.
-- user_project_access booleans override these when non-NULL.
-- =============================================================================

CREATE TABLE role_permissions (
    role                    user_role PRIMARY KEY,
    can_create_submittals   BOOLEAN NOT NULL DEFAULT FALSE,
    can_approve_submittals  BOOLEAN NOT NULL DEFAULT FALSE,
    can_create_rfis         BOOLEAN NOT NULL DEFAULT FALSE,
    can_create_daily_reports BOOLEAN NOT NULL DEFAULT FALSE,
    can_view_financials     BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_users        BOOLEAN NOT NULL DEFAULT FALSE,
    cross_project_view      BOOLEAN NOT NULL DEFAULT FALSE,  -- can see all projects
    description             TEXT
);

INSERT INTO role_permissions VALUES
    ('admin',           TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  'Full system access'),
    ('project_manager', TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  FALSE, FALSE, 'Full project access for assigned projects'),
    ('superintendent',  FALSE, FALSE, TRUE,  TRUE,  FALSE, FALSE, FALSE, 'Field-focused: daily reports, RFIs, photos'),
    ('assistant_pm',    TRUE,  FALSE, TRUE,  TRUE,  FALSE, FALSE, FALSE, 'PM support: can create but not approve'),
    ('executive',       FALSE, FALSE, FALSE, FALSE, TRUE,  FALSE, TRUE,  'Read-only cross-project dashboards'),
    ('subcontractor',   TRUE,  FALSE, TRUE,  TRUE,  FALSE, FALSE, FALSE, 'Limited to their trade scope on assigned projects'),
    ('read_only',       FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, 'View-only access');

-- =============================================================================
-- CONVERSATION CONTEXT — Helps Katsuragi maintain state per user
-- =============================================================================
-- 
-- Tracks the "working context" for each user so Katsuragi doesn't have
-- to ask "which project?" every time when it's obvious.
-- =============================================================================

CREATE TABLE user_context (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES user_profiles(id) UNIQUE,
    
    -- Current working context
    active_project_id UUID REFERENCES projects(id),    -- last project they were working on
    active_submittal_id UUID REFERENCES submittals(id), -- last submittal discussed
    active_rfi_id   UUID REFERENCES rfis(id),           -- last RFI discussed
    
    -- Inference state
    last_intent     TEXT,                   -- 'submittal', 'rfi', 'daily_report', 'query', etc.
    last_message_at TIMESTAMPTZ,
    context_expires_at TIMESTAMPTZ,         -- auto-clear after inactivity (e.g., 4 hours)
    
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- USER ACTIVITY LOG — Lightweight per-user audit
-- =============================================================================

CREATE TABLE user_activity_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES user_profiles(id),
    action          TEXT NOT NULL,           -- 'login', 'submittal_created', 'rfi_viewed', 'query', etc.
    entity_type     TEXT,
    entity_id       UUID,
    project_id      UUID REFERENCES projects(id),
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Primary lookup: who is this chat user?
CREATE UNIQUE INDEX idx_user_profiles_chat ON user_profiles(chat_platform, chat_id);
CREATE INDEX idx_user_profiles_search ON user_profiles USING GIN (search_vector);
CREATE INDEX idx_user_profiles_status ON user_profiles(status) WHERE status = 'active';
CREATE INDEX idx_user_profiles_role ON user_profiles(role);
CREATE INDEX idx_user_profiles_company ON user_profiles(company_id);
CREATE INDEX idx_user_profiles_procore ON user_profiles(procore_user_id) WHERE procore_user_id IS NOT NULL;

-- Project access lookups
CREATE INDEX idx_user_project_access_user ON user_project_access(user_id);
CREATE INDEX idx_user_project_access_project ON user_project_access(project_id);
CREATE INDEX idx_user_project_access_active ON user_project_access(user_id) WHERE is_active = TRUE;

-- Context lookup (fast per-user)
CREATE INDEX idx_user_context_user ON user_context(user_id);

-- Activity log (time-series)
CREATE INDEX idx_user_activity_user ON user_activity_log(user_id, created_at DESC);
CREATE INDEX idx_user_activity_project ON user_activity_log(project_id, created_at DESC);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER trg_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_user_context_updated_at 
    BEFORE UPDATE ON user_context 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Get a user's effective permission for a project
-- Checks project-level override first, then falls back to role default
CREATE OR REPLACE FUNCTION get_user_permission(
    p_user_id UUID,
    p_project_id UUID,
    p_permission TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_override BOOLEAN;
    v_role_default BOOLEAN;
    v_user_role user_role;
    v_project_role user_role;
    v_has_cross_project BOOLEAN;
BEGIN
    -- Get user's global role
    SELECT role INTO v_user_role FROM user_profiles WHERE id = p_user_id;
    
    -- Check if role has cross-project view (executives see everything)
    SELECT cross_project_view INTO v_has_cross_project 
    FROM role_permissions WHERE role = v_user_role;
    
    -- Get project-specific access
    SELECT project_role,
           CASE p_permission
               WHEN 'create_submittals' THEN can_create_submittals
               WHEN 'approve_submittals' THEN can_approve_submittals
               WHEN 'create_rfis' THEN can_create_rfis
               WHEN 'create_daily_reports' THEN can_create_daily_reports
               WHEN 'view_financials' THEN can_view_financials
               WHEN 'manage_users' THEN can_manage_users
           END
    INTO v_project_role, v_override
    FROM user_project_access
    WHERE user_id = p_user_id AND project_id = p_project_id AND is_active = TRUE;
    
    -- If explicit project override exists, use it
    IF v_override IS NOT NULL THEN
        RETURN v_override;
    END IF;
    
    -- If user has project access, use project role defaults
    IF v_project_role IS NOT NULL THEN
        SELECT CASE p_permission
            WHEN 'create_submittals' THEN can_create_submittals
            WHEN 'approve_submittals' THEN can_approve_submittals
            WHEN 'create_rfis' THEN can_create_rfis
            WHEN 'create_daily_reports' THEN can_create_daily_reports
            WHEN 'view_financials' THEN can_view_financials
            WHEN 'manage_users' THEN can_manage_users
        END INTO v_role_default
        FROM role_permissions WHERE role = v_project_role;
        RETURN COALESCE(v_role_default, FALSE);
    END IF;
    
    -- If executive with cross-project view, allow read-level access
    IF v_has_cross_project THEN
        -- Executives can view but not create/modify
        IF p_permission IN ('view_financials') THEN
            RETURN TRUE;
        END IF;
        RETURN FALSE;
    END IF;
    
    -- No access
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- Quick lookup: get all projects a user can access
CREATE OR REPLACE FUNCTION get_user_projects(p_user_id UUID)
RETURNS TABLE(project_id UUID, project_name TEXT, project_role user_role) AS $$
BEGIN
    RETURN QUERY
    SELECT p.id, p.name, upa.project_role
    FROM user_project_access upa
    JOIN projects p ON p.id = upa.project_id
    WHERE upa.user_id = p_user_id 
      AND upa.is_active = TRUE
      AND p.is_deleted = FALSE
      AND p.status = 'active'
    ORDER BY p.name;
END;
$$ LANGUAGE plpgsql STABLE;

-- Quick lookup: identify user from chat
CREATE OR REPLACE FUNCTION identify_user(p_chat_id TEXT, p_platform TEXT DEFAULT 'telegram')
RETURNS TABLE(
    user_id UUID, 
    first_name TEXT, 
    last_name TEXT, 
    role user_role, 
    status user_status,
    default_project_id UUID,
    active_project_id UUID,
    project_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        up.id,
        up.first_name,
        up.last_name,
        up.role,
        up.status,
        up.default_project_id,
        uc.active_project_id,
        (SELECT COUNT(*) FROM user_project_access upa WHERE upa.user_id = up.id AND upa.is_active = TRUE)
    FROM user_profiles up
    LEFT JOIN user_context uc ON uc.user_id = up.id
    WHERE up.chat_id = p_chat_id 
      AND up.chat_platform = p_platform
      AND up.status = 'active';
    
    -- Update last_active timestamp
    UPDATE user_profiles SET last_active_at = NOW() 
    WHERE chat_id = p_chat_id AND chat_platform = p_platform;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE user_profiles IS 'Maps chat platform users to roles and project access. Primary lookup by chat_id.';
COMMENT ON TABLE user_project_access IS 'Per-project role and permission overrides. Global role = ceiling.';
COMMENT ON TABLE role_permissions IS 'Default permissions per role. Project-level booleans override when non-NULL.';
COMMENT ON TABLE user_context IS 'Conversational state per user — helps Katsuragi avoid redundant questions.';
COMMENT ON FUNCTION identify_user IS 'Primary entry point: Katsuragi calls this on every inbound message to know who is talking.';
COMMENT ON FUNCTION get_user_permission IS 'Check if a user can perform an action on a specific project. Handles role hierarchy + overrides.';
