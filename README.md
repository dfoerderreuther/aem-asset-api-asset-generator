# AEM Test Image Uploader

Purpose of the tool is to generate thousands of test assets in AEM Cloud Service.

## Example

![Example of image upload process](README_example.png)

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
AEM_ENABLED=true  # Enable/disable AEM upload functionality
AEM_HOST=https://author-p1111-e2222.adobeaemcloud.com  # AEM Cloud Service instance URL
AEM_DESTINATION=/content/dam/gen  # Target folder in AEM for uploaded assets
AEM_PUT_INTO_DATE_FOLDER=true  # Organize uploads into date-based subfolders

# Customer Structure Replication
REPLICATE_CUSTOMER_STRUCTURE=true  # Enable/disable customer folder structure replication
REPLICATE_CUSTOMER_STRUCTURE_FILE=data/customer_structure.csv  # CSV file defining folder structure and asset counts
```

The `customer_structure.csv` file should contain two columns:
- First column: AEM folder path to create
- Second column: Number of random assets to generate in that folder

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


## Run: 

```
pip install -r requirements.txt
python image_processor.py  
```

## Adobe documentation

### Asset upload: 

https://experienceleague.adobe.com/en/docs/experience-manager-cloud-service/content/assets/admin/developer-reference-material-apis#initiate-upload



## Attribution

Images in this project are generated using Adobe Firefly and are subject to Adobe's terms of service.