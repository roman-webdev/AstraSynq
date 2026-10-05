"""Persistence contracts; authentication contracts live in auth.py."""
from typing import Literal
from pydantic import BaseModel, Field

class Health(BaseModel):
    status: Literal['ok', 'ready', 'not_ready']
    service: str = 'astrasynq-api'
    version: str = '0.5.0-rc.1'
    storage: str = 'postgresql'

class Mapping(BaseModel):
    fields: dict[str, str] = Field(description='Canonical field → CSV column; email is required')

class Issue(BaseModel):
    field: str
    code: str

class PreviewRow(BaseModel):
    row_number: int
    data: dict[str, str]
    classification: Literal['valid', 'invalid', 'duplicate']
    issues: list[Issue] = []

class ImportResult(BaseModel):
    id: str
    filename: str
    status: Literal['uploaded', 'mapped', 'analyzed', 'completed']
    columns: list[str]
    mapping: dict[str, str]
    total: int
    valid: int
    invalid: int
    duplicate: int
    inserted: int = 0
    rows: list[PreviewRow]
    created_at: str

class Activity(BaseModel):
    id: str
    filename: str
    created_at: str
    total: int
    valid: int
    invalid: int
    duplicate: int
    status: str

class Summary(BaseModel):
    integration_count: int = 0
    record_count: int
    import_count: int
    valid: int
    invalid: int
    duplicate: int
    quality: float
    series: list[dict]
    imports: list[Activity]
    records: list[dict]
    mode: str = 'postgresql'

class CommitResult(BaseModel):
    import_id: str
    inserted: int
    status: Literal['completed'] = 'completed'
    notifications: str = 'durable outbox'

class IntegrationContract(BaseModel):
    type: Literal['webhook', 'telegram']
    enabled: bool = False
    destination: str

class JobContract(BaseModel):
    id: str
    status: Literal['queued', 'running', 'completed', 'failed']
    processed: int = 0
    total: int = 0

class ErrorResponse(BaseModel):
    detail: dict[str, str]

class ImportPage(BaseModel):
    items: list[Activity]
    total: int
    page: int
    page_size: int

class LeadResult(BaseModel):
    id: str
    import_id: str
    email_normalized: str
    created_at: str
    data: dict[str,str]

class LeadPage(BaseModel):
    items: list[LeadResult]
    total: int
    page: int
    page_size: int



