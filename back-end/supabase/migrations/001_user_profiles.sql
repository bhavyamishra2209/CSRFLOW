-- ============================================================
-- Migration 001: CSRFlow user_profiles + csr_projects
-- 3 roles: csr_head, project_manager, approver
--
-- Run in Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- 1. Create the role enum
DO $$ BEGIN
    CREATE TYPE csr_role AS ENUM (
        'csr_head',
        'project_manager',
        'approver'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        TEXT,
    full_name    TEXT,
    organisation TEXT,
    csr_role     csr_role NOT NULL DEFAULT 'project_manager',
    is_active    BOOLEAN  NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Users read their own profile
CREATE POLICY "users_read_own_profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

-- Users update their own name/org — but NOT their role
CREATE POLICY "users_update_own_profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (
        auth.uid() = id
        AND csr_role = (SELECT csr_role FROM user_profiles WHERE id = auth.uid())
    );

-- Service role (backend) can do everything
CREATE POLICY "service_role_all_profiles"
    ON user_profiles FOR ALL
    USING (auth.role() = 'service_role');

-- 3. Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Auto-create profile on signup (default role: project_manager)
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, csr_role)
    VALUES (NEW.id, NEW.email, 'project_manager')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_on_auth_user_created ON auth.users;
CREATE TRIGGER trg_on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- 5. csr_projects table
-- ============================================================
CREATE TABLE IF NOT EXISTS csr_projects (
    project_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT NOT NULL,
    domain              TEXT NOT NULL,
    description         TEXT DEFAULT '',
    budget              NUMERIC(15,2),
    stage               TEXT NOT NULL DEFAULT 'draft',
    created_by          UUID REFERENCES user_profiles(id),   -- always csr_head
    assigned_pm         UUID REFERENCES user_profiles(id),   -- project_manager
    assigned_approver   UUID REFERENCES user_profiles(id),   -- approver
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    documents           JSONB DEFAULT '[]'::jsonb,
    milestones          JSONB DEFAULT '[]'::jsonb,
    impact_data         JSONB DEFAULT '{}'::jsonb,
    stage_history       JSONB DEFAULT '[]'::jsonb
);

ALTER TABLE csr_projects ENABLE ROW LEVEL SECURITY;

-- csr_head sees all projects
CREATE POLICY "csr_head_all_projects"
    ON csr_projects FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE id = auth.uid() AND csr_role = 'csr_head'
        )
    );

-- project_manager sees only their assigned projects
CREATE POLICY "pm_read_assigned"
    ON csr_projects FOR SELECT
    USING (assigned_pm = auth.uid());

CREATE POLICY "pm_update_assigned"
    ON csr_projects FOR UPDATE
    USING (assigned_pm = auth.uid());

-- approver sees only their assigned projects
CREATE POLICY "approver_read_assigned"
    ON csr_projects FOR SELECT
    USING (assigned_approver = auth.uid());

-- approver can update stage (approve/reject) but NOT their own created project
CREATE POLICY "approver_update_assigned"
    ON csr_projects FOR UPDATE
    USING (
        assigned_approver = auth.uid()
        AND created_by <> auth.uid()   -- cannot approve own work
    );

-- service role bypass
CREATE POLICY "service_role_all_projects"
    ON csr_projects FOR ALL
    USING (auth.role() = 'service_role');

DROP TRIGGER IF EXISTS trg_csr_projects_updated_at ON csr_projects;
CREATE TRIGGER trg_csr_projects_updated_at
    BEFORE UPDATE ON csr_projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 6. stage_transitions audit log
-- ============================================================
CREATE TABLE IF NOT EXISTS stage_transitions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL REFERENCES csr_projects(project_id) ON DELETE CASCADE,
    from_stage    TEXT NOT NULL,
    to_stage      TEXT NOT NULL,
    actor_id      UUID NOT NULL REFERENCES user_profiles(id),
    actor_role    TEXT NOT NULL,
    comment       TEXT DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE stage_transitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_transitions"
    ON stage_transitions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "read_own_project_transitions"
    ON stage_transitions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM csr_projects
            WHERE project_id = stage_transitions.project_id
            AND (
                created_by = auth.uid()
                OR assigned_pm = auth.uid()
                OR assigned_approver = auth.uid()
            )
        )
    );
