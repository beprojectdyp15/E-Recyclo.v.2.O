"""
Smart Category Mapper for E-Waste Classification — v3.0
Maps YOLO class name strings → 14 user-friendly grouped categories.

FALLBACK CHAIN (in order):
  1. Direct CLASS_TO_CATEGORY lookup
  2. Keyword substring match on class name
  3. top-N: check 2nd/3rd YOLO predictions if top-1 is 'other' or low confidence
  4. title_hint: keyword-match the item title typed by the user
  5. Image geometry (last resort)
"""


class CategoryMapper:

    # -----------------------------------------------------------------------
    # 14 GROUPED CATEGORIES
    # -----------------------------------------------------------------------
    CATEGORY_MAPPING = {
        'smartphone': {
            'display_name': 'Smartphone & Mobile',
            'description': 'Smartphones, Feature Phones, Flip Phones',
            'icon': 'smartphone',
            'recyclable_parts': ['Battery', 'Screen', 'Circuit Board', 'Camera Module', 'Speakers'],
            'value_range': (200, 800),
        },
        'laptop': {
            'display_name': 'Laptop & Notebook',
            'description': 'Laptops, Notebooks, Ultrabooks, MacBooks, Chromebooks',
            'icon': 'laptop_mac',
            'recyclable_parts': ['Battery', 'Screen Panel', 'Motherboard', 'Hard Drive / SSD', 'RAM'],
            'value_range': (800, 3000),
        },
        'computer': {
            'display_name': 'Desktop Computer',
            'description': 'Desktop PCs, Towers, All-in-Ones, Workstations, Servers',
            'icon': 'computer',
            'recyclable_parts': ['CPU', 'Motherboard', 'RAM', 'Hard Drive', 'Power Supply', 'GPU'],
            'value_range': (500, 2000),
        },
        'tablet': {
            'display_name': 'Tablet & E-Reader',
            'description': 'Tablets, iPads, Android Tablets, Kindles, E-Readers',
            'icon': 'tablet_mac',
            'recyclable_parts': ['Battery', 'Screen', 'Circuit Board'],
            'value_range': (300, 1200),
        },
        'monitor_tv': {
            'display_name': 'Monitor & Television',
            'description': 'Computer Monitors, LED/LCD/Plasma/Smart TVs, Projectors',
            'icon': 'monitor',
            'recyclable_parts': ['Screen Panel', 'Power Supply Board', 'Main Circuit Board', 'Speakers'],
            'value_range': (400, 1500),
        },
        'battery_charger': {
            'display_name': 'Battery & Charger',
            'description': 'Phone/Laptop Chargers, Power Banks, AA/AAA/Lithium Batteries, UPS, Adapters',
            'icon': 'battery_charging_full',
            'recyclable_parts': ['Lithium Cells', 'Metal Casing', 'Copper Wire'],
            'value_range': (50, 300),
        },
        'peripheral': {
            'display_name': 'Computer Peripheral',
            'description': 'Keyboards, Mice, Trackpads, Webcams, Microphones, USB Hubs',
            'icon': 'keyboard',
            'recyclable_parts': ['Circuit Board', 'Plastic Casing', 'Metal Parts'],
            'value_range': (50, 400),
        },
        'audio_visual': {
            'display_name': 'Audio & Camera',
            'description': 'Headphones, Earphones, Speakers, Digital Cameras, Camcorders, DSLR, Action Cameras',
            'icon': 'headphones',
            'recyclable_parts': ['Speakers / Drivers', 'Battery', 'Circuit Board', 'Lens Assembly'],
            'value_range': (100, 600),
        },
        'storage_network': {
            'display_name': 'Storage & Networking',
            'description': 'Hard Drives, SSDs, USB Flash Drives, Memory Cards, Routers, Modems, Network Switches',
            'icon': 'storage',
            'recyclable_parts': ['Magnetic Platters', 'Flash Memory Chips', 'Circuit Board'],
            'value_range': (50, 500),
        },
        'gaming': {
            'display_name': 'Gaming Equipment',
            'description': 'Gaming Consoles (PlayStation, Xbox, Nintendo), Controllers, VR Headsets',
            'icon': 'sports_esports',
            'recyclable_parts': ['Circuit Board', 'Battery', 'Optical Drive', 'Cooling Fan'],
            'value_range': (300, 1500),
        },
        'large_appliance': {
            'display_name': 'Large Appliance',
            'description': 'Washing Machines, Refrigerators, Air Conditioners, Dishwashers, Dryers',
            'icon': 'kitchen',
            'recyclable_parts': ['Compressor', 'Motor', 'Metal Frame', 'Circuit Board', 'Copper Coil'],
            'value_range': (500, 2500),
        },
        'small_appliance': {
            'display_name': 'Small Appliance',
            'description': 'Microwaves, Electric Irons, Vacuum Cleaners, Hair Dryers, Toasters, Kettles, Fans',
            'icon': 'blender',
            'recyclable_parts': ['Motor', 'Heating Element', 'Metal Parts', 'Circuit Board'],
            'value_range': (100, 500),
        },
        'cable_component': {
            'display_name': 'Cable, Printer & Component',
            'description': 'Cables (USB/HDMI/Power), Circuit Boards, Printers, Scanners, Remote Controls, Calculators',
            'icon': 'cable',
            'recyclable_parts': ['Copper Wire', 'PCB', 'Plastic Insulation'],
            'value_range': (30, 200),
        },
        'other': {
            'display_name': 'Other / Not E-Waste',
            'description': 'Item not recognised as e-waste or does not belong to any known category',
            'icon': 'help_outline',
            'recyclable_parts': [],
            'value_range': (0, 0),
        },
    }

    # -----------------------------------------------------------------------
    # YOLO CLASS NAMES → CATEGORY KEY
    # Add new model class names here. Everything else is automatic.
    # -----------------------------------------------------------------------
    CLASS_TO_CATEGORY = {
        # Smartphones
        'smartphone': 'smartphone', 'mobile_phone': 'smartphone',
        'cell_phone': 'smartphone', 'iphone': 'smartphone',
        'android_phone': 'smartphone', 'feature_phone': 'smartphone',
        'flip_phone': 'smartphone', 'phone': 'smartphone',
        # Laptops
        'laptop': 'laptop', 'notebook': 'laptop', 'ultrabook': 'laptop',
        'chromebook': 'laptop', 'macbook': 'laptop', 'gaming_laptop': 'laptop',
        # Desktop computers
        'desktop_computer': 'computer', 'computer_tower': 'computer',
        'desktop': 'computer', 'all_in_one_computer': 'computer',
        'workstation': 'computer', 'server': 'computer', 'cpu': 'computer',
        # Tablets
        'tablet': 'tablet', 'ipad': 'tablet', 'android_tablet': 'tablet',
        'e_reader': 'tablet', 'kindle': 'tablet',
        # Monitors / TVs
        'monitor': 'monitor_tv', 'computer_monitor': 'monitor_tv',
        'lcd_monitor': 'monitor_tv', 'led_monitor': 'monitor_tv',
        'crt_monitor': 'monitor_tv', 'television': 'monitor_tv',
        'tv': 'monitor_tv', 'flat_screen_tv': 'monitor_tv',
        'led_tv': 'monitor_tv', 'lcd_tv': 'monitor_tv',
        'plasma_tv': 'monitor_tv', 'smart_tv': 'monitor_tv',
        'crt_television': 'monitor_tv', 'projector': 'monitor_tv',
        # Batteries / chargers
        'battery': 'battery_charger', 'laptop_battery': 'battery_charger',
        'aa_battery': 'battery_charger', 'aaa_battery': 'battery_charger',
        'lithium_battery': 'battery_charger', 'phone_charger': 'battery_charger',
        'laptop_charger': 'battery_charger', 'power_adapter': 'battery_charger',
        'charger': 'battery_charger', 'power_bank': 'battery_charger',
        'ups': 'battery_charger',
        # Peripherals
        'keyboard': 'peripheral', 'mouse': 'peripheral',
        'computer_mouse': 'peripheral', 'trackpad': 'peripheral',
        'webcam': 'peripheral', 'microphone': 'peripheral', 'usb_hub': 'peripheral',
        # Audio / cameras
        'headphones': 'audio_visual', 'earphones': 'audio_visual',
        'earbuds': 'audio_visual', 'speaker': 'audio_visual',
        'bluetooth_speaker': 'audio_visual', 'camera': 'audio_visual',
        'digital_camera': 'audio_visual', 'dslr_camera': 'audio_visual',
        'camcorder': 'audio_visual', 'action_camera': 'audio_visual',
        # Storage / networking
        'hard_drive': 'storage_network', 'hdd': 'storage_network',
        'ssd': 'storage_network', 'usb_drive': 'storage_network',
        'flash_drive': 'storage_network', 'memory_card': 'storage_network',
        'sd_card': 'storage_network', 'router': 'storage_network',
        'modem': 'storage_network', 'network_switch': 'storage_network',
        # Gaming
        'gaming_console': 'gaming', 'game_controller': 'gaming',
        'joystick': 'gaming', 'vr_headset': 'gaming',
        # Large appliances
        'washing_machine': 'large_appliance', 'refrigerator': 'large_appliance',
        'air_conditioner': 'large_appliance', 'dishwasher': 'large_appliance',
        'dryer': 'large_appliance', 'fridge': 'large_appliance',
        # Small appliances
        'microwave': 'small_appliance', 'microwave_oven': 'small_appliance',
        'electric_oven': 'small_appliance', 'toaster': 'small_appliance',
        'kettle': 'small_appliance', 'hair_dryer': 'small_appliance',
        'iron': 'small_appliance', 'vacuum_cleaner': 'small_appliance',
        'fan': 'small_appliance', 'electric_fan': 'small_appliance',
        'blender': 'small_appliance',
        # Cables / components
        'cable': 'cable_component', 'usb_cable': 'cable_component',
        'hdmi_cable': 'cable_component', 'power_cable': 'cable_component',
        'extension_cord': 'cable_component', 'circuit_board': 'cable_component',
        'pcb': 'cable_component', 'printer': 'cable_component',
        'scanner': 'cable_component', 'fax_machine': 'cable_component',
        'copier': 'cable_component', 'remote_control': 'cable_component',
        'calculator': 'cable_component', 'telephone': 'cable_component',
        'landline_phone': 'cable_component',
        # Fallback
        'other': 'other', 'unknown': 'other',
        'not_ewaste': 'other', 'non_ewaste': 'other',
    }

    LOW_CONF_THRESHOLD = 0.40

    # -----------------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------------

    @classmethod
    def map_prediction(cls, class_name, confidence, all_predictions=None, title_hint=None, image_size=None):
        """
        Map a raw YOLO class name → enriched category dict.

        Args:
            class_name      : string from predictor (e.g. "lcd_monitor")
                              OR legacy integer class_id
            confidence      : float 0-1
            all_predictions : [{'category':str,'confidence':float}, ...]
            title_hint      : item title typed by user (keyword override)
            image_size      : (width, height) — last-resort geometry
        """
        # Legacy integer support
        _LEGACY = {0:'monitor',1:'laptop',2:'battery',3:'appliance',4:'smartphone',5:'other',6:'cpu'}
        if isinstance(class_name, int):
            class_name = _LEGACY.get(class_name, 'other')

        normalised = str(class_name).strip().lower().replace('-', '_').replace(' ', '_')

        # 1. Direct lookup
        category_key = cls.CLASS_TO_CATEGORY.get(normalised)

        # 2. Keyword fallback on class name
        if category_key is None:
            category_key = cls._keyword_fallback(normalised)

        # 3. top-N fallback
        if (not category_key or category_key == 'other' or confidence < cls.LOW_CONF_THRESHOLD) and all_predictions:
            for pred in all_predictions[1:]:
                alt_raw  = str(pred.get('category', '')).strip().lower().replace('-','_').replace(' ','_')
                alt_key  = cls.CLASS_TO_CATEGORY.get(alt_raw) or cls._keyword_fallback(alt_raw)
                alt_conf = pred.get('confidence', 0.0)
                if alt_key and alt_key != 'other' and alt_conf >= 0.12:
                    category_key = alt_key
                    confidence   = alt_conf
                    break

        # 4. Title keyword override (catches "Car Battery", "Microwave", etc.)
        if (not category_key or category_key == 'other' or confidence < cls.LOW_CONF_THRESHOLD) and title_hint:
            kw = cls._title_keyword_match(title_hint)
            if kw:
                category_key = kw

        # 5. Geometry last resort
        if not category_key or category_key == 'other':
            category_key = cls._geometry_fallback(image_size) if image_size else 'other'

        info = cls.CATEGORY_MAPPING.get(category_key, cls.CATEGORY_MAPPING['other']).copy()
        info['category']    = category_key
        info['raw_class']   = class_name
        info['confidence']  = round(confidence * 100, 2)
        info['ai_detected'] = True
        return info

    @classmethod
    def get_estimated_value(cls, category_key):
        info = cls.CATEGORY_MAPPING.get(category_key, cls.CATEGORY_MAPPING['other'])
        return info.get('value_range', (50, 300))

    @classmethod
    def get_all_categories(cls):
        return [
            {'value': k, 'label': v['display_name'], 'description': v['description'], 'icon': v['icon']}
            for k, v in cls.CATEGORY_MAPPING.items()
        ]

    @classmethod
    def get_category_choices(cls):
        return [(k, v['display_name']) for k, v in cls.CATEGORY_MAPPING.items()]

    # -----------------------------------------------------------------------
    # PRIVATE HELPERS
    # -----------------------------------------------------------------------

    @classmethod
    def _keyword_fallback(cls, normalised):
        RULES = [
            (['phone','mobile','iphone','samsung','pixel','oneplus','redmi'],  'smartphone'),
            (['laptop','notebook','macbook','chromebook'],                      'laptop'),
            (['desktop','tower','workstation','server','all_in_one'],          'computer'),
            (['tablet','ipad','kindle','e_reader'],                            'tablet'),
            (['monitor','television','tv','display','screen','projector'],     'monitor_tv'),
            (['battery','charger','adapter','power_bank','ups','inverter'],    'battery_charger'),
            (['keyboard','trackpad','webcam','microphone'],                    'peripheral'),
            (['headphone','earphone','earbud','speaker','camera','dslr'],      'audio_visual'),
            (['hard_drive','hdd','ssd','usb','memory','router','modem'],       'storage_network'),
            (['console','controller','joystick','gamepad','vr'],               'gaming'),
            (['washing','refrigerator','fridge','air_condition','dishwasher'], 'large_appliance'),
            (['microwave','toaster','kettle','iron','vacuum','fan','oven'],    'small_appliance'),
            (['cable','wire','cord','pcb','board','printer','scanner',
              'remote','calculator','telephone'],                               'cable_component'),
        ]
        for keywords, category in RULES:
            if any(kw in normalised for kw in keywords):
                return category
        return None

    @classmethod
    def _title_keyword_match(cls, title):
        """Keyword-match user-typed title. Handles Indian product names."""
        t = ' ' + title.lower() + ' '
        RULES = [
            (['battery','charger','power bank','adapter','ups','inverter',
              'car battery','truck battery','vehicle battery'],            'battery_charger'),
            (['microwave','oven','toaster','kettle','iron ','vacuum',
              'hair dryer','geyser','water heater','cooler','chimney',
              'mixer','grinder','juicer','induction'],                    'small_appliance'),
            (['washing machine','refrigerator','fridge','air conditioner',
              ' ac ',' a.c.','dishwasher','water purifier'],              'large_appliance'),
            (['monitor','television',' tv ','lcd','led tv','oled',
              'projector','display screen'],                               'monitor_tv'),
            (['laptop','notebook','chromebook','macbook'],                 'laptop'),
            (['desktop','cpu cabinet','pc cabinet','motherboard',
              'processor','graphics card',' gpu '],                       'computer'),
            (['mobile','smartphone',' phone','iphone','android',
              'tablet','ipad'],                                            'smartphone'),
            (['camera','dslr','speaker','headphone','earphone',
              'earbuds','home theatre','soundbar'],                       'audio_visual'),
            (['playstation','xbox','nintendo','game console',
              'controller','joystick','gamepad'],                         'gaming'),
            (['router','modem','hard disk','hard drive','ssd',
              'pendrive','pen drive','memory card','network switch'],     'storage_network'),
            (['keyboard','webcam','printer','scanner'],                   'peripheral'),
            (['hdmi','usb wire','extension cord','remote control',
              'calculator'],                                               'cable_component'),
        ]
        for keywords, category in RULES:
            if any(kw in t for kw in keywords):
                return category
        return None

    @classmethod
    def _geometry_fallback(cls, image_size):
        width, height = image_size
        area  = width * height
        ratio = width / height if height > 0 else 1
        if ratio > 1.6:             return 'monitor_tv'
        if area > 500_000:          return 'large_appliance'
        if area > 200_000:          return 'computer'
        return 'other'