from django import template

register = template.Library()

@register.filter
def sum_field(queryset, field):
    """
    Sums a specific field in a list of dictionaries or objects.
    Usage: {{ my_list|sum_field:'count' }}
    """
    if not queryset:
        return 0
    
    total = 0
    for item in queryset:
        if isinstance(item, dict):
            total += item.get(field, 0)
        else:
            total += getattr(item, field, 0)
    return total

@register.filter
def percentage(value, total):
    """
    Calculates percentage (value / total * 100)
    Usage: {{ value|percentage:total }}
    """
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
@register.filter
def split(value, arg):
    """
    Splits the string by arg and returns the list.
    """
    return value.split(arg)

@register.filter
def trim(value):
    """
    Strips whitespace from the string.
    """
    return value.strip()
