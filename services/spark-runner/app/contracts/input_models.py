"""
Modeles de validation des donnees entrantes
Validation stricte des payloads avant persistance
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class TeamInput(BaseModel):
    """Modele validation equipe NBA"""
    id: str = Field(..., min_length=1, max_length=10, description="Identifiant unique equipe")
    name: str = Field(..., min_length=1, max_length=100, description="Nom de l'equipe")
    city: str = Field(..., min_length=1, max_length=100, description="Ville de l'equipe")
    
    @field_validator('id')
    @classmethod
    def validate_team_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Team ID cannot be empty")
        return v.strip().lower()


class MatchInput(BaseModel):
    """Modele validation match NBA entrant"""
    external_id: str = Field(..., min_length=1, description="ID externe du match (NBA API)")
    home_team: TeamInput = Field(..., description="Equipe a domicile")
    away_team: TeamInput = Field(..., description="Equipe visiteuse")
    scheduled_at: str = Field(..., description="Date/heure programmee (ISO 8601)")
    season: str = Field(..., pattern=r'^\d{4}-\d{2}$', description="Saison (format: YYYY-YY)")
    game_type: str = Field(default="regular", pattern=r'^(regular|playoff|preseason)$')
    
    @field_validator('external_id')
    @classmethod
    def validate_external_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("External ID cannot be empty")
        return v.strip()
    
    @field_validator('scheduled_at')
    @classmethod
    def validate_scheduled_at(cls, v: str) -> str:
        """Valide le format ISO 8601"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}. Expected ISO 8601 format.")


class IngestionRequest(BaseModel):
    """Requete d'ingestion avec metadata"""
    run_id: str = Field(..., description="Identifiant unique du run")
    trace_id: str = Field(..., description="ID de tracabilite pour correlation logs")
    source_url: Optional[str] = Field(default=None, description="URL source optionnelle")
    requested_at: datetime = Field(default_factory=datetime.utcnow)
