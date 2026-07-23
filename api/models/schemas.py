"""Pydantic models for request/response validation."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class UserProfileBase(BaseModel):
    """User profile request/response schema."""
    target_roles: List[str] = Field(default=[], description="Target job titles")
    preferred_modality: Optional[str] = Field(default=None, description="remote, hybrid, on-site, or null for any")
    preferred_countries: List[str] = Field(default=[], description="Preferred countries")
    priority_country: Optional[str] = Field(default=None, description="Priority country for job search (must be in preferred_countries)")
    salary_min: Optional[int] = Field(default=None, description="Minimum annual salary USD")
    tech_stack: List[str] = Field(default=[], description="Technical skills")
    cv_base_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    email_provider: Optional[str] = None


class UserProfileResponse(UserProfileBase):
    """User profile with timestamps."""
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    """Job listing schema."""
    title: str
    company: str
    location: str
    modality: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: List[str] = []
    nice_to_have_skills: List[str] = []
    experience_level: str = "unknown"
    description_raw: str


class JobResponse(JobBase):
    """Job with metadata."""
    id: str
    user_id: str
    source: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FitScoreResponse(BaseModel):
    """Job fit score response."""
    id: str
    job_id: str
    score: int
    decision: str
    strengths: List[str]
    gaps: List[str]
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationBase(BaseModel):
    """Application request schema."""
    status: str


class ApplicationResponse(BaseModel):
    """Application response."""
    id: str
    job_id: str
    user_id: str
    status: str
    cv_version_url: Optional[str] = None
    cover_letter_url: Optional[str] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Notification response."""
    id: str
    user_id: str
    job_id: Optional[str] = None
    type: str
    message: str
    is_read: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobSearchRequest(BaseModel):
    """Trigger job discovery request."""
    user_id: str
    roles: Optional[List[str]] = None  # If provided, search these roles instead of profile roles


class ApplicationApprovalRequest(BaseModel):
    """Approve/dismiss application request."""
    approved: bool = Field(..., description="True to approve, False to dismiss")
