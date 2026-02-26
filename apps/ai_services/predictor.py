"""
E-Waste Detection Predictor
Uses YOLOv8 model for classification with lazy loading
"""
from pathlib import Path
from PIL import Image
import numpy as np
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Model path
MODEL_PATH = Path(__file__).parent / 'ml_weights' / 'best.pt'


class EWastePredictor:
    """
    Singleton predictor for e-waste detection
    
    IMPORTANT: Model loads lazily to avoid import issues during Django migrations.
    This is critical for Railway/Docker deployments where YOLO/OpenCV can't load
    during the build phase (missing system libraries).
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern - only one predictor instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def model(self):
        """
        Lazy load YOLO model only when first prediction is made.
        
        This prevents import errors during:
        - Django migrations
        - collectstatic
        - Server startup in environments without GPU/display
        
        Returns:
            YOLO model instance
        """
        if self._model is None:
            try:
                # Import YOLO here, not at module level
                # This prevents loading during migrations/collectstatic
                from ultralytics import YOLO
                
                if not MODEL_PATH.exists():
                    logger.error(f"Model file not found at {MODEL_PATH}")
                    raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}")
                
                logger.info(f"Loading YOLO model from {MODEL_PATH}")
                self._model = YOLO(str(MODEL_PATH))
                logger.info("✓ YOLO model loaded successfully")
                
            except ImportError as e:
                logger.error(f"Failed to import ultralytics: {e}")
                logger.error("Make sure ultralytics is installed: pip install ultralytics")
                raise
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
                raise
        
        return self._model
    
    def predict(self, image_path, confidence_threshold=0.25):
        """
        Predict e-waste category from image
        
        Args:
            image_path: Path to image file, PIL Image, or numpy array
            confidence_threshold: Minimum confidence (0-1) for predictions
            
        Returns:
            dict: {
                'success': bool,
                'category': str,
                'confidence': float,
                'all_predictions': list,
                'message': str
            }
        """
        try:
            # Model loads here on first prediction (lazy loading)
            results = self.model(image_path, conf=confidence_threshold, verbose=False)
            
            if not results or len(results) == 0:
                return {
                    'success': False,
                    'category': None,
                    'confidence': 0.0,
                    'all_predictions': [],
                    'message': 'No objects detected in image'
                }
            
            # Get first result
            result = results[0]
            
            # Check if any predictions
            if result.boxes is None or len(result.boxes) == 0:
                return {
                    'success': False,
                    'category': None,
                    'confidence': 0.0,
                    'all_predictions': [],
                    'message': 'No e-waste detected in image'
                }
            
            # Get all predictions sorted by confidence
            predictions = []
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = result.names[class_id]
                
                predictions.append({
                    'category': class_name,
                    'confidence': confidence,
                    'class_id': class_id
                })
            
            # Sort by confidence (highest first)
            predictions.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Return top prediction
            top_prediction = predictions[0]
            
            return {
                'success': True,
                'category': top_prediction['category'],
                'confidence': top_prediction['confidence'],
                'all_predictions': predictions,
                'message': f"Detected {top_prediction['category']} with {top_prediction['confidence']:.1%} confidence"
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {
                'success': False,
                'category': None,
                'confidence': 0.0,
                'all_predictions': [],
                'message': f"Prediction error: {str(e)}"
            }
    
    def predict_batch(self, image_paths, confidence_threshold=0.25):
        """
        Predict e-waste categories for multiple images
        
        Args:
            image_paths: List of image paths
            confidence_threshold: Minimum confidence (0-1) for predictions
            
        Returns:
            list of prediction dicts
        """
        results = []
        for image_path in image_paths:
            results.append(self.predict(image_path, confidence_threshold))
        return results
    
    def is_model_loaded(self):
        """Check if model is currently loaded in memory"""
        return self._model is not None
    
    def unload_model(self):
        """Unload model from memory (useful for freeing RAM)"""
        if self._model is not None:
            logger.info("Unloading YOLO model from memory")
            self._model = None


# Create singleton instance (but model not loaded yet!)
predictor = EWastePredictor()


# Convenience function for easy imports
def predict_ewaste(image_path, confidence_threshold=0.25):
    """
    Convenience function for e-waste prediction
    
    Usage:
        from apps.ai_services.predictor import predict_ewaste
        result = predict_ewaste('path/to/image.jpg')
    """
    return predictor.predict(image_path, confidence_threshold)