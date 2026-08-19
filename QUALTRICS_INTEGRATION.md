# Qualtrics Integration Guide

This guide explains how to configure Qualtrics to send Survey 1 responses to the FastAPI backend.

## Overview

You'll need to:
1. Set up embedded data fields in Qualtrics
2. Add JavaScript to format and send data to the API
3. Configure the API endpoint URL
4. Test the integration

## Step 1: Set Up Embedded Data Fields

In your Qualtrics survey, you'll need to store some metadata as embedded data:

1. Go to **Survey Flow** in your Qualtrics survey
2. Add an **Embedded Data** element at the beginning
3. Add these fields:
   - `participant_id` - Will be set to `${e://Field/ResponseID}`
   - `topic_condition` - Your random assignment variable (teams, plastic_ban, or pe_mandatory)
   - `prolific_id` - If you're using Prolific, capture this from URL parameters

## Step 2: Add JavaScript to Send Data to API

Add this JavaScript code to the **last question** of Survey 1 (or in a separate block after all Survey 1 questions).

### Option A: Add to End of Survey Block

1. Go to the last question in Survey 1
2. Click **Add JavaScript** (or go to Question Options → JavaScript)
3. Paste the following code:

```javascript
Qualtrics.SurveyEngine.addOnReady(function() {
    // Get all the data we need
    var participantId = "${e://Field/ResponseID}";
    var prolificId = "${e://Field/prolific_id}" || "${url:PROLIFIC_PID}" || null;
    var qualtricsResponseId = "${e://Field/ResponseID}";
    var topicCondition = "${e://Field/topic_condition}";
    
    // Get attitude responses (adjust question IDs to match your survey)
    // Replace QID1, QID2, etc. with your actual question IDs
    var attitudes = [];
    var attitudeQuestions = ['QID1', 'QID2', 'QID3', 'QID4', 'QID5', 'QID6', 'QID7', 'QID8'];
    
    attitudeQuestions.forEach(function(qid, index) {
        var response = parseInt(this.getQuestionChoiceValue(qid));
        if (response && response >= 1 && response <= 7) {
            attitudes.push({
                item_id: "att" + (index + 1),
                response: response
            });
        }
    }.bind(this));
    
    // Get other responses (adjust question IDs)
    var beliefArgument = this.getQuestionChoiceValue('QID9') || null; // Text entry question
    var topicImportance = parseInt(this.getQuestionChoiceValue('QID10')) || null;
    var attitudeStrength = parseInt(this.getQuestionChoiceValue('QID11')) || null;
    
    // Get demographics (adjust question IDs)
    var demographics = {
        age: parseInt(this.getQuestionChoiceValue('QID12')) || null,
        gender: this.getQuestionChoiceValue('QID13') || null,
        education: this.getQuestionChoiceValue('QID14') || null,
        ethnicity: this.getQuestionChoiceValue('QID15') || null,
        country: this.getQuestionChoiceValue('QID16') || null
    };
    
    // Prepare the payload
    var payload = {
        participant_id: participantId,
        prolific_id: prolificId,
        qualtrics_response_id: qualtricsResponseId,
        topic_condition: topicCondition,
        attitudes: attitudes,
        belief_argument: beliefArgument,
        topic_importance: topicImportance,
        attitude_strength: attitudeStrength,
        demographics: demographics,
        survey_completion_time: new Date().toISOString()
    };
    
    // Send to API
    var apiUrl = 'http://your-server-url/api/v1/survey1'; // REPLACE WITH YOUR SERVER URL
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Survey data sent successfully:', data);
        // Optionally store confirmation in embedded data
        Qualtrics.SurveyEngine.setEmbeddedData('api_response', JSON.stringify(data));
    })
    .catch(error => {
        console.error('Error sending survey data:', error);
        // Store error for debugging
        Qualtrics.SurveyEngine.setEmbeddedData('api_error', error.toString());
    });
});
```

### Option B: Using Qualtrics Web Service (Recommended for Production)

For a more robust solution, use Qualtrics' built-in Web Service action:

1. Go to **Survey Flow**
2. Add a **Web Service** element after Survey 1 questions
3. Configure:
   - **URL**: `http://your-server-url/api/v1/survey1`
   - **Method**: POST
   - **Content Type**: application/json
   - **Body**: Use the JSON format below

#### Web Service Body Configuration

In the Web Service body, use Qualtrics piped text to map fields:

```json
{
  "participant_id": "${e://Field/ResponseID}",
  "prolific_id": "${e://Field/prolific_id}",
  "qualtrics_response_id": "${e://Field/ResponseID}",
  "topic_condition": "${e://Field/topic_condition}",
  "attitudes": [
    {"item_id": "att1", "response": ${q://QID1/ChoiceNumericValue}},
    {"item_id": "att2", "response": ${q://QID2/ChoiceNumericValue}},
    {"item_id": "att3", "response": ${q://QID3/ChoiceNumericValue}},
    {"item_id": "att4", "response": ${q://QID4/ChoiceNumericValue}},
    {"item_id": "att5", "response": ${q://QID5/ChoiceNumericValue}},
    {"item_id": "att6", "response": ${q://QID6/ChoiceNumericValue}},
    {"item_id": "att7", "response": ${q://QID7/ChoiceNumericValue}},
    {"item_id": "att8", "response": ${q://QID8/ChoiceNumericValue}}
  ],
  "belief_argument": "${q://QID9/ChoiceTextEntryValue}",
  "topic_importance": ${q://QID10/ChoiceNumericValue},
  "attitude_strength": ${q://QID11/ChoiceNumericValue},
  "demographics": {
    "age": ${q://QID12/ChoiceNumericValue},
    "gender": "${q://QID13/ChoiceTextEntryValue}",
    "education": "${q://QID14/ChoiceTextEntryValue}",
    "ethnicity": "${q://QID15/ChoiceTextEntryValue}",
    "country": "${q://QID16/ChoiceTextEntryValue}"
  }
}
```

**Note**: Replace `QID1`, `QID2`, etc. with your actual Qualtrics question IDs.

## Step 3: Finding Your Question IDs

1. In Qualtrics, go to your survey
2. Click on a question
3. Look at the URL - it will contain something like `QID=123`
4. Or go to **Tools** → **Export Question IDs** to get a list

## Step 4: Mapping Question Types

### Multiple Choice (Single Answer) - for numeric scales
- Use: `${q://QID1/ChoiceNumericValue}` or `${q://QID1/ChoiceTextEntryValue}`

### Text Entry
- Use: `${q://QID1/ChoiceTextEntryValue}`

### Matrix Questions
- For matrix rows: `${q://QID1/ChoiceNumericValue}` (for each row)

## Step 5: Setting Up Topic Condition Random Assignment

In Survey Flow, before Survey 1:

1. Add a **Randomizer** element
2. Add 3 branches:
   - Branch 1: Set embedded data `topic_condition` = `"teams"`
   - Branch 2: Set embedded data `topic_condition` = `"plastic_ban"`
   - Branch 3: Set embedded data `topic_condition` = `"pe_mandatory"`

## Step 6: Testing

### Test Mode

1. Use Qualtrics **Preview** mode
2. Complete Survey 1
3. Check browser console (F12) for any errors
4. Verify data in MongoDB:
   ```bash
   # Connect to MongoDB and check
   db.survey1_responses.find().pretty()
   ```

### Test with Sample Data

You can test the API directly using curl or Postman:

```bash
curl -X POST "http://localhost:8000/api/v1/survey1" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "TEST_QUALTRICS_123",
    "topic_condition": "teams",
    "attitudes": [
      {"item_id": "att1", "response": 5},
      {"item_id": "att2", "response": 4},
      {"item_id": "att3", "response": 6},
      {"item_id": "att4", "response": 3},
      {"item_id": "att5", "response": 5},
      {"item_id": "att6", "response": 4},
      {"item_id": "att7", "response": 5},
      {"item_id": "att8", "response": 6}
    ],
    "topic_importance": 6,
    "attitude_strength": 5
  }'
```

## Step 7: Production Deployment

### Update API URL

Replace `http://your-server-url` with your actual server URL:
- Local testing: `http://localhost:8000`
- Production: `https://your-domain.com` or your deployed server URL

### Security Considerations

1. **CORS**: The API currently allows all origins (`allow_origins=["*"]`). For production, update `api/main.py` to only allow Qualtrics domains:
   ```python
   allow_origins=[
       "https://yourbrand.qualtrics.com",
       "https://*.qualtrics.com"  # If using multiple Qualtrics accounts
   ]
   ```

2. **HTTPS**: Always use HTTPS in production

3. **API Authentication** (Optional): Consider adding API keys if needed

## Troubleshooting

### Common Issues

1. **CORS Errors**: 
   - Ensure CORS is enabled in the FastAPI app
   - Check that the API URL is correct

2. **Data Not Sending**:
   - Check browser console for JavaScript errors
   - Verify question IDs match your survey
   - Check that all required fields are present

3. **404 Errors**:
   - Verify the API endpoint URL is correct
   - Ensure the FastAPI server is running

4. **Validation Errors**:
   - Check that attitude responses are integers between 1-7
   - Ensure exactly 8 attitude items are sent
   - Verify topic_condition is one of: "teams", "plastic_ban", "pe_mandatory"

### Debugging Tips

1. Add console.log statements in JavaScript to see what data is being sent
2. Check the Network tab in browser DevTools to see the actual request
3. Check FastAPI logs for incoming requests
4. Use Qualtrics' embedded data to store API responses for debugging

## Example: Complete Survey Flow Setup

```
Survey Flow:
├── Embedded Data (Set participant_id, topic_condition)
├── Randomizer (Topic condition assignment)
│   ├── Branch 1: Set topic_condition = "teams"
│   ├── Branch 2: Set topic_condition = "plastic_ban"
│   └── Branch 3: Set topic_condition = "pe_mandatory"
├── Block: Survey 1 Questions
│   ├── Question 1-8: Attitude items
│   ├── Question 9: Belief argument (text)
│   ├── Question 10: Topic importance
│   ├── Question 11: Attitude strength
│   └── Question 12-16: Demographics
└── Web Service (POST to /api/v1/survey1)
    └── Or JavaScript in last question
```

## Need Help?

- Check FastAPI docs: `http://localhost:8000/docs` (Swagger UI)
- Check API health: `http://localhost:8000/health`
- Review Qualtrics documentation on Web Services and JavaScript

