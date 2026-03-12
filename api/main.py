from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from api.schema import Survey1Request, Survey1Response, Survey3Request, Survey3Response

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
_survey3_collection = None

def get_database():
    """Get database connection, reusing existing connection for serverless"""
    global _client, _db, _survey1_collection, _survey3_collection
    
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URL,
            maxPoolSize=10,  
            minPoolSize=1,   
            serverSelectionTimeoutMS=5000  
        )
        _db = _client[DATABASE_NAME]
        _survey1_collection = _db["survey1_responses"]
        _survey3_collection = _db["survey3_responses"]
    
    return _client, _db, _survey1_collection


def get_survey3_collection():
    """Get Survey 3 collection, ensuring database is initialized"""
    global _survey3_collection

    if _survey3_collection is None:
        # This will initialize the client, db, and collections if needed
        get_database()

    return _survey3_collection


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Persuasive AI Study API",
        "version": "1.0.0",
        "endpoints": {
            "survey1": "/api/v1/survey1",
            "survey3": "/api/v1/survey3",
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
            "pre_block": {
                "block_id": survey_data.pre_block_id,
                "topic": survey_data.pre_topic,
                "personalization": survey_data.pre_personalization,
                "is_control": survey_data.pre_is_control,
                "responses": [
                    {"item_id": item.item_id, "response": item.response}
                    for item in (survey_data.pre_block_responses or [])
                ],
            }
            if survey_data.pre_block_id is not None
            else None,
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


@app.post("/api/v1/survey3", response_model=Survey3Response, status_code=status.HTTP_201_CREATED)
async def submit_survey3(survey_data: Survey3Request):
    """
    Submit Survey 3 responses

    This endpoint receives responses from the follow-up survey (Survey 3) and stores
    them in MongoDB. Survey 3 consists of 8 compulsory Likert questions with
    6 response options (completely disagree to completely agree).
    """
    try:
        client, db, _ = get_database()
        survey3_collection = get_survey3_collection()

        document = {
            "participant_id": survey_data.participant_id,
            "prolific_id": survey_data.prolific_id,
            "prolific_id_text_entry": survey_data.prolific_id_text_entry,
            "qualtrics_response_id": survey_data.qualtrics_response_id,
            "topic_condition": survey_data.topic_condition,
            "topic_items": [
                {"question_id": item.question_id, "response": item.response}
                for item in survey_data.topic_items
            ],
            "chatbot_items": [
                {"question_id": item.question_id, "response": item.response}
                for item in survey_data.chatbot_items
            ],
            "survey_completion_time": survey_data.survey_completion_time
            or datetime.utcnow(),
            "ip_address": survey_data.ip_address,
            "user_agent": survey_data.user_agent,
            "study_comment_or_withdrawal": survey_data.study_comment_or_withdrawal,
            "created_at": datetime.utcnow(),
            "survey_type": "survey3_followup",
            "week": 2,
        }

        result = await survey3_collection.insert_one(document)

        return Survey3Response(
            success=True,
            message="Survey 3 response stored successfully",
            participant_id=survey_data.participant_id,
            survey_id=str(result.inserted_id),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store survey 3 response: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
