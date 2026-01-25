
from app.workers.celery_app import celery
import random, time
from app.api.v1.quality import JOB_STATUS

@celery.task
def run_quality_job(job_id: str, asset_id: str):
    JOB_STATUS[job_id] = "RUNNING"
    time.sleep(5)  # simulate profiling
    JOB_STATUS[job_id] = {
        "asset_id": asset_id,
        "completeness": random.randint(80,100),
        "uniqueness": random.randint(70,100),
        "score": random.randint(80,95)
    }
