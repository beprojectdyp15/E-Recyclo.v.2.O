"""
Smart Category Mapper for E-Waste Classification
Maps YOLO predictions to user-friendly categories with hybrid logic
"""

class CategoryMapper:
    """
    Hybrid mapping system:
    - Direct mapping for clear detections
    - Smart suggestions for 'other' category based on context
    """
    
    # YOLO classes (based on your training)
    YOLO_CLASSES = {
        0: 'monitor',
        1: 'laptop', 
        2: 'battery',
        3: 'appliance',
        4: 'smartphone',
        5: 'other'
    }
    
    # User-friendly category mapping
    CATEGORY_MAPPING = {
        'laptop': {
            'display_name': 'Laptop',
            'description': 'Laptops, Notebooks, and Portable Computers',
            'icon': 'laptop_mac',
            'recyclable_parts': ['Battery', 'Screen', 'Motherboard', 'Hard Drive'],
        },
        'monitor': {
            'display_name': 'Monitor & TV',
            'description': 'Computer Monitors, Televisions, and Displays',
            'icon': 'monitor',
            'recyclable_parts': ['Screen Panel', 'Power Supply', 'Circuit Board'],
        },
        'smartphone': {
            'display_name': 'Smartphone',
            'description': 'Mobile Phones and Smartphones',
            'icon': 'smartphone',
            'recyclable_parts': ['Battery', 'Screen', 'Circuit Board', 'Camera'],
        },
        'battery': {
            'display_name': 'Battery & Charger',
            'description': 'Batteries, Chargers, and Power Adapters',
            'icon': 'battery_charging_full',
            'recyclable_parts': ['Lithium Cells', 'Metal Casing', 'Cables'],
        },
        'appliance': {
            'display_name': 'Large Appliance',
            'description': 'Washing Machines, Microwaves, Refrigerators (NOT TVs)',
            'icon': 'kitchen',
            'recyclable_parts': ['Motor', 'Metal Frame', 'Circuit Board', 'Compressor'],
        },
        'other': {
            'display_name': 'Computer Accessory',
            'description': 'Mouse, Keyboard, Cables, Speakers, Printer, Router',
            'icon': 'devices_other',
            'recyclable_parts': ['Plastic', 'Circuit Board', 'Metal Parts'],
        }
    }


    # Smart suggestions based on image features (for 'other' category)
    SIZE_BASED_MAPPING = {
        'large': 'appliance',      # TV, Washing Machine, Refrigerator
        'medium': 'monitor',        # Printers, Speakers, Desktop PC
        'small': 'other',          # Mouse, Keyboard, Cables
    }
    
    @classmethod
    def map_prediction(cls, yolo_class_id, confidence, image_size=None):
        """
        Map YOLO prediction to user-friendly category
        
        Args:
            yolo_class_id: Predicted class ID from YOLO
            confidence: Prediction confidence (0-1)
            image_size: Tuple of (width, height) for smart mapping
            
        Returns:
            dict: Category information with display name, description, etc.
        """
        # Get YOLO class name
        yolo_class = cls.YOLO_CLASSES.get(yolo_class_id, 'other')
        
        # If 'other' category and low confidence, use smart mapping
        if yolo_class == 'other' and image_size:
            yolo_class = cls._smart_map_other(image_size, confidence)
        
        # Get category details
        category_info = cls.CATEGORY_MAPPING.get(yolo_class, cls.CATEGORY_MAPPING['other'])
        
        # Add metadata
        category_info['yolo_class'] = yolo_class
        category_info['confidence'] = round(confidence * 100, 2)
        category_info['ai_detected'] = True
        
        return category_info
    
    @classmethod
    def _smart_map_other(cls, image_size, confidence):
        """Enhanced smart mapping"""
        width, height = image_size
        area = width * height
        aspect_ratio = width / height if height > 0 else 1
        
        # Very wide aspect ratio → Monitor or TV
        if aspect_ratio > 1.6:
            return 'monitor'  # TVs and monitors grouped together
        
        # Large square-ish → Washing machine, refrigerator
        elif area > 500000 and 0.6 < aspect_ratio < 1.4:
            return 'appliance'
        
        # Medium size → Desktop components or printer
        elif area > 200000:
            return 'other'  # Computer accessories
        
        # Small → definitely accessories
        else:
            return 'other'
    
    
    @classmethod
    def get_all_categories(cls):
        """Get list of all available categories for dropdown"""
        return [
            {
                'value': key,
                'label': info['display_name'],
                'description': info['description'],
                'icon': info['icon']
            }
            for key, info in cls.CATEGORY_MAPPING.items()
        ]
    
    @classmethod
    def get_category_choices(cls):
        """Django model choices format"""
        return [
            (key, info['display_name'])
            for key, info in cls.CATEGORY_MAPPING.items()
        ]