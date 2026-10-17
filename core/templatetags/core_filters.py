from django import template

register = template.Library()

@register.filter
def lookup(dict_obj, key):
    """Template filter to lookup dictionary values by key."""
    if dict_obj and key:
        return dict_obj.get(key, [])
    return []