"""
Image preprocessing for YOLO model
"""
from PIL import Image
import io

class ImageProcessor:
    """Preprocess images for YOLO prediction"""
    
    @staticmethod
    def preprocess_image(image_file):
        """
        Preprocess uploaded image for YOLO model
        
        Args:
            image_file: Django UploadedFile object
            
        Returns:
            PIL.Image: Preprocessed image
        """
        try:
            # Open image
            img = Image.open(image_file)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get original size for smart mapping
            original_size = img.size
            
            # YOLO expects images in specific format, but ultralytics handles this
            # We just ensure it's RGB
            
            return img, original_size
            
        except Exception as e:
            raise ValueError(f"Failed to process image: {str(e)}")
    
    @staticmethod
    def get_image_dimensions(image_file):
        """Get image dimensions without loading full image"""
        try:
            img = Image.open(image_file)
            return img.size  # (width, height)
        except:
            return (0, 0)