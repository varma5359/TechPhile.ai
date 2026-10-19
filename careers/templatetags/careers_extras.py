import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from careers.rendering import render_markdown

register = template.Library()

_BOLD = re.compile(r'\*\*(.+?)\*\*')
_CODE = re.compile(r'`([^`]+)`')


@register.filter
def markdown_lesson(value):
    """Render admin-written Markdown (sanitised)."""
    return render_markdown(value)


@register.filter
def inline(value):
    """Render ``**bold**`` and ```code``` in admin-written lesson text.

    The text is HTML-escaped first, so only these two constructs can add markup.
    """
    text = escape(value or '')
    text = _BOLD.sub(r'<strong>\1</strong>', text)
    text = _CODE.sub(r'<code>\1</code>', text)
    return mark_safe(text)
