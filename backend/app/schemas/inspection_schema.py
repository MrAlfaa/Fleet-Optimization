from __future__ import annotations

from datetime import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.inspection_model import (
    INSPECTION_CHECK_OUTCOMES,
    INSPECTION_DECISIONS,
    INSPECTION_PRIORITIES,
    INSPECTION_STATUSES,
)
from app.models.maintenance_model import MAINTENANCE_PRIORITIES, MAINTENANCE_SYSTEMS
from app.utils.validators import validate_choice, validate_non_empty


def _object_id(value: str) -> str:
    value = validate_non_empty(value)
    if not ObjectId.is_valid(value):
        raise ValueError("Value must be a valid ObjectId")
    return value


class InspectionCreateRequest(BaseModel):
    vehicle_id: str
    inspection_type: Literal["risk_assessment", "commissioning"] = "risk_assessment"
    assessment_id: str | None = None
    feature_hash: str | None = Field(default=None, min_length=6, max_length=128)
    priority: str = "medium"
    inspection_areas: list[str] = Field(default_factory=list, max_length=14)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("vehicle_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return _object_id(value)

    @field_validator("assessment_id")
    @classmethod
    def valid_optional_assessment_id(cls, value: str | None) -> str | None:
        return _object_id(value) if value is not None else None

    @field_validator("feature_hash")
    @classmethod
    def normalized_feature_hash(cls, value: str | None) -> str | None:
        return validate_non_empty(value, "Feature hash") if value is not None else None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        return validate_choice(value, INSPECTION_PRIORITIES, "Inspection priority")

    @field_validator("inspection_areas")
    @classmethod
    def unique_areas(cls, values: list[str]) -> list[str]:
        normalized = [validate_non_empty(value, "Inspection area") for value in values]
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("Inspection areas must be unique")
        return normalized

    @model_validator(mode="after")
    def assessment_fields_match_inspection_type(self):
        if self.inspection_type == "risk_assessment" and (not self.assessment_id or not self.feature_hash):
            raise ValueError("assessment_id and feature_hash are required for risk assessment inspections")
        if self.inspection_type == "commissioning" and (self.assessment_id or self.feature_hash):
            raise ValueError("Commissioning inspections cannot reference an assessment")
        return self


class InspectionAssignRequest(BaseModel):
    assigned_to: str
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("assigned_to")
    @classmethod
    def valid_assignee(cls, value: str) -> str:
        return _object_id(value)


class InspectionAssigneeResponse(BaseModel):
    id: str
    full_name: str
    role: Literal["admin", "maintenance_manager"]

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return _object_id(value)

    @field_validator("full_name")
    @classmethod
    def non_empty_name(cls, value: str) -> str:
        return validate_non_empty(value, "Full name")


class InspectionStartRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class InspectionChecklistItem(BaseModel):
    key: str = Field(max_length=80)
    label: str = Field(max_length=160)
    outcome: str
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator("key", "label")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)

    @field_validator("outcome")
    @classmethod
    def valid_outcome(cls, value: str) -> str:
        return validate_choice(value, INSPECTION_CHECK_OUTCOMES, "Checklist outcome")

    @model_validator(mode="after")
    def failed_item_requires_remark(self):
        if self.outcome == "failed" and not (self.remark and self.remark.strip()):
            raise ValueError("A remark is required for a failed checklist item")
        if self.remark is not None:
            self.remark = self.remark.strip() or None
        return self


class InspectionCompleteRequest(BaseModel):
    checklist: list[InspectionChecklistItem] = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=3, max_length=4000)

    @field_validator("summary")
    @classmethod
    def non_empty_summary(cls, value: str) -> str:
        return validate_non_empty(value, "Inspection summary")

    @field_validator("checklist")
    @classmethod
    def unique_checklist_keys(cls, values: list[InspectionChecklistItem]) -> list[InspectionChecklistItem]:
        keys = [item.key.casefold() for item in values]
        if len(set(keys)) != len(keys):
            raise ValueError("Checklist item keys must be unique")
        return values


class InspectionDraftRequest(BaseModel):
    checklist: list[InspectionChecklistItem] | None = Field(default=None, max_length=100)
    summary: str | None = Field(default=None, max_length=4000)

    @field_validator("summary")
    @classmethod
    def normalized_summary(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("checklist")
    @classmethod
    def unique_checklist_keys(
        cls, values: list[InspectionChecklistItem] | None
    ) -> list[InspectionChecklistItem] | None:
        if values is None:
            return None
        keys = [item.key.casefold() for item in values]
        if len(set(keys)) != len(keys):
            raise ValueError("Checklist item keys must be unique")
        return values


class InspectionCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("reason")
    @classmethod
    def non_empty_reason(cls, value: str) -> str:
        return validate_non_empty(value, "Cancellation reason")


class InspectionDecisionRequest(BaseModel):
    decision: str
    notes: str = Field(min_length=3, max_length=4000)
    maintenance_system: str | None = None
    issue_type: str | None = Field(default=None, max_length=500)
    priority: str | None = None
    estimated_cost: float | None = Field(default=None, ge=0)

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value: str) -> str:
        return validate_choice(value, INSPECTION_DECISIONS, "Inspection decision")

    @field_validator("notes")
    @classmethod
    def non_empty_notes(cls, value: str) -> str:
        return validate_non_empty(value, "Decision notes")

    @field_validator("maintenance_system")
    @classmethod
    def valid_maintenance_system(cls, value: str | None) -> str | None:
        return validate_choice(value, MAINTENANCE_SYSTEMS, "Maintenance system") if value is not None else value

    @field_validator("priority")
    @classmethod
    def valid_maintenance_priority(cls, value: str | None) -> str | None:
        return validate_choice(value, MAINTENANCE_PRIORITIES, "Priority") if value is not None else value

    @field_validator("issue_type")
    @classmethod
    def normalized_issue_type(cls, value: str | None) -> str | None:
        return validate_non_empty(value, "Issue type") if value is not None else value

    @model_validator(mode="after")
    def maintenance_decision_requires_work_scope(self):
        if self.decision == "maintenance_required":
            required = ("maintenance_system", "issue_type", "priority", "estimated_cost")
            missing = [field for field in required if getattr(self, field) is None]
            if missing:
                raise ValueError(f"{', '.join(missing)} required when maintenance is required")
        return self


class InspectionResponse(BaseModel):
    id: str
    vehicle_id: str
    inspection_type: Literal["risk_assessment", "commissioning"] = "risk_assessment"
    assessment_id: str | None = None
    feature_hash: str
    status: str
    is_active: bool = True
    priority: str
    inspection_areas: list[str] = Field(default_factory=list)
    notes: str | None = None
    checklist: list[InspectionChecklistItem] = Field(default_factory=list)
    summary: str | None = None
    draft_checklist: list[InspectionChecklistItem] = Field(default_factory=list)
    draft_summary: str | None = None
    draft_saved_by: str | None = None
    draft_saved_at: datetime | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    assigned_at: datetime | None = None
    started_by: str | None = None
    started_at: datetime | None = None
    completed_by: str | None = None
    completed_at: datetime | None = None
    decision: str | None = None
    decision_notes: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    work_order_id: str | None = None
    cancellation_reason: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, INSPECTION_STATUSES, "Inspection status")


class InspectionListResponse(BaseModel):
    items: list[InspectionResponse]
    page: int
    limit: int
    total: int
    pages: int
