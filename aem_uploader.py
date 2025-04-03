import os
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from get_token import get_aem_token
import urllib.parse

class AEMUploader:
    def __init__(self):
        self.aem_enabled = os.getenv('AEM_ENABLED', 'false').lower() == 'true'
        if self.aem_enabled:
            self.aem_host = os.getenv('AEM_HOST', 'http://localhost:4502')
            self.aem_token = get_aem_token()  # Get token from get_token.py
            self.aem_destination = os.getenv('AEM_DESTINATION', '/content/dam/images')
            
            # Configure logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger('AEMUploader')
            self.logger.setLevel(logging.ERROR)

    def _log_curl_command(self, method: str, url: str, headers: Dict[str, str], data: Dict[str, str] = None) -> None:
        """Log the equivalent curl command for debugging."""
        curl_cmd = ['curl', '-X', method]
        
        # Add headers
        for key, value in headers.items():
            curl_cmd.extend(['-H', f'"{key}: {value}"'])
        
        # Add data if present
        if data:
            data_str = ' '.join([f'-d "{k}={urllib.parse.quote(str(v))}"' for k, v in data.items()])
            curl_cmd.append(data_str)
        
        # Add URL
        curl_cmd.append(f'"{url}"')
        
        self.logger.info("Curl command for testing:")
        self.logger.info(' '.join(curl_cmd))

    def upload(self, image_path: Path, date: datetime, tags: List[str]) -> bool:
        """Upload an image to AEM using the Assets API."""
        if not self.aem_enabled:
            self.logger.info("AEM upload is disabled")
            return True

        try:
            # Step 1: Initiate upload
            self.logger.info(f"Step 1: Initiating upload for {image_path.name}")
            upload_info = self._initiate_upload(image_path)
            if not upload_info:
                return False

            # Step 2: Upload binary to signed URL
            self.logger.info(f"Step 2: Uploading binary for {image_path.name}")
            if not self._upload_binary(image_path, upload_info):
                return False

            # Step 3: Complete upload
            self.logger.info(f"Step 3: Completing upload for {image_path.name}")
            return self._complete_upload(image_path, upload_info, date, tags)

        except Exception as e:
            self.logger.error(f"Failed to upload {image_path} to AEM: {str(e)}")
            return False

    def _initiate_upload(self, image_path: Path) -> Dict[str, Any]:
        """Step 1: Initiate the upload process."""
        try:
            headers = {
                'Authorization': f'Bearer {self.aem_token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'fileName': image_path.name,
                'fileSize': image_path.stat().st_size
            }
            
            url = f'{self.aem_host}{self.aem_destination}.initiateUpload.json'
            self.logger.info(f"Initiating upload to {url}")
            
            # Log the curl command
            #self._log_curl_command('POST', url, headers, data)
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                self.logger.info("Upload initiation successful")
                return response.json()
            else:
                self.logger.error(f"Failed to initiate upload: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error during upload initiation: {str(e)}")
            return None

    def _upload_binary(self, image_path: Path, upload_info: Dict[str, Any]) -> bool:
        """Step 2: Upload the binary to the signed URL."""
        try:
            upload_uris = upload_info['files'][0]['uploadURIs']
            self.logger.info(f"Uploading to {len(upload_uris)} URIs")
            
            with open(image_path, 'rb') as f:
                file_data = f.read()
                
            for uri in upload_uris:
                self.logger.info(f"Uploading to URI: {uri}")
                response = requests.put(uri, data=file_data)
                if response.status_code not in [200, 201, 204]:
                    self.logger.error(f"Failed to upload binary: {response.text}")
                    return False
                    
            self.logger.info("Binary upload completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during binary upload: {str(e)}")
            return False

    def _complete_upload(self, image_path: Path, upload_info: Dict[str, Any], 
                        date: datetime, tags: List[str]) -> bool:
        """Step 3: Complete the upload process."""
        try:
            headers = {
                'Authorization': f'Bearer {self.aem_token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'uploadToken': upload_info['files'][0]['uploadToken'],
                'fileName': image_path.name,
                'mimeType': 'image/jpeg',
                'jcr:title': image_path.stem,
                'jcr:description': f'Uploaded on {date.strftime("%Y-%m-%d")}',
                'jcr:tags': ",".join(tags)
            }
            
            self.logger.info("Completing upload process")
            response = requests.post(
                f'{self.aem_host}{upload_info["completeURI"]}',
                headers=headers,
                data=data
            )
            
            if response.status_code in [200, 201]:
                self.logger.info("Upload completed successfully")
                return True
            else:
                self.logger.error(f"Failed to complete upload: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during upload completion: {str(e)}")
            return False 