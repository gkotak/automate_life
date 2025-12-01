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
    MEDIA_BUCKET_NAME = "uploaded-media"  # For user-uploaded video/audio files
    ARTICLE_MEDIA_BUCKET_NAME = os.getenv("ARTICLE_MEDIA_BUCKET", "article-media")  # For persisted downloaded media

    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize storage manager with Supabase client

        Args:
            bucket_name: Optional bucket name to use (defaults to BUCKET_NAME for video frames)
        """
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = bucket_name or self.BUCKET_NAME

    def ensure_bucket_exists(self, allowed_mime_types: Optional[list] = None, file_size_limit: Optional[int] = None) -> bool:
        """
        Ensure the bucket exists, create if not

        Args:
            allowed_mime_types: Optional list of allowed MIME types for the bucket
            file_size_limit: Optional file size limit in bytes

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

                # Default options based on bucket type
                if self.bucket_name == self.MEDIA_BUCKET_NAME:
                    # Uploaded media: videos, audio files, and documents
                    # Note: file_size_limit uses Supabase tier defaults (Pro: 5GB, Free: 50MB)
                    options = {
                        "public": True,
                        "allowed_mime_types": allowed_mime_types or [
                            "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm",
                            "audio/mpeg", "audio/wav", "audio/mp4", "audio/aac", "audio/ogg", "audio/flac",
                            "application/pdf"
                        ]
                    }
                    # Only add file_size_limit if explicitly provided (Supabase rejects default values)
                    if file_size_limit:
                        options["file_size_limit"] = file_size_limit
                else:
                    # Video frames: images only (up to 10MB)
                    options = {
                        "public": True,
                        "file_size_limit": file_size_limit or 10485760,  # 10MB default
                        "allowed_mime_types": allowed_mime_types or ["image/jpeg", "image/png", "image/webp"]
                    }

                # Create bucket with public access
                self.supabase.storage.create_bucket(
                    id=self.bucket_name,
                    name=self.bucket_name,
                    options=options
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

    def upload_media_file(
        self,
        file_path: str,
        user_id: str,
        original_filename: str,
        content_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a user-uploaded media file (video/audio/document) to Supabase storage

        This method handles uploads through the backend for secure authentication.
        Supports video, audio, and PDF files.
        File size limits are based on Supabase tier:
        - Pro tier: Up to 5GB per file
        - Free tier: Up to 50MB per file

        Args:
            file_path: Path to the media file
            user_id: ID of the user uploading the file
            original_filename: Original filename (for extension)
            content_type: MIME type of the file

        Returns:
            Tuple of (success, storage_path, public_url)
        """
        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists():
                return False, None, None

            # Generate storage path: user_{user_id}/{timestamp}_{filename}
            import time
            timestamp = int(time.time())
            file_ext = Path(original_filename).suffix
            safe_filename = f"{timestamp}_{Path(original_filename).stem}{file_ext}"
            storage_path = f"user_{user_id}/{safe_filename}"

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Upload to Supabase storage
            logger.info(f"📤 Uploading media file to storage: {storage_path}")

            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)

            logger.info(f"✅ Media file uploaded successfully: {public_url}")

            return True, storage_path, public_url

        except Exception as e:
            logger.error(f"❌ Failed to upload media file: {e}", exc_info=True)
            return False, None, None

    def get_public_url(self, storage_path: str) -> Optional[str]:
        """
        Get the public URL for a file in storage

        Args:
            storage_path: Path to the file in storage

        Returns:
            Public URL or None if failed
        """
        try:
            return self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
        except Exception as e:
            logger.error(f"❌ Failed to get public URL: {e}")
            return None

    # ===========================================
    # Article Media Persistence Methods (Phase 2)
    # ===========================================

    def upload_article_media(
        self,
        file_path: str,
        article_id: int,
        article_type: str,
        content_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload downloaded media to persistent storage for later reprocessing.

        This stores media (video/audio) downloaded during article processing
        so it can be used later for video frame re-extraction or transcript
        regeneration without re-downloading.

        Args:
            file_path: Local path to the downloaded media file
            article_id: ID of the article this media belongs to
            article_type: 'public' or 'private'
            content_type: MIME type of the file (e.g., 'video/mp4')

        Returns:
            Tuple of (success, storage_path)
        """
        try:
            # Use the article media bucket
            bucket_name = self.ARTICLE_MEDIA_BUCKET_NAME

            # Ensure bucket exists with appropriate settings
            original_bucket = self.bucket_name
            self.bucket_name = bucket_name
            if not self.ensure_bucket_exists(
                allowed_mime_types=[
                    "video/mp4", "video/webm", "video/quicktime", "video/x-matroska",
                    "audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/flac"
                ]
            ):
                self.bucket_name = original_bucket
                return False, None
            self.bucket_name = original_bucket

            # Generate storage path: {article_type}/{article_id}/media.{ext}
            file_ext = Path(file_path).suffix or '.mp4'
            storage_path = f"{article_type}/{article_id}/media{file_ext}"

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Upload to Supabase storage
            logger.info(f"📤 Uploading article media to storage: {bucket_name}/{storage_path}")

            self.supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            logger.info(f"✅ Article media uploaded successfully: {storage_path}")

            return True, storage_path

        except Exception as e:
            logger.error(f"❌ Failed to upload article media: {e}", exc_info=True)
            return False, None

    def download_article_media(
        self,
        storage_path: str,
        destination_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Download media from storage to a local file.

        Used when reprocessing an article to extract new video frames
        or regenerate transcripts from previously stored media.

        Args:
            storage_path: Path within the storage bucket
            destination_path: Local path to save the downloaded file
            bucket_name: Optional bucket name (defaults to article-media)

        Returns:
            True if download was successful
        """
        try:
            bucket = bucket_name or self.ARTICLE_MEDIA_BUCKET_NAME

            logger.info(f"📥 Downloading article media from storage: {bucket}/{storage_path}")

            # Download file content
            response = self.supabase.storage.from_(bucket).download(storage_path)

            # Write to destination
            with open(destination_path, 'wb') as f:
                f.write(response)

            logger.info(f"✅ Article media downloaded successfully to: {destination_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to download article media: {e}", exc_info=True)
            return False

    def delete_article_media(
        self,
        storage_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Delete media from storage.

        Used by the cleanup script to remove expired media.

        Args:
            storage_path: Path within the storage bucket
            bucket_name: Optional bucket name (defaults to article-media)

        Returns:
            True if deletion was successful
        """
        try:
            bucket = bucket_name or self.ARTICLE_MEDIA_BUCKET_NAME

            logger.info(f"🗑️ Deleting article media from storage: {bucket}/{storage_path}")

            self.supabase.storage.from_(bucket).remove([storage_path])

            logger.info(f"✅ Article media deleted successfully: {storage_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete article media: {e}", exc_info=True)
            return False

    def get_article_media_signed_url(
        self,
        storage_path: str,
        expiry_seconds: int = 3600,
        bucket_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a signed URL for accessing stored media.

        Since the article-media bucket is private, this generates
        a time-limited signed URL for access.

        Args:
            storage_path: Path within the storage bucket
            expiry_seconds: How long the URL should be valid (default 1 hour)
            bucket_name: Optional bucket name (defaults to article-media)

        Returns:
            Signed URL or None if failed
        """
        try:
            bucket = bucket_name or self.ARTICLE_MEDIA_BUCKET_NAME

            result = self.supabase.storage.from_(bucket).create_signed_url(
                storage_path,
                expiry_seconds
            )

            if result and 'signedURL' in result:
                return result['signedURL']

            logger.warning(f"⚠️ Could not get signed URL for: {storage_path}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get signed URL: {e}", exc_info=True)
            return None
