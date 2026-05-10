# Serverless Deployment Guide

Your FastAPI backend is now configured for serverless deployment. Here are options and instructions.

## ✅ Serverless-Ready Features

- ✅ Connection pooling for MongoDB (reuses connections across invocations)
- ✅ Stateless application design
- ✅ No file system dependencies
- ✅ Environment variable configuration

## Deployment Options

### Option 1: AWS Lambda (Recommended for MongoDB Atlas)

**Pros:**
- Works well with MongoDB Atlas
- Pay per request
- Auto-scaling
- Good for low to medium traffic

**Setup:**

1. Install Mangum adapter:
```bash
pip install mangum
```

2. Create `lambda_handler.py`:
```python
from mangum import Mangum
from api.main import app

handler = Mangum(app)
```

3. Deploy using:
- **Serverless Framework**: `serverless deploy`
- **AWS SAM**: `sam build && sam deploy`
- **Terraform**: Configure Lambda function
- **Zappa**: `zappa deploy production`

**Requirements:**
- `requirements.txt` (already have it)
- `handler.py` pointing to Mangum handler
- Environment variables in Lambda configuration

### Option 2: Vercel

**Pros:**
- Easy deployment from Git
- Free tier available
- Automatic HTTPS
- Good for small to medium projects

**Setup:**

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Create `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/main.py"
    }
  ],
  "env": {
    "MONGODB_URL": "@mongodb_url",
    "DATABASE_NAME": "@database_name"
  }
}
```

3. Deploy:
```bash
vercel
```

**Note:** Vercel has a 10-second timeout limit. For longer operations, consider AWS Lambda.

### Option 3: Google Cloud Functions

**Setup:**

1. Create `main.py` wrapper:
```python
from api.main import app
import functions_framework

@functions_framework.http
def handler(request):
    return app(request.environ, request.start_response)
```

2. Deploy:
```bash
gcloud functions deploy survey-api \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars MONGODB_URL=your_url,DATABASE_NAME=your_db
```

### Option 4: Azure Functions

**Setup:**

1. Install Azure Functions Core Tools
2. Create `function_app.py`:
```python
import azure.functions as func
from api.main import app

def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        app(req.environ, lambda status, headers: None),
        mimetype="application/json"
    )
```

## Environment Variables

Set these in your serverless platform:

- `MONGODB_URL`: Your MongoDB connection string
- `DATABASE_NAME`: Database name (default: `persuasive_ai_study`)

## MongoDB Connection Notes

- **MongoDB Atlas**: Recommended for serverless (cloud-hosted)
- **Connection Pooling**: Already configured (reuses connections)
- **Cold Starts**: First request may be slower (~1-2 seconds)
- **Warm Instances**: Subsequent requests are fast

## Testing Serverless Locally

### AWS Lambda (SAM)
```bash
sam local start-api
```

### Vercel
```bash
vercel dev
```

## Cost Considerations

- **AWS Lambda**: ~$0.20 per 1M requests (free tier: 1M/month)
- **Vercel**: Free tier available, then $20/month
- **MongoDB Atlas**: Free tier (512MB), then pay-as-you-go

## Performance Tips

1. **Keep functions warm**: Use scheduled pings for high-traffic periods
2. **Connection reuse**: Already implemented
3. **Cold start mitigation**: Use provisioned concurrency (AWS) or keep-alive (Vercel)
4. **Database**: Use MongoDB Atlas in same region as your serverless function

## Monitoring

- **AWS**: CloudWatch logs
- **Vercel**: Built-in analytics
- **Google Cloud**: Cloud Functions logs
- **Azure**: Application Insights

## Recommended Setup

For your use case (survey data collection):

1. **Platform**: AWS Lambda or Vercel
2. **Database**: MongoDB Atlas (same region)
3. **Monitoring**: Set up alerts for errors
4. **Backup**: MongoDB Atlas automatic backups

## Next Steps

1. Choose your platform
2. Set up MongoDB Atlas (if not already)
3. Configure environment variables
4. Deploy and test
5. Update Qualtrics API URL to point to your serverless endpoint

