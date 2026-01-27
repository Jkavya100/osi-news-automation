"""
OSI News Automation System - Cloudinary Image Uploader
=======================================================
Uploads locally generated images to Cloudinary CDN and returns public URLs.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Initialize Cloudinary
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )
    
    CLOUDINARY_AVAILABLE = True
    logger.info("✅ Cloudinary configured successfully")
    
except ImportError:
    CLOUDINARY_AVAILABLE = False
    logger.warning("⚠️ Cloudinary not installed. Run: pip install cloudinary")


def upload_image_to_cloudinary(
    image_path: str,
    folder: str = "osi-news",
    public_id: str = None
) -> Optional[str]:
    """
    Upload an image to Cloudinary and return the public URL.
    
    Args:
        image_path: Local path to the image file.
        folder: Cloudinary folder to organize images.
        public_id: Optional custom public ID for the image.
        
    Returns:
        Public URL of the uploaded image, or None if upload failed.
    """
    if not CLOUDINARY_AVAILABLE:
        logger.error("Cloudinary not available")
        return None
    
    # Check if image exists
    if not Path(image_path).exists():
        logger.error(f"Image file not found: {image_path}")
        return None
    
    try:
        logger.info(f"📤 Uploading image to Cloudinary: {Path(image_path).name}")
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            image_path,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            format="png"
        )
        
        # Get secure URL
        image_url = result.get('secure_url')
        
        if image_url:
            logger.success(f"✅ Image uploaded: {image_url}")
            return image_url
        else:
            logger.error("❌ Upload succeeded but no URL returned")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to upload image to Cloudinary: {e}")
        return None


def upload_multiple_images(
    image_paths: list,
    folder: str = "osi-news"
) -> dict:
    """
    Upload multiple images to Cloudinary.
    
    Args:
        image_paths: List of local image paths.
        folder: Cloudinary folder to organize images.
        
    Returns:
        Dictionary mapping original paths to public URLs.
    """
    url_mapping = {}
    
    for image_path in image_paths:
        url = upload_image_to_cloudinary(image_path, folder=folder)
        if url:
            url_mapping[image_path] = url
    
    logger.info(f"📊 Uploaded {len(url_mapping)}/{len(image_paths)} images successfully")
    
    return url_mapping


def delete_image_from_cloudinary(public_id: str) -> bool:
    """
    Delete an image from Cloudinary.
    
    Args:
        public_id: The public ID of the image to delete.
        
    Returns:
        True if deletion successful, False otherwise.
    """
    if not CLOUDINARY_AVAILABLE:
        return False
    
    try:
        result = cloudinary.uploader.destroy(public_id)
        
        if result.get('result') == 'ok':
            logger.success(f"✅ Image deleted: {public_id}")
            return True
        else:
            logger.warning(f"⚠️ Image deletion failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error deleting image: {e}")
        return False


def test_cloudinary_connection():
    """Test Cloudinary connection and configuration."""
    print("\n" + "=" * 60)
    print("🧪 Cloudinary Connection Test")
    print("=" * 60)
    
    if not CLOUDINARY_AVAILABLE:
        print("❌ Cloudinary SDK not installed")
        print("   Run: pip install cloudinary")
        return False
    
    # Check configuration
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
    
    print(f"\n📋 Configuration:")
    print(f"   Cloud Name: {cloud_name if cloud_name else '❌ Not set'}")
    print(f"   API Key: {api_key[:10] + '...' if api_key else '❌ Not set'}")
    print(f"   API Secret: {'✅ Set' if api_secret else '❌ Not set'}")
    
    if not all([cloud_name, api_key, api_secret]):
        print("\n❌ Cloudinary credentials not configured in .env")
        print("   Add: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
        return False
    
    # Test API connection
    try:
        print("\n🔌 Testing API connection...")
        result = cloudinary.api.ping()
        
        if result.get('status') == 'ok':
            print("✅ Cloudinary API connection successful!")
            return True
        else:
            print(f"❌ API test failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    test_cloudinary_connection()
