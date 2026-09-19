from fastapi import APIRouter, HTTPException

from app.disease import predictor
from app.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    try:
        return predictor.predict(req.symptoms)
    except predictor.ModelUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
