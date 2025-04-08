import os
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path
import randomname
from PIL import Image, ImageDraw, ImageFont
import piexif
from typing import List, Tuple, Optional
import queue
import logging
import argparse
from dotenv import load_dotenv
from aem_uploader import AEMUploader
from customer_structure import CustomerStructureReplicator

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'image_processing.log')),
        logging.StreamHandler()
    ]
)

class ImageProcessor:
    def __init__(self, num_threads: int = None):
        self.num_threads = num_threads or int(os.getenv('NUM_THREADS', '4'))
        self.task_queue = queue.Queue()
        self.threads = []
        self.img_dir = Path(os.getenv('INPUT_DIR', 'img'))
        self.out_dir = Path(os.getenv('OUTPUT_DIR', 'out'))
        self.out_dir.mkdir(exist_ok=True)
        self.processed_count = 0
        self.processed_lock = threading.Lock()
        
        # Hardcoded configuration
        self.start_date = datetime.strptime('2010-01-01', '%Y-%m-%d')
        self.min_tags = 5
        self.max_tags = 10
        self.font_size = 36
        self.font_name = 'Arial.ttf'
        self.text_color = (255, 255, 255)
        self.text_position = (10, 10)
        self.num_generations = int(os.getenv('NUM_GENERATIONS', '1000'))
        
        # Initialize AEM uploader and customer structure replicator
        self.aem_uploader = AEMUploader()
        self.customer_replicator = CustomerStructureReplicator(self.aem_uploader)

    def get_random_date(self) -> datetime:
        """Generate a random date between start_date and today."""
        end_date = datetime.now()
        time_between = end_date - self.start_date
        days_between = time_between.days
        random_days = random.randint(0, days_between)
        return self.start_date + timedelta(days=random_days)

    def get_random_tags(self, image_path: Path) -> List[str]:
        """Extract tags from the file name and add random tags, ignoring numbers, 'firefly', and short words."""
        tags = ["findme"]  # Always include the "findme" tag
        
        # Get filename-based tags
        try:
            filename = image_path.stem.lower()  # Get filename without extension
            
            # Split filename into words and filter according to requirements
            words = filename.split(' ')
            for word in words:
                # Skip if word is too short, contains numbers, or is 'firefly'
                if (len(word) < 3 or 
                    any(c.isdigit() for c in word) or 
                    word == 'firefly'):
                    continue
                tags.append(word)
        except Exception as e:
            logging.warning(f"Error processing filename for tags: {str(e)}")
            pass  # Continue with just random tags if there's an error

        # Add random tags to reach the minimum required
        while len(tags) < self.min_tags:
            try:
                # Generate a random name for tag
                tag = randomname.get_name()
                if tag:
                    # Remove any hyphens and capitalize first letter
                    tag = tag.replace('-', ' ').title()
                    # Split the tag into separate words and add each as a tag
                    split_tags = tag.split()
                    tags.extend(split_tags)
            except Exception as e:
                logging.warning(f"Error generating random tag: {str(e)}")
                # Fallback to simple tag if randomname fails
                tags.append(f"Tag_{len(tags) + 1}")

        # Ensure we don't exceed max_tags
        if len(tags) > self.max_tags:
            tags = tags[:self.max_tags]

        return tags

    def normalize_filename(self, name: str) -> str:
        """Normalize a filename to ASCII characters."""
        # Remove any non-ASCII characters and replace spaces with underscores
        normalized = ''.join(c for c in name if ord(c) < 128)
        normalized = normalized.replace(' ', '_')
        # Remove any non-alphanumeric characters except underscores
        normalized = ''.join(c for c in normalized if c.isalnum() or c == '_')
        return normalized.lower()

    def process_image(self, image_path: Path, target_folder: Optional[str] = None) -> None:
        """Process a single image with all required modifications."""
        try:
            # Generate random name and date
            random_name = self.normalize_filename(randomname.get_name())
            random_date = self.get_random_date()
            tags = self.get_random_tags(image_path)

            # Open and process image
            with Image.open(str(image_path)) as img:
                # Create a copy of the image for drawing
                img_copy = img.copy()
                draw = ImageDraw.Draw(img_copy)

                # Try to load a font, fallback to default if not available
                try:
                    font = ImageFont.truetype(self.font_name, self.font_size)
                except:
                    font = ImageFont.load_default()

                # Draw text on image
                text = f"{random_name}\n{random_date.strftime('%Y-%m-%d')}\n{', '.join(tags)}"
                draw.text(self.text_position, text, font=font, fill=self.text_color)

                # Save the modified image
                output_path = self.out_dir / f"{random_name}.jpg"
                img_copy.save(str(output_path), "JPEG")

                # Update EXIF data
                exif_dict = piexif.load(str(output_path))
                if exif_dict is None:
                    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

                # Update date in EXIF
                date_str = random_date.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str.encode('ascii')
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str.encode('ascii')

                # Update tags in EXIF - use UTF-16LE encoding for XPKeywords
                tags_str = ", ".join(tags)
                exif_dict["0th"][piexif.ImageIFD.XPKeywords] = tags_str.encode('utf-16le')

                # Add title and description
                title = random_name.replace('_', ' ').title()
                # Use ASCII encoding for better compatibility
                exif_dict["0th"][piexif.ImageIFD.DocumentName] = title.encode('ascii')
                exif_dict["0th"][piexif.ImageIFD.XPTitle] = title.encode('utf-16le')
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = tags_str.encode('ascii')

                # Save EXIF data
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, str(output_path))

                # Upload to AEM if enabled
                if self.aem_uploader.aem_enabled:
                    if target_folder:
                        # Override the destination path for customer structure replication
                        self.aem_uploader.aem_destination = target_folder
                    self.aem_uploader.upload(output_path, random_date, tags)

                # Update processed count and log
                with self.processed_lock:
                    self.processed_count += 1
                    logging.info(f"Processed {self.processed_count}: {output_path.name}")
                    logging.debug(f"  Date: {random_date.strftime('%Y-%m-%d')}")
                    logging.debug(f"  Tags: {', '.join(tags)}")

        except Exception as e:
            logging.error(f"Error processing {image_path}: {str(e)}")

    def worker(self) -> None:
        """Worker function for thread processing."""
        while True:
            try:
                image_path = self.task_queue.get_nowait()
                self.process_image(image_path)
            except queue.Empty:
                break

    def process_directory(self) -> None:
        """Process specified number of images using multiple threads."""
        # Get all jpg and jpeg files
        source_images = list(self.img_dir.glob("*.jpg")) + list(self.img_dir.glob("*.jpeg"))
        
        if not source_images:
            logging.error("No images found in the input directory!")
            return

        logging.info(f"Found {len(source_images)} source images")
        logging.info(f"Will generate {self.num_generations} new images")
        
        # Randomly select images to process
        selected_images = random.choices(source_images, k=self.num_generations)
        
        # Add selected images to the queue
        for image_path in selected_images:
            self.task_queue.put(image_path)

        # Create and start threads
        for _ in range(min(self.num_threads, self.num_generations)):
            thread = threading.Thread(target=self.worker)
            thread.start()
            self.threads.append(thread)

        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()

        logging.info(f"Processing complete! Generated {self.processed_count} images")

def main():
    parser = argparse.ArgumentParser(description='Process images with random metadata and overlays')
    parser.add_argument('--threads', type=int, help='Number of threads to use (overrides NUM_THREADS from .env)')
    args = parser.parse_args()

    logging.info(f"Starting image processing with {args.threads or os.getenv('NUM_THREADS', '4')} threads")
    processor = ImageProcessor(args.threads)
    
    # Check if customer structure replication is enabled
    if processor.customer_replicator.enabled:
        logging.info("Customer structure replication is enabled - will only process customer structure")
        processor.customer_replicator.replicate_structure(processor)
    else:
        # Only process regular batch if customer structure replication is disabled
        if processor.num_generations > 0:
            logging.info("Processing regular batch of random assets")
            processor.process_directory()
        else:
            logging.warning("No generations specified and customer structure replication is disabled - nothing to do")

if __name__ == "__main__":
    main() 