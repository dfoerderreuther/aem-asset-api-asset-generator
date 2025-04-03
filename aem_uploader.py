import os
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from get_token import get_aem_token
import urllib.parse
import time

class AEMUploader:
    def __init__(self):
        self.aem_enabled = os.getenv('AEM_ENABLED', 'false').lower() == 'true'
        if self.aem_enabled:
            self.aem_host = os.getenv('AEM_HOST', 'http://localhost:4502')
            self.aem_token = get_aem_token()  # Get token from get_token.py
            self.aem_destination = os.getenv('AEM_DESTINATION', '/content/dam/images')
            self.put_into_date_folder = os.getenv('AEM_PUT_INTO_DATE_FOLDER', 'false').lower() == 'true'
            
            # Configure logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger('AEMUploader')
            self.logger.setLevel(logging.ERROR)

    def _get_destination_path(self, date: datetime) -> str:
        """Get the destination path based on date if AEM_PUT_INTO_DATE_FOLDER is true."""
        if self.put_into_date_folder:
            year = date.strftime('%Y')
            month = date.strftime('%m')
            return f"{self.aem_destination}/{year}/{month}"
        return self.aem_destination

    def _create_folder(self, folder_path: str, max_retries: int = 3, retry_delay: int = 2) -> bool:
        """Create a folder in AEM if it doesn't exist, with retry mechanism."""
        for attempt in range(max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.aem_token}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Check if folder exists
                check_url = f'{self.aem_host}{folder_path}.json'
                response = requests.get(check_url, headers=headers)
                
                if response.status_code == 200:
                    self.logger.info(f"Folder {folder_path} exists")
                    return True
                
                # Create folder
                create_url = f'{self.aem_host}{folder_path}'
                data = {
                    'class': 'sling:Folder',
                    'jcr:primaryType': 'sling:Folder'
                }
                
                self.logger.info(f"Creating folder {folder_path} (attempt {attempt + 1}/{max_retries})")
                response = requests.post(create_url, headers=headers, data=data)
                
                if response.status_code in [200, 201]:
                    # Wait a bit to ensure folder is properly created
                    time.sleep(retry_delay)
                    self.logger.info(f"Successfully created folder {folder_path}")
                    return True
                else:
                    self.logger.warning(f"Failed to create folder {folder_path} (attempt {attempt + 1}/{max_retries}): {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error creating folder {folder_path}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False

    def _ensure_folders_exist(self, destination_path: str) -> bool:
        """Ensure all folders in the path exist, creating them if necessary."""
        if not self.put_into_date_folder:
            return True
            
        # Split the path into components
        path_parts = destination_path.split('/')
        current_path = ''
        
        # Start from the root and create each folder in the path
        for part in path_parts:
            if not part:
                continue
            current_path += f'/{part}'
            if not self._create_folder(current_path):
                return False
                
        return True

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
            # Get the appropriate destination path based on date
            destination_path = self._get_destination_path(date)
            
            # Ensure all folders in the path exist
            if not self._ensure_folders_exist(destination_path):
                self.logger.error(f"Failed to create required folders for {destination_path}")
                return False
            
            # Step 1: Initiate upload
            self.logger.info(f"Step 1: Initiating upload for {image_path.name} to {destination_path}")
            upload_info = self._initiate_upload(image_path, destination_path)
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

    def _initiate_upload(self, image_path: Path, destination_path: str, max_retries: int = 3, retry_delay: int = 2) -> Dict[str, Any]:
        """Step 1: Initiate the upload process with retry mechanism."""
        for attempt in range(max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.aem_token}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                data = {
                    'fileName': image_path.name,
                    'fileSize': image_path.stat().st_size
                }
                
                url = f'{self.aem_host}{destination_path}.initiateUpload.json'
                self.logger.info(f"Initiating upload to {url} (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(url, headers=headers, data=data)
                
                if response.status_code == 200:
                    self.logger.info("Upload initiation successful")
                    return response.json()
                else:
                    self.logger.warning(f"Failed to initiate upload (attempt {attempt + 1}/{max_retries}): {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error during upload initiation: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
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