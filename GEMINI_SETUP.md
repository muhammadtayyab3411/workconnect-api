# Gemini API Document Verification Setup

## Overview
WorkConnect uses Google's Gemini API for automated document verification. This allows for instant verification of:
- National ID cards
- Address proof documents
- Professional licenses

## Prerequisites

### 1. Install Required Dependencies
```bash
# Navigate to the Django backend directory
cd workconnect-api

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. **Visit Google AI Studio:**
   - Go to https://aistudio.google.com/
   - Sign in with your Google account

2. **Create API Key:**
   - Click on "Get API key" 
   - Create a new API key for your project
   - Copy the generated API key (starts with `AIza...`)

3. **Important:** Keep your API key secure and never commit it to version control!

## Configuration

### Add API Key to Django Settings

**Option 1: Environment Variable (Recommended)**
```bash
# Add to your .env file or export in terminal
export GEMINI_API_KEY=your_api_key_here
```

**Option 2: Django Settings File**
Add this to your `workconnect-api/workconnect/settings.py`:
```python
# Gemini API Configuration
GEMINI_API_KEY = 'your_api_key_here'  # Replace with your actual key
```

⚠️ **Security Note:** For production, always use environment variables or secure secret management.

### Example .env File
Create `workconnect-api/.env`:
```
DEBUG=True
SECRET_KEY=your-django-secret-key
GEMINI_API_KEY=your-gemini-api-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

## Usage

### API Endpoints

1. **List Documents:**
   ```
   GET /api/auth/profile/documents/
   ```

2. **Upload Document:**
   ```
   POST /api/auth/profile/documents/upload/
   Content-Type: multipart/form-data
   
   Body:
   - document_type: 'national_id' | 'address_proof' | 'license'
   - document_file: File
   ```

3. **Re-verify Document:**
   ```
   POST /api/auth/profile/documents/{id}/reverify/
   ```

### Supported Document Types

1. **National ID (`national_id`)**
   - Government-issued photo ID
   - Passport, driver's license, national ID card
   - Extracts: Name, ID number, expiry date

2. **Address Proof (`address_proof`)**
   - Utility bills, bank statements
   - Government mail, rental agreements
   - Extracts: Name, address, document date

3. **Professional License (`license`)**
   - Trade licenses, professional certifications
   - Business licenses, permits
   - Extracts: Name, license number, profession, expiry

### File Requirements

- **Max Size:** 5MB per document
- **Formats:** JPG, PNG, GIF, PDF
- **Quality:** Clear, readable text
- **One document per type** per user

## Verification Process

1. **Upload:** User uploads document via frontend
2. **Processing:** File validated and sent to Gemini API
3. **Analysis:** Gemini analyzes document authenticity and extracts data
4. **Scoring:** Confidence score (0-10) and status assignment:
   - **Verified (8.0+):** High confidence, automatically approved
   - **Rejected (≤3.0):** Low confidence or major issues
   - **Manual Review (3.1-7.9):** Requires human review

4. **Response:** User gets instant feedback with verification status

## Testing

### Test Document Upload
```bash
curl -X POST \
  http://localhost:8000/api/auth/profile/documents/upload/ \
  -H "Authorization: Bearer your_jwt_token" \
  -F "document_type=national_id" \
  -F "document_file=@path/to/id_card.jpg"
```

### Expected Response
```json
{
  "message": "Document uploaded and verified successfully",
  "document": {
    "id": "uuid",
    "document_type": "national_id",
    "status": "verified",
    "confidence_score": 8.5,
    "verification_notes": "Document appears authentic with clear text"
  },
  "verification_result": {
    "status": "verified",
    "confidence": 8.5,
    "extracted_data": {
      "full_name": "John Doe",
      "id_number": "123456789"
    },
    "issues": [],
    "reasoning": "Valid government ID with matching name"
  }
}
```

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'google.generativeai'**
   ```bash
   pip install google-generativeai
   ```

2. **ValueError: GEMINI_API_KEY not found in settings**
   - Check your API key is set in settings.py or environment
   - Verify the key format (should start with 'AIza')

3. **API Quota Exceeded**
   - Gemini has generous free limits: 15 requests/minute, 1,500/day
   - For higher usage, consider upgrading to paid tier

4. **Document Verification Fails**
   - Check image quality (clear, good lighting)
   - Ensure document type matches actual document
   - Verify file format is supported

### Fallback Behavior

If Gemini API is unavailable:
- Documents are marked as 'manual_review'
- System continues to work without AI verification
- Admin can manually approve/reject documents

## API Limits (Free Tier)

- **Rate Limit:** 15 requests/minute
- **Daily Limit:** 1,500 requests/day  
- **Monthly Limit:** 1 million tokens
- **File Size:** Up to 20MB per request

Perfect for development and moderate production usage!

## Next Steps

1. Set up your Gemini API key
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Test document upload via frontend
5. Monitor verification accuracy and adjust prompts if needed

For production deployment, consider:
- Using environment variables for API key
- Setting up error monitoring
- Implementing rate limiting
- Adding document retention policies 