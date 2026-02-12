"""
FastAPI entrypoint pour le service spark-runner
Expose health check et trigger ingestion
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional

from pipelines.ingest_pipeline import IngestPipeline
from pipelines.scoring_pipeline import ScoringPipeline
from contracts.output_models import IngestionResult

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    logger.info("Spark-runner demarrage...")
    yield
    logger.info("Spark-runner arret...")


app = FastAPI(
    title="Spark-Runner NBA",
    description="Service d'ingestion des matchs NBA",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "spark-runner",
        "version": "0.1.0"
    }


@app.post("/ingest/trigger", response_model=IngestionResult)
async def trigger_ingestion(background_tasks: BackgroundTasks, trace_id: Optional[str] = None):
    """
    Declenche une ingestion des matchs du jour
    
    Args:
        trace_id: ID de tracabilite (genere si non fourni)
        
    Returns:
        IngestionResult avec statut et metadonnees
    """
    import uuid
    trace_id = trace_id or str(uuid.uuid4())
    
    logger.info(f"[{trace_id}] Trigger ingestion recu")
    
    try:
        # Execution synchrone pour l'instant (peut etre async plus tard)
        pipeline = IngestPipeline(trace_id=trace_id)
        result = pipeline.run()
        
        if result.status == "error":
            logger.error(f"[{trace_id}] Ingestion echouee: {result.error_cause}")
            return JSONResponse(
                status_code=500,
                content=result.model_dump_json_safe()
            )
        
        logger.info(f"[{trace_id}] Ingestion reussie: {result.matches_count} matchs")
        return result
        
    except Exception as e:
        logger.error(f"[{trace_id}] Exception ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ingest/status/{run_id}")
async def get_ingestion_status(run_id: str):
    """
    Recupere le statut d'un run d'ingestion

    Args:
        run_id: Identifiant du run

    Returns:
        Statut du run
    """
    # Pour l'instant, statut simplifie (a enrichir avec persistance)
    return {
        "run_id": run_id,
        "status": "unknown",
        "message": "Statut persistant a implementer avec PostgreSQL"
    }


@app.post("/score")
async def score_matches_endpoint(request: dict):
    """
    Endpoint de scoring predictif (Story 1.4)

    Args:
        request: {
            run_id: str,
            trace_id: str,
            matches: List[MatchData]
        }

    Returns:
        Resultat du scoring avec signaux et exclusions
    """
    import uuid

    run_id = request.get("run_id", str(uuid.uuid4()))
    trace_id = request.get("trace_id", str(uuid.uuid4()))
    matches = request.get("matches", [])

    logger.info(f"[{trace_id}] Scoring request received for run {run_id} with {len(matches)} matches")

    try:
        pipeline = ScoringPipeline()
        result = pipeline.score_matches(
            run_id=run_id,
            trace_id=trace_id,
            matches=matches
        )

        if result["status"] == "failed":
            logger.error(f"[{trace_id}] Scoring failed: {result.get('error_cause')}")
            return JSONResponse(
                status_code=500,
                content=result
            )

        logger.info(f"[{trace_id}] Scoring completed: {len(result['signals'])} signals generated")
        return result

    except Exception as e:
        logger.error(f"[{trace_id}] Exception scoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
