"""
YOLO Model Predictor for E-Waste Classification
Handles model loading, prediction, and result processing
"""
import os
import torch
from pathlib import Path
from django.conf import settings
from .category_mapper import CategoryMapper
from .image_processor import ImageProcessor

# ============================================
# FIX FOR PYTORCH 2.6+ WEIGHTS_ONLY SECURITY
# ============================================
# Method 1: Add safe globals for ultralytics
try:
    import ultralytics.nn.tasks
    torch.serialization.add_safe_globals([ultralytics.nn.tasks.DetectionModel])
except Exception:
    pass

# Method 2: Monkey-patch torch.load to use weights_only=False for .pt files
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    # Force weights_only=False for model files
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load
# ============================================

from ultralytics import YOLO

class EWastePredictor:
    """YOLOv8 based E-Waste classifier"""
    
    _model = None  # Singleton pattern - load model once
    
    MODEL_PATH = Path(__file__).parent / 'ml_weights' / 'best.pt'
    
    @classmethod
    def get_model(cls):
        """Load model (singleton pattern for efficiency)"""
        if cls._model is None:
            try:
                print(f"Loading YOLO model from: {cls.MODEL_PATH}")
                cls._model = YOLO(str(cls.MODEL_PATH))
                print("✓ Model loaded successfully!")
            except Exception as e:
                print(f"✗ Failed to load model: {e}")
                raise RuntimeError(f"Could not load YOLO model: {str(e)}")
        
        return cls._model
    
    @classmethod
    def predict(cls, image_file, return_details=False):
        """
        Predict e-waste category from uploaded image
        """
        try:
            # Preprocess image
            img, original_size = ImageProcessor.preprocess_image(image_file)
            
            # Get model
            model = cls.get_model()
            
            # Run prediction with LOWER confidence threshold for better detection
            results = model(img, conf=0.15)  # Lowered from 0.25 to 0.15
            
            # Extract prediction
            if len(results) > 0 and len(results[0].boxes) > 0:
                # Get ALL predictions, not just top one
                boxes = results[0].boxes
                
                # Sort by confidence
                confidences = boxes.conf.cpu().numpy()
                sorted_indices = confidences.argsort()[::-1]
                
                # Get top prediction
                top_idx = sorted_indices[0]
                class_id = int(boxes.cls[top_idx])
                confidence = float(boxes.conf[top_idx])
                
                print(f"🔍 Detection: Class {class_id}, Confidence: {confidence:.2%}")
                print(f"   Image size: {original_size}")
                
                # ENHANCED MAPPING with size-based logic
                yolo_class = CategoryMapper.YOLO_CLASSES.get(class_id, 'other')
                
                # Smart override for 'appliance' if detected as monitor-sized
                if yolo_class == 'appliance':
                    width, height = original_size
                    aspect_ratio = width / height if height > 0 else 1
                    
                    # If aspect ratio is very wide (>1.5), likely a TV/Monitor
                    if aspect_ratio > 1.5:
                        print(f"   ⚠️ Appliance but wide aspect {aspect_ratio:.2f} → Likely Monitor/TV")
                        # Keep as appliance (will show as "Home Appliance" which includes TV)
                    else:
                        print(f"   ✓ Appliance with aspect {aspect_ratio:.2f} → Large appliance")
                
                # Map to user-friendly category
                category_info = CategoryMapper.map_prediction(
                    class_id, 
                    confidence,
                    original_size
                )
                
                # Add alternative suggestions if confidence is low
                suggestions = []
                if confidence < 0.50:  # Low confidence
                    # Get top 3 predictions
                    for idx in sorted_indices[:3]:
                        alt_class_id = int(boxes.cls[idx])
                        alt_conf = float(boxes.conf[idx])
                        alt_class = CategoryMapper.YOLO_CLASSES.get(alt_class_id, 'other')
                        suggestions.append({
                            'category': alt_class,
                            'confidence': round(alt_conf * 100, 1)
                        })
                
                prediction_result = {
                    'success': True,
                    'category': category_info['yolo_class'],
                    'display_name': category_info['display_name'],
                    'description': category_info['description'],
                    'confidence': category_info['confidence'],
                    'icon': category_info['icon'],
                    'recyclable_parts': category_info['recyclable_parts'],
                    'ai_detected': True,
                    'suggestions': suggestions,  # Alternative categories
                }
                
                if return_details:
                    prediction_result['raw_class_id'] = class_id
                    prediction_result['bounding_box'] = boxes.xyxy[top_idx].tolist()
                
                return prediction_result
                
            else:
                # No detection
                return {
                    'success': True,
                    'category': 'other',
                    'display_name': 'Computer Accessory',
                    'description': 'Could not classify - please select manually',
                    'confidence': 0.0,
                    'icon': 'devices_other',
                    'recyclable_parts': ['Plastic', 'Circuit Board', 'Metal Parts'],
                    'ai_detected': False,
                    'suggestions': [],
                }
                
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'category': 'other',
                'display_name': 'Other E-Waste',
                'ai_detected': False,
                'suggestions': [],
            }
            
    @classmethod
    def batch_predict(cls, image_files):
        """Predict multiple images at once"""
        results = []
        for image_file in image_files:
            results.append(cls.predict(image_file))
        return results