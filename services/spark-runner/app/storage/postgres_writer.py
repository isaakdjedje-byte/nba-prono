"""
Module d'ecriture PostgreSQL pour les entites run et match
Utilise SQLAlchemy pour abstraction ORM
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

logger = logging.getLogger(__name__)

Base = declarative_base()


class RunEntity(Base):
    """Table runs - statut d'ingestion"""
    __tablename__ = "runs"
    
    id = Column(String, primary_key=True)
    status = Column(String, nullable=False)  # pending, collecting, success, error
    trace_id = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    matches_count = Column(Integer, default=0)
    error_cause = Column(String, nullable=True)
    error_details = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class MatchEntity(Base):
    """Table matches - donnees collectees"""
    __tablename__ = "matches"

    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    external_id = Column(String, nullable=False, index=True)
    home_team = Column(JSON, nullable=False)
    away_team = Column(JSON, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    season = Column(String, nullable=False)
    game_type = Column(String, default="regular")
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_data = Column(JSON, nullable=True)


class SignalEntity(Base):
    """Table signals - predictions generees (Story 1.4)"""
    __tablename__ = "signals"

    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    match_id = Column(String, nullable=False, index=True)
    home_team = Column(JSON, nullable=False)
    away_team = Column(JSON, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)

    # Signal winner
    winner_prediction = Column(String, nullable=False)  # home, away
    winner_confidence = Column(String, nullable=False)  # 0.0 - 1.0

    # Score projete
    score_total = Column(String, nullable=False)
    score_home = Column(String, nullable=False)
    score_away = Column(String, nullable=False)

    # Over/Under
    ou_signal = Column(String, nullable=False)  # over, under, no_signal
    ou_line = Column(String, nullable=False)
    ou_confidence = Column(String, nullable=False)
    ou_edge = Column(String, nullable=True)

    # Metadata
    quality_score = Column(String, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    signal_data = Column(JSON, nullable=True)  # Donnees completes JSON


class PostgresWriter:
    """
    Writer PostgreSQL pour persistance runs et matches
    Incremental - pas de schema massif upfront
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/nba_prono"
        )
        self.engine = None
        self.Session = None
        
    def connect(self):
        """Initialise la connexion PostgreSQL"""
        try:
            self.engine = create_engine(self.connection_string)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("PostgreSQL connection initialisee")
        except Exception as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise
    
    def create_tables(self):
        """Cree les tables incrementalement"""
        if not self.engine:
            self.connect()
        
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Tables runs/matches creees/verifiees")
        except Exception as e:
            logger.error(f"Erreur creation tables: {e}")
            raise
    
    def save_run(self, run_data: Dict[str, Any]) -> str:
        """
        Sauvegarde un run d'ingestion
        
        Args:
            run_data: Donnees du run
            
        Returns:
            str: ID du run sauvegarde
        """
        if not self.Session:
            self.connect()
        
        session = self.Session()
        try:
            run = RunEntity(
                id=run_data.get("run_id"),
                status=run_data.get("status"),
                trace_id=run_data.get("trace_id"),
                started_at=run_data.get("started_at", datetime.now(timezone.utc)),
                completed_at=run_data.get("completed_at"),
                matches_count=run_data.get("matches_count", 0),
                error_cause=run_data.get("error_cause"),
                error_details=run_data.get("error_details"),
                metadata_json=run_data.get("metadata")
            )
            
            session.merge(run)  # Merge pour upsert
            session.commit()
            
            logger.info(f"Run sauvegarde: {run.id}")
            return run.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur sauvegarde run: {e}")
            raise
        finally:
            session.close()
    
    def save_matches(self, run_id: str, matches: List[Dict[str, Any]]) -> int:
        """
        Sauvegarde les matches d'un run
        
        Args:
            run_id: ID du run
            matches: Liste des matches
            
        Returns:
            int: Nombre de matches sauvegardes
        """
        if not self.Session:
            self.connect()
        
        session = self.Session()
        saved_count = 0
        
        try:
            for match_data in matches:
                match = MatchEntity(
                    id=f"{run_id}_{match_data.get('external_id')}",
                    run_id=run_id,
                    external_id=match_data.get("external_id"),
                    home_team=match_data.get("home_team"),
                    away_team=match_data.get("away_team"),
                    scheduled_at=datetime.fromisoformat(
                        match_data.get("scheduled_at").replace('Z', '+00:00')
                    ),
                    season=match_data.get("season"),
                    game_type=match_data.get("game_type", "regular"),
                    raw_data=match_data
                )
                
                session.merge(match)
                saved_count += 1
            
            session.commit()
            logger.info(f"{saved_count} matches sauvegardes pour run {run_id}")
            return saved_count

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur sauvegarde matches: {e}")
            raise
        finally:
            session.close()

    def save_signals(self, run_id: str, signals: List[Dict[str, Any]]) -> int:
        """
        Sauvegarde les signaux de prediction pour un run (Story 1.4)
        ATOMICITE: Tous les signaux sont persistes ou aucun (transaction complete)

        Args:
            run_id: ID du run
            signals: Liste des signaux a sauvegarder

        Returns:
            int: Nombre de signaux sauvegardes
        """
        if not self.Session:
            self.connect()

        session = self.Session()

        try:
            # Transaction atomique: tout ou rien
            with session.begin():
                signal_entities = []
                for signal_data in signals:
                    signal = SignalEntity(
                        id=f"{run_id}_{signal_data.get('match_id')}",
                        run_id=run_id,
                        match_id=signal_data.get("match_id"),
                        home_team=signal_data.get("home_team", {}),
                        away_team=signal_data.get("away_team", {}),
                        scheduled_at=datetime.fromisoformat(
                            signal_data.get("scheduled_at", datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')
                        ),
                        winner_prediction=signal_data.get("winner", {}).get("prediction", ""),
                        winner_confidence=str(signal_data.get("winner", {}).get("confidence", 0)),
                        score_total=str(signal_data.get("score_projection", {}).get("total", 0)),
                        score_home=str(signal_data.get("score_projection", {}).get("home", 0)),
                        score_away=str(signal_data.get("score_projection", {}).get("away", 0)),
                        ou_signal=signal_data.get("over_under", {}).get("signal", "no_signal"),
                        ou_line=str(signal_data.get("over_under", {}).get("line", 220.5)),
                        ou_confidence=str(signal_data.get("over_under", {}).get("confidence", 0)),
                        ou_edge=str(signal_data.get("over_under", {}).get("edge", 0)),
                        quality_score=str(signal_data.get("quality_score", 0)),
                        signal_data=signal_data
                    )
                    signal_entities.append(signal)

                # Bulk merge pour atomicite
                for signal in signal_entities:
                    session.merge(signal)

            saved_count = len(signal_entities)
            logger.info(f"{saved_count} signaux sauvegardes pour run {run_id} (atomic)")
            return saved_count

        except Exception as e:
            logger.error(f"Erreur sauvegarde signaux (rollback automatique): {e}")
            raise
        finally:
            session.close()

    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupere le statut d'un run
        
        Args:
            run_id: ID du run
            
        Returns:
            Dict ou None si non trouve
        """
        if not self.Session:
            self.connect()
        
        session = self.Session()
        try:
            run = session.query(RunEntity).filter(RunEntity.id == run_id).first()
            
            if not run:
                return None
            
            return {
                "run_id": run.id,
                "status": run.status,
                "trace_id": run.trace_id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "matches_count": run.matches_count,
                "error_cause": run.error_cause,
                "error_details": run.error_details
            }
            
        finally:
            session.close()


if __name__ == "__main__":
    # Test manuel
    writer = PostgresWriter()
    writer.create_tables()
    print("Tables creees avec succes")
