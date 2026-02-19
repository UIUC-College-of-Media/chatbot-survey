from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
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

_client = None
_db = None
_survey1_collection = None

def get_database():
    """Get database connection, reusing existing connection for serverless"""
    global _client, _db, _survey1_collection
    
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URL,
            maxPoolSize=10,  
            minPoolSize=1,   
            serverSelectionTimeoutMS=5000  
        )
        _db = _client[DATABASE_NAME]
        _survey1_collection = _db["survey1_responses"]
    
    return _client, _db, _survey1_collection


class AttitudeItem(BaseModel):
    """Individual attitude item response"""
    item_id: str = Field(..., description="Identifier for the attitude item")
    response: int = Field(..., ge=1, le=7, description="Response value (1-7 scale)")


class OpinionStatementItem(BaseModel):
    """Individual opinion statement response (6-point Likert scale)"""
    statement_id: str = Field(..., description="Identifier for the opinion statement")
    response: int = Field(..., ge=1, le=6, description="Response value (1-6 scale: completely disagree to completely agree)")


class Demographics(BaseModel):
    """Demographics information"""
    age: Optional[int] = Field(None, ge=18, description="Participant age (input field)")
    gender: Optional[str] = Field(None, description="Gender identity (5 options: 4 predefined + 1 self-describe option)")
    gender_self_describe: Optional[str] = Field(None, description="Self-described gender (if 'self-describe' option was selected)")
    education: Optional[str] = Field(None, description="Highest level of education (6 options)")
    kids_in_school: Optional[str] = Field(None, description="Do you have kids in school? (3 options)")
    political_belief: Optional[str] = Field(None, description="Political belief (6 options)")


class Survey1Request(BaseModel):
    """Survey 1 (Baseline) response model"""
    participant_id: str = Field(..., description="Unique participant identifier from Qualtrics")
    prolific_id: Optional[str] = Field(None, description="Prolific participant ID")
    qualtrics_response_id: Optional[str] = Field(None, description="Qualtrics response ID")
    
    topic_condition: str = Field(..., description="Topic condition: 'teams', 'plastic_ban', or 'pe_mandatory'")
    
    # Opinion question (first question - 6 choices: completely agree to completely disagree)
    opinion_question: Optional[int] = Field(None, ge=1, le=6, description="Opinion response (1-6 scale: completely agree to completely disagree)")
    opinion_reason: Optional[str] = Field(None, description="Reason/explanation for the opinion response")
    
    # Opinion statements (7 statements with 6-point Likert scale each)
    opinion_statements: List[OpinionStatementItem] = Field(..., min_items=7, max_items=7, description="7 opinion statements about the topic")
    
    # Feeling and importance questions (6-point scale each)
    feeling_strength: Optional[int] = Field(None, ge=1, le=6, description="How strongly do you feel about the topic? (1=Not at all, 6=Very strongly)")
    topic_importance_feeling: Optional[int] = Field(None, ge=1, le=6, description="How important is the topic to you? (1=Not at all, 6=Very important)")
    
    # Topic usage question (topic-dependent, e.g., "How do you use MS Teams?")
    topic_usage: Optional[List[str]] = Field(None, description="How do you use the topic? (multiple choice, 6 options total with 1 self-describe option)")
    topic_usage_self_describe: Optional[str] = Field(None, description="Self-described topic usage (if 'self-describe' option was selected)")
    
    # Topic behavior question (topic-dependent, e.g., "How often do you drink water in plastic bottles?")
    topic_behavior: Optional[str] = Field(None, description="Topic-specific behavior question (3 options, e.g., frequency of plastic bottle usage)")
    
    attitudes: List[AttitudeItem] = Field(..., min_items=8, max_items=8, description="8 attitude items")
    
    demographics: Optional[Demographics] = Field(None, description="Demographics information")
    
    # End of survey optional comment
    survey_comment: Optional[str] = Field(None, description="Optional comment at the end of the survey")
    
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
        client, db, survey1_collection = get_database()
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
        client, db, survey1_collection = get_database()
        
        document = {
            "participant_id": survey_data.participant_id,
            "prolific_id": survey_data.prolific_id,
            "qualtrics_response_id": survey_data.qualtrics_response_id,
            "topic_condition": survey_data.topic_condition,
            "opinion_question": survey_data.opinion_question,
            "opinion_reason": survey_data.opinion_reason,
            "opinion_statements": [{"statement_id": item.statement_id, "response": item.response} for item in survey_data.opinion_statements],
            "feeling_strength": survey_data.feeling_strength,
            "topic_importance_feeling": survey_data.topic_importance_feeling,
            "topic_usage": survey_data.topic_usage,
            "topic_usage_self_describe": survey_data.topic_usage_self_describe,
            "topic_behavior": survey_data.topic_behavior,
            "attitudes": [{"item_id": item.item_id, "response": item.response} for item in survey_data.attitudes],
            "demographics": survey_data.demographics.dict() if survey_data.demographics else None,
            "survey_comment": survey_data.survey_comment,
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

