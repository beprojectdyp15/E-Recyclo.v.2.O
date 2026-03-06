from django import template

register = template.Library()

@register.filter
def mask_data(value):
    """
    Masks string data, showing only the last 4 characters.
    e.g., '1234567890' -> '******7890'
    """
    if not value or len(str(value)) <= 4:
        return value
    
    val_str = str(value)
    mask = '*' * (len(val_str) - 4)
    return f"{mask}{val_str[-4:]}"
