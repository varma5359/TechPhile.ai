# your_app/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Template filter to get dictionary items with a default empty set"""
    return dictionary.get(key, set())