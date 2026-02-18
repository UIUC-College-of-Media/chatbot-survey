from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Persuasive AI Study API",
    description="API for collecting and storing survey responses for the Persuasive AI study",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #TODO: In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "persuasive_ai_study")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
survey1_collection = db["survey1_responses"]


class AttitudeItem(BaseModel):
    """Individual attitude item response"""
    item_id: str = Field(..., description="Identifier for the attitude item")
    response: int = Field(..., ge=1, le=7, description="Response value (1-7 scale)")


class Demographics(BaseModel):
    """Demographics information"""
    age: Optional[int] = Field(None, ge=18, description="Participant age")
    gender: Optional[str] = Field(None, description="Gender identity")
    education: Optional[str] = Field(None, description="Education level")
    ethnicity: Optional[str] = Field(None, description="Ethnicity")
    country: Optional[str] = Field(None, description="Country of residence")
    other: Optional[Dict[str, Any]] = Field(None, description="Additional demographic fields")


class Survey1Request(BaseModel):
    """Survey 1 (Baseline) response model"""
    participant_id: str = Field(..., description="Unique participant identifier from Qualtrics")
    prolific_id: Optional[str] = Field(None, description="Prolific participant ID")
    qualtrics_response_id: Optional[str] = Field(None, description="Qualtrics response ID")
    
    topic_condition: str = Field(..., description="Topic condition: 'teams', 'plastic_ban', or 'pe_mandatory'")
    
    attitudes: List[AttitudeItem] = Field(..., min_items=8, max_items=8, description="8 attitude items")
    
    belief_argument: Optional[str] = Field(None, description="Belief argument response")
    
    topic_importance: Optional[int] = Field(None, ge=1, le=7, description="Topic importance rating (1-7)")
    
    attitude_strength: Optional[int] = Field(None, ge=1, le=7, description="Attitude strength rating (1-7)")
    
    demographics: Optional[Demographics] = Field(None, description="Demographics information")
    
    survey_completion_time: Optional[datetime] = Field(None, description="Survey completion timestamp")
    ip_address: Optional[str] = Field(None, description="IP address of participant")
    user_agent: Optional[str] = Field(None, description="User agent string")


class Survey1Response(BaseModel):
    """Response model for Survey 1 submission"""
    success: bool
    message: str
    participant_id: str
    survey_id: str
    timestamp: datetime


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Persuasive AI Study API",
        "version": "1.0.0",
        "endpoints": {
            "survey1": "/api/v1/survey1",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@app.post("/api/v1/survey1", response_model=Survey1Response, status_code=status.HTTP_201_CREATED)
async def submit_survey1(survey_data: Survey1Request):
    """
    Submit Survey 1 responses
    
    This endpoint receives responses from Qualtrics survey and stores them in MongoDB.
    """
    try:
        document = {
            "participant_id": survey_data.participant_id,
            "prolific_id": survey_data.prolific_id,
            "qualtrics_response_id": survey_data.qualtrics_response_id,
            "topic_condition": survey_data.topic_condition,
            "attitudes": [{"item_id": item.item_id, "response": item.response} for item in survey_data.attitudes],
            "belief_argument": survey_data.belief_argument,
            "topic_importance": survey_data.topic_importance,
            "attitude_strength": survey_data.attitude_strength,
            "demographics": survey_data.demographics.dict() if survey_data.demographics else None,
            "survey_completion_time": survey_data.survey_completion_time or datetime.utcnow(),
            "ip_address": survey_data.ip_address,
            "user_agent": survey_data.user_agent,
            "created_at": datetime.utcnow(),
            "survey_type": "survey1_baseline",
            "week": 0
        }
        
        result = await survey1_collection.insert_one(document)
        
        return Survey1Response(
            success=True,
            message="Survey 1 response stored successfully",
            participant_id=survey_data.participant_id,
            survey_id=str(result.inserted_id),
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store survey response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

