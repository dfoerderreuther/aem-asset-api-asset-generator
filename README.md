# AEM Image Uploader

This tool uploads images to Adobe Experience Manager (AEM) Cloud Service using the direct binary upload protocol.

## Configuration Files

### Environment Variables (.env)

The `.env` file contains configuration settings for the image uploader:

```env
# Image Processing Configuration
NUM_THREADS=12
NUM_GENERATIONS=3000

# Directory Configuration
INPUT_DIR=img
OUTPUT_DIR=out

# Logging Configuration
LOG_FILE=image_processing.log
LOG_LEVEL=INFO

# AEM Configuration
AEM_ENABLED=true
AEM_HOST=https://author-p1111-e2222.adobeaemcloud.com
AEM_DESTINATION=/content/dam/gen
```


### Local Development Token (local_development_token.json)

The `local_development_token.json` file contains the AEM access token for authentication. Load it from Developer Console -> Integrations -> Local token

```json
{
  "ok": true,
  "statusCode": 200,
  "accessToken": "eyJhbGciOiJSUzI1NiIs..."
}
```

This token is used to authenticate API requests to AEM. The token is automatically obtained and refreshed by the `get_token.py` script.

## Adobe documentation

### Asset upload: 

https://experienceleague.adobe.com/en/docs/experience-manager-cloud-service/content/assets/admin/developer-reference-material-apis#initiate-upload



## Attribution

Images in this project are generated using Adobe Firefly and are subject to Adobe's terms of service.