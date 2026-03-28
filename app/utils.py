import mistune
import bleach

ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
    'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
    'h1', 'h2', 'h3', 'p', 'br',
]
ALLOWED_ATTRIBUTES = {'a': ['href', 'title'], 'abbr': ['title'], 'acronym': ['title']}

_md = mistune.create_markdown()


def render_markdown(text):
    """Convert markdown to sanitized HTML. Returns '' for falsy input."""
    if not text:
        return ''
    html = _md(text)
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
