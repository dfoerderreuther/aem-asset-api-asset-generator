# AEM Image Uploader

This tool uploads images to Adobe Experience Manager (AEM) Cloud Service using the direct binary upload protocol.

## Configuration Files

### Environment Variables (.env)

The `.env` file contains configuration settings for the image uploader:

```env
# Image Processing Configuration
NUM_THREADS=8
NUM_GENERATIONS=1000
START_DATE=2010-01-01
MIN_TAGS=5
MAX_TAGS=10
FONT_SIZE=36
FONT_NAME=Arial.ttf
TEXT_COLOR=255,255,255
TEXT_POSITION=10,10

# Directory Configuration
INPUT_DIR=img
OUTPUT_DIR=out

# Logging Configuration
LOG_FILE=image_processing.log
LOG_LEVEL=INFO

# AEM Configuration
AEM_ENABLED=true
AEM_HOST=https://author-p90966-e1577661.adobeaemcloud.com
AEM_DESTINATION=/content/dam/gen
```

#### AEM Configuration Details:
- `AEM_ENABLED`: Set to `true` to enable AEM uploads, `false` to disable
- `AEM_HOST`: The AEM Cloud Service author instance URL
- `AEM_DESTINATION`: The DAM folder path where images will be uploaded

### Local Development Token (local_development_token.json)

The `local_development_token.json` file contains the AEM access token for authentication:

```json
{
  "ok": true,
  "statusCode": 200,
  "accessToken": "eyJhbGciOiJSUzI1NiIs..."
}
```

This token is used to authenticate API requests to AEM. The token is automatically obtained and refreshed by the `get_token.py` script.

## Security Notes

1. Never commit the `.env` file or `local_development_token.json` to version control
2. Keep the AEM access token secure and never share it
3. Use environment-specific tokens for different environments (development, staging, production)

## Upload Process

The upload process follows AEM Cloud Service's direct binary upload protocol:

1. **Initiate Upload**: Request signed URLs for upload
2. **Upload Binary**: Upload the file to the signed URLs
3. **Complete Upload**: Finalize the upload with metadata

Each step is logged with detailed information, including curl commands for testing and debugging. 