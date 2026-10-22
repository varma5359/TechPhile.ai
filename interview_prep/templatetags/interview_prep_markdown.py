"""Render model-authored Markdown as a small, sanitized HTML subset."""

import markdown
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def safe_markdown(value):
    if not isinstance(value, str) or not value.strip():
        return ''
    rendered = markdown.markdown(value, extensions=['fenced_code', 'sane_lists', 'tables'])
    cleaned = nh3.clean(
        rendered,
        tags={'p', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'h3', 'h4', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td'},
        attributes={},
        url_schemes=set(),
    )
    return mark_safe(cleaned)
