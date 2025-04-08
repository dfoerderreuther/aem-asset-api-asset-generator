import os
import csv
from pathlib import Path
from typing import List, Dict
import logging
from aem_uploader import AEMUploader
import random
import queue
import threading

class CustomerStructureReplicator:
    def __init__(self, aem_uploader: AEMUploader):
        self.aem_uploader = aem_uploader
        self.enabled = os.getenv('REPLICATE_CUSTOMER_STRUCTURE', 'false').lower() == 'true'
        self.structure_file = Path(os.getenv('REPLICATE_CUSTOMER_STRUCTURE_FILE', 'data/customer_structure.csv'))
        self.logger = logging.getLogger('CustomerStructureReplicator')
        self.logger.setLevel(logging.INFO)
        self.task_queue = queue.Queue()
        self.processed_count = 0
        self.processed_lock = threading.Lock()
        self.threads = []
        self.created_folders = set()  # Track created folders

    def read_structure_file(self) -> List[Dict[str, str]]:
        """Read the customer structure CSV file and return its contents."""
        if not self.structure_file.exists():
            self.logger.error(f"Customer structure file not found: {self.structure_file}")
            return []

        try:
            with open(self.structure_file, 'r') as f:
                reader = csv.DictReader(f, delimiter=';', fieldnames=['folder', 'asset_count'])
                # Skip header row
                next(reader)
                return list(reader)
        except Exception as e:
            self.logger.error(f"Error reading customer structure file: {str(e)}")
            return []

    def create_folder_structure(self, folder_path: str) -> bool:
        """Create the folder structure in AEM."""
        try:
            # Ensure the folder path starts with /content/dam
            if not folder_path.startswith('/content/dam'):
                folder_path = f'/content/dam{folder_path}'

            # Create each folder in the path, skipping /content and /content/dam
            path_parts = folder_path.split('/')
            current_path = '/content/dam'  # Start from /content/dam since it exists
            
            # Skip the first two parts (/content and /dam) since they exist
            for part in path_parts[3:]:
                if not part:
                    continue
                current_path += f'/{part}'
                
                # Skip if folder already exists
                if current_path in self.created_folders:
                    continue
                    
                self.logger.info(f"-> Creating folder: {current_path}")
                if not self.aem_uploader._create_folder(current_path):
                    self.logger.error(f"Failed to create folder: {current_path}")
                    return False
                    
                self.created_folders.add(current_path)
            
            return True
        except Exception as e:
            self.logger.error(f"Error creating folder structure: {str(e)}")
            return False

    def worker(self, image_processor) -> None:
        """Worker function for thread processing."""
        while True:
            try:
                task = self.task_queue.get_nowait()
                folder_path, asset_count, source_image = task
                image_processor.process_image(source_image, target_folder=folder_path)
                
                with self.processed_lock:
                    self.processed_count += 1
                    self.logger.info(f"Processed {self.processed_count} assets")
            except queue.Empty:
                break

    def replicate_structure(self, image_processor) -> None:
        """Replicate the customer structure and generate assets."""
        if not self.enabled:
            self.logger.info("Customer structure replication is disabled")
            return

        structure = self.read_structure_file()
        if not structure:
            self.logger.error("No customer structure data found")
            return

        self.logger.info(f"Starting customer structure replication for {len(structure)} folders")
        
        # Store original setting and temporarily disable date-based folders
        original_date_folder_setting = self.aem_uploader.put_into_date_folder
        self.aem_uploader.put_into_date_folder = False
        
        try:
            # First create all folder structures
            for entry in structure:
                folder_path = entry['folder'].strip()
                try:
                    asset_count = int(entry['asset_count'].strip())
                except ValueError:
                    self.logger.error(f"Invalid asset count for folder {folder_path}: {entry['asset_count']}")
                    continue

                # Skip folders with 0 assets
                if asset_count == 0:
                    continue

                self.logger.info(f"Creating folder structure for {folder_path}")
                if not self.create_folder_structure(folder_path):
                    self.logger.error(f"Failed to create folder structure for {folder_path}")
                    continue

            # Get all source images once
            source_images = list(image_processor.img_dir.glob("*.jpg")) + list(image_processor.img_dir.glob("*.jpeg"))
            if not source_images:
                self.logger.error("No source images found for processing")
                return

            # Queue all tasks
            total_assets = 0
            for entry in structure:
                folder_path = entry['folder'].strip()
                try:
                    asset_count = int(entry['asset_count'].strip())
                except ValueError:
                    continue

                if asset_count == 0:
                    continue

                for _ in range(asset_count):
                    source_image = random.choice(source_images)
                    self.task_queue.put((folder_path, asset_count, source_image))
                    total_assets += 1

            # Create and start threads
            num_threads = min(int(os.getenv('NUM_THREADS', '4')), total_assets)
            self.logger.info(f"Starting {num_threads} threads to process {total_assets} assets")
            
            for _ in range(num_threads):
                thread = threading.Thread(target=self.worker, args=(image_processor,))
                thread.start()
                self.threads.append(thread)

            # Wait for all threads to complete
            for thread in self.threads:
                thread.join()

        finally:
            # Restore original setting
            self.aem_uploader.put_into_date_folder = original_date_folder_setting

        self.logger.info(f"Customer structure replication completed. Processed {self.processed_count} assets") 