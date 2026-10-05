
CREATE TABLE events (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	type VARCHAR(64) NOT NULL, 
	dedupe_key VARCHAR(160) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	UNIQUE (dedupe_key)
)

;
CREATE INDEX ix_events_workspace_id ON events (workspace_id);

CREATE TABLE integration_configs (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	destination VARCHAR(2048) NOT NULL, 
	credential_ref VARCHAR(128) NOT NULL, 
	timeout INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	backoff INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_integration_kind UNIQUE (workspace_id, kind), 
	CONSTRAINT ck_integration_kind CHECK (kind IN ('webhook','telegram')), 
	CONSTRAINT ck_integration_policy CHECK (timeout BETWEEN 1 AND 20 AND max_attempts BETWEEN 1 AND 10 AND backoff BETWEEN 1 AND 3600), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

;

CREATE TABLE deliveries (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	event_id UUID NOT NULL, 
	integration_id UUID NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	attempts INTEGER NOT NULL, 
	response_code INTEGER, 
	last_error VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	delivered_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_event_delivery UNIQUE (event_id, integration_id), 
	CONSTRAINT ck_delivery_status CHECK (status IN ('queued','running','retry','delivered','failed','paused')), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE, 
	FOREIGN KEY(integration_id) REFERENCES integration_configs (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_deliveries_workspace_id ON deliveries (workspace_id);

CREATE TABLE jobs (
	id UUID NOT NULL, 
	event_id UUID NOT NULL, 
	delivery_id UUID, 
	dedupe_key VARCHAR(160) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	attempts INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	backoff INTEGER NOT NULL, 
	run_after TIMESTAMP WITH TIME ZONE NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	heartbeat_at TIMESTAMP WITH TIME ZONE, 
	lease_token UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_job_status CHECK (status IN ('queued','running','retry','completed','failed','paused')), 
	CONSTRAINT ck_job_attempts CHECK (attempts >= 0 AND max_attempts BETWEEN 1 AND 10), 
	FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE, 
	UNIQUE (delivery_id), 
	FOREIGN KEY(delivery_id) REFERENCES deliveries (id) ON DELETE CASCADE, 
	UNIQUE (dedupe_key)
)

;
CREATE INDEX ix_job_claim ON jobs (status, run_after, lease_until);

CREATE TABLE schedules (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	next_run_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (workspace_id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_schedules_next_run_at ON schedules (next_run_at);
