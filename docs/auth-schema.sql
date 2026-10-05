BEGIN;

-- Running upgrade 6d131c25bdd2 -> a3auth0000001

CREATE TABLE users (
    id UUID NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    password_hash VARCHAR(512) NOT NULL, 
    active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_user_email CHECK (email = lower(btrim(email)) AND length(email) > 3), 
    UNIQUE (email)
);

CREATE TABLE audit_logs (
    id UUID NOT NULL, 
    workspace_id UUID, 
    actor_id UUID, 
    action VARCHAR(64) NOT NULL, 
    entity VARCHAR(64) NOT NULL, 
    entity_id VARCHAR(64), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL, 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_workspace_created ON audit_logs (workspace_id, created_at, id);

CREATE TABLE workspace_memberships (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    role VARCHAR(16) NOT NULL, 
    active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_membership_role CHECK (role IN ('admin','operator','viewer')), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    CONSTRAINT uq_membership_scope UNIQUE (id, workspace_id), 
    UNIQUE (user_id)
);

CREATE INDEX ix_workspace_memberships_workspace_id ON workspace_memberships (workspace_id);

CREATE TABLE sessions (
    id UUID NOT NULL, 
    membership_id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_session_expiry CHECK (expires_at > created_at), 
    CONSTRAINT fk_session_membership_scope FOREIGN KEY(membership_id, workspace_id) REFERENCES workspace_memberships (id, workspace_id) ON DELETE CASCADE, 
    UNIQUE (token_hash)
);

CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

CREATE INDEX ix_sessions_membership_id ON sessions (membership_id);

UPDATE alembic_version SET version_num='a3auth0000001' WHERE alembic_version.version_num = '6d131c25bdd2';

COMMIT;

