"""Safe Markdown rendering for admin-written lesson content.

Lessons are written in Markdown in Django admin. Output is sanitised with nh3,
so raw HTML or scripts typed into a lesson never reach students. Two fenced
block types draw diagrams without any JavaScript:

```flow
Business problem | "Sales are down 12%"
Validate the data | Complete? Same definitions?
```

```tree
? Is the drop visible in complete, comparable data?
  No -> Fix the data first.
  Yes ? Is the drop concentrated in one segment?
    Yes -> Investigate that segment.
    No -> Look at broad causes.
```
"""
import re

import markdown
import nh3
from django.utils.html import escape
from django.utils.safestring import mark_safe

ALLOWED_TAGS = {
    'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 'blockquote',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'div', 'span',
}
ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'}, 'div': {'class'}, 'p': {'class'}, 'span': {'class'}, 'code': {'class'},
    'th': {'align'}, 'td': {'align'},
}
FENCE = re.compile(r'^```(flow|tree)[ \t]*\n(.*?)^```[ \t]*$', re.S | re.M)


def _flow(body):
    items = []
    for line in body.strip().splitlines():
        if not line.strip():
            continue
        label, _, hint = line.partition('|')
        items.append((label.strip(), hint.strip().strip('"')))
    parts = ['<div class="lx-flow" role="list">']
    for i, (label, hint) in enumerate(items):
        parts.append('<div class="lx-flow-node" role="listitem"><strong>%s</strong>%s</div>'
                     % (escape(label), '<small>%s</small>' % escape(hint) if hint else ''))
        if i < len(items) - 1:
            parts.append('<div class="lx-flow-arrow" aria-hidden="true">&#8595;</div>')
    parts.append('</div>')
    return ''.join(parts)


def _parse_tree(lines):
    """Parse indented ``Answer -> outcome`` / ``Answer ? question`` lines into nested nodes."""
    root = {'question': '', 'branches': []}
    stack = [(-1, root)]
    for raw in lines:
        if not raw.strip():
            continue
        indent = (len(raw) - len(raw.lstrip(' '))) // 2
        text = raw.strip()
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith('?'):
            root['question'] = text[1:].strip()
        elif '->' in text:
            answer, _, outcome = text.partition('->')
            parent['branches'].append({'answer': answer.strip(), 'outcome': outcome.strip()})
        elif '?' in text:
            answer, _, question = text.partition('?')
            node = {'answer': answer.strip(), 'question': question.strip(), 'branches': []}
            parent['branches'].append(node)
            stack.append((indent, node))
    return root


def _tree_html(node, top=False):
    html = ''
    if top:
        html += '<div class="lx-q">%s</div>' % escape(node['question'])
    html += '<div class="lx-tree-branches">'
    for branch in node['branches']:
        html += '<div class="lx-branch"><span class="lx-answer">%s</span>' % escape(branch['answer'])
        if 'outcome' in branch:
            html += '<div class="lx-outcome">%s</div>' % escape(branch['outcome'])
        else:
            html += '<div class="lx-q">%s</div>' % escape(branch['question'])
            html += _tree_html(branch)
        html += '</div>'
    return html + '</div>'


def _diagram(kind, body):
    if kind == 'flow':
        return '<figure class="lx-figure">%s</figure>' % _flow(body)
    return '<figure class="lx-figure"><div class="lx-tree">%s</div></figure>' % _tree_html(_parse_tree(body.splitlines()), top=True)


def render_markdown(text):
    """Return sanitised HTML for ``text``. Diagram blocks are drawn from their own safe renderer."""
    if not text:
        return mark_safe('')
    diagrams = []

    def stash(match):
        diagrams.append(_diagram(match.group(1), match.group(2)))
        return '\n\nLXDIAGRAM%dLX\n\n' % (len(diagrams) - 1)

    source = FENCE.sub(stash, text.replace('\r\n', '\n'))
    html = markdown.markdown(source, extensions=['tables', 'fenced_code', 'sane_lists', 'admonition'])
    html = nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                     url_schemes={'http', 'https', 'mailto'}, link_rel='noopener noreferrer')
    for index, figure in enumerate(diagrams):
        html = html.replace('<p>LXDIAGRAM%dLX</p>' % index, figure)
    return mark_safe(html)
