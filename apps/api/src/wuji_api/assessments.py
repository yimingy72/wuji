"""W1 bounded, evidence-based assessment contracts."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

Verdict = Literal["unassessed", "confirmed", "not_reproduced", "inconclusive"]
Outcome = Literal["not_assessed", "complete", "partial", "inconclusive"]

class CoverageItem(Strict):
    id: UUID
    target_url: str
    rule_id: Literal["cors-reflection-v1"] = "cors-reflection-v1"
    state: Literal["pending", "evaluated", "blocked", "inconclusive", "not_run"]
    verdict: Verdict | None = None
    verification_run_id: UUID | None = None
    result_id: UUID | None = None
    reason: str | None = None

class AssessmentReference(Strict):
    plan_id: UUID
    revision: int = Field(ge=1)
    outcome: Outcome

class AssessmentView(Strict):
    state: Literal["not_assessed", "available"]
    profile_id: str | None = None
    plan_id: UUID | None = None
    revision: int = Field(default=0,ge=0)
    progress_digest: str | None = None
    outcome: Outcome = "not_assessed"
    discovery_state: Literal["pending", "complete", "incomplete"] = "pending"
    items: list[CoverageItem] = Field(default_factory=list,max_length=11)
    limitations: list[str] = Field(default_factory=list,max_length=30)

class Observation(Strict):
    id: UUID
    tool_call_id: UUID
    agent_run_id: UUID
    target_url: str
    method: Literal["GET", "HEAD", "OPTIONS"]
    request_headers: dict[str,str]
    response_status: int | None
    response_headers: dict[str,str]
    complete: bool
    termination: Literal["complete","size_limit","timeout","cancelled","network_error"]
    body_bytes: int = Field(ge=0,le=1048576)
    body_sha256: str
    body_encoding: Literal["client-decoded"]
    redacted_headers: list[str]
    artifact_id: UUID
    body_artifact_id: UUID
    started_at: datetime
    finished_at: datetime
    created_at: datetime

class ObservationPage(Strict):
    items: list[Observation] = Field(max_length=100)
    next_cursor: str | None

class VerificationResult(Strict):
    id: UUID
    verification_run_id: UUID
    revision: int = Field(ge=1)
    verdict: Verdict
    reason: str
    limitations: list[str]
    supersedes_result_id: UUID | None
    created_at: datetime

class VerificationRun(Strict):
    id: UUID
    coverage_item_id: UUID
    target_url: str
    rule_id: Literal["cors-reflection-v1"]
    claim: str
    agent_run_id: UUID
    intent_id: str | None
    created_at: datetime
    latest_result: VerificationResult | None = None

class VerificationPage(Strict):
    items: list[VerificationRun] = Field(max_length=100)
    next_cursor: str | None

class EvidenceLink(Strict):
    id: UUID
    verification_result_id: UUID
    observation_id: UUID
    artifact_id: UUID
    relation: Literal["supports","refutes","limits"]
    selector: dict

class VerificationDetail(Strict):
    verification: VerificationRun
    results: list[VerificationResult] = Field(max_length=100)
    evidence: list[EvidenceLink] = Field(max_length=200)

class VerificationSubmit(Strict):
    rule_id: Literal["cors-reflection-v1"]
    tool_call_ids: list[UUID] = Field(min_length=1,max_length=2)
    limitations: list[str] = Field(default_factory=list,max_length=10)
    supersedes_result_id: UUID | None = None

    @field_validator("tool_call_ids")
    @classmethod
    def distinct(cls,value):
        if len(set(value))!=len(value):raise ValueError("duplicate tool reference")
        return value

    @field_validator("limitations")
    @classmethod
    def bounded_text(cls,value):
        if any(not text.strip() or len(text)>500 for text in value):raise ValueError("invalid limitation")
        return value

class HttpRequest(Strict):
    url: str = Field(min_length=1,max_length=2048)
    method: Literal["GET","HEAD","OPTIONS"] = "GET"
    headers: dict[str,str] = Field(default_factory=dict)

    @field_validator("headers")
    @classmethod
    def allowed_headers(cls,value):
        normalized={}
        for key,item in value.items():
            name=key.lower()
            if name not in {"accept","origin"} or name in normalized or any(c in key+item for c in "\r\n\0"):
                raise ValueError("header denied")
            normalized[name]=item
        if sum(len((k+": "+v+"\r\n").encode()) for k,v in normalized.items())>8192:
            raise ValueError("headers too large")
        return normalized

class HttpExchange(Strict):
    schema_version: Literal["http.exchange.v1"]
    url: str
    method: Literal["GET","HEAD","OPTIONS"]
    request_headers: dict[str,str]
    status: int | None = Field(ge=100,le=599)
    response_headers: dict[str,str]
    body_base64: str = Field(max_length=1398104)
    body_bytes: int = Field(ge=0,le=1048576)
    body_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    body_encoding: Literal["client-decoded"]
    started_at: datetime
    finished_at: datetime
    complete: bool
    termination: Literal["complete","size_limit","timeout","cancelled","network_error"]
    redacted_headers: list[str]
