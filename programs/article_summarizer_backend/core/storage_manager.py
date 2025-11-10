"""
Supabase Storage Manager

Handles uploading and managing files in Supabase storage buckets.
"""

import os
import logging
from typing import Optional, Tuple
from pathlib import Path
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class StorageManager:
    """Manage Supabase storage uploads"""

    BUCKET_NAME = "video-frames"

    def __init__(self):
        """Initialize storage manager with Supabase client"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = self.BUCKET_NAME

    def ensure_bucket_exists(self) -> bool:
        """
        Ensure the video-frames bucket exists, create if not

        Returns:
            True if bucket exists or was created successfully
        """
        try:
            # List all buckets
            buckets = self.supabase.storage.list_buckets()

            # Check if our bucket exists
            bucket_exists = any(bucket.name == self.bucket_name for bucket in buckets)

            if not bucket_exists:
                logger.info(f"📦 Creating Supabase storage bucket: {self.bucket_name}")
                # Create bucket with public access
                self.supabase.storage.create_bucket(
                    id=self.bucket_name,
                    name=self.bucket_name,
                    options={
                        "public": True,  # Make frames publicly accessible
                        "file_size_limit": 10485760,  # 10MB max per file
                        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"]
                    }
                )
                logger.info(f"✅ Created bucket: {self.bucket_name}")
            else:
                logger.info(f"✅ Bucket already exists: {self.bucket_name}")

            return True

        except Exception as e:
            logger.error(f"❌ Error ensuring bucket exists: {e}", exc_info=True)
            return False

    def upload_frame(
        self,
        file_path: str,
        article_id: int,
        timestamp_seconds: float
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a video frame to Supabase storage

        Args:
            file_path: Path to the frame image file
            article_id: ID of the article this frame belongs to
            timestamp_seconds: Timestamp of the frame in the video

        Returns:
            Tuple of (success, storage_path, public_url)
        """
        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists():
                return False, None, None

            # Generate storage path: article_{id}/frame_{timestamp}.jpg
            file_ext = Path(file_path).suffix or '.jpg'
            storage_path = f"article_{article_id}/frame_{int(timestamp_seconds)}{file_ext}"

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Upload to Supabase storage
            logger.info(f"📤 Uploading frame to storage: {storage_path}")

            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)

            logger.info(f"✅ Frame uploaded successfully: {public_url}")

            return True, storage_path, public_url

        except Exception as e:
            logger.error(f"❌ Failed to upload frame: {e}", exc_info=True)
            return False, None, None

    def delete_article_frames(self, article_id: int) -> bool:
        """
        Delete all frames for an article

        Args:
            article_id: ID of the article

        Returns:
            True if deletion was successful
        """
        try:
            folder_path = f"article_{article_id}"

            # List all files in the folder
            files = self.supabase.storage.from_(self.bucket_name).list(folder_path)

            if not files:
                logger.info(f"No frames found for article {article_id}")
                return True

            # Delete all files
            file_paths = [f"{folder_path}/{file['name']}" for file in files]
            self.supabase.storage.from_(self.bucket_name).remove(file_paths)

            logger.info(f"🗑️ Deleted {len(file_paths)} frames for article {article_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete frames: {e}", exc_info=True)
            return False

    def get_frame_url(self, storage_path: str) -> Optional[str]:
        """
        Get public URL for a frame

        Args:
            storage_path: Storage path of the frame

        Returns:
            Public URL or None if failed
        """
        try:
            return self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
        except Exception as e:
            logger.error(f"❌ Failed to get frame URL: {e}")
            return None
