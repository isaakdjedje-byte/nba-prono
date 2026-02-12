"""
Modeles de sortie du pipeline d'ingestion
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class IngestionStatus(str, Enum):
    """Statuts possibles d'ingestion"""
    PENDING = "pending"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    STORING = "storing"
    SUCCESS = "success"
    SOURCE_ERROR = "source_error"
    VALIDATION_ERROR = "validation_error"
    STORAGE_ERROR = "storage_error"


class IngestionResult(BaseModel):
    """Resultat d'une execution d'ingestion"""
    status: str = Field(..., pattern=r'^(success|error|partial)$')
    trace_id: str = Field(..., description="ID de tracabilite")
    run_id: str = Field(..., description="Identifiant du run")
    matches_count: int = Field(default=0, ge=0)
    matches: List[Dict[str, Any]] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    error_cause: Optional[str] = Field(default=None, description="Cause explicite en cas d'erreur")
    error_details: Optional[str] = Field(default=None, description="Details techniques de l'erreur")
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convertit en dict JSON-serializable"""
        data = self.model_dump()
        data['collected_at'] = self.collected_at.isoformat()
        return data


class RunStatusOutput(BaseModel):
    """Statut d'un run d'ingestion"""
    run_id: str
    status: IngestionStatus
    trace_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    matches_collected: int = 0
    error_cause: Optional[str] = None
