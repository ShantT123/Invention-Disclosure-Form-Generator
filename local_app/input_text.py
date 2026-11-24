"""Separate HTTP intake, saved-text, and local inference budgets."""
MAX_INPUT_BYTES = 200_000
MAX_REQUEST_BYTES = 2 * 1024 * 1024
DIRECT_INPUT_BYTES = 6000
CHUNK_BYTES = 3600
DIGEST_BYTES = 2200


def validate_input(text, minimum=3, existing_bytes=0):
    if not isinstance(text, str) or len(text.strip()) < minimum:
        raise ValueError(f'Enter at least {minimum} characters of invention text')
    if '\x00' in text:
        raise ValueError('Paste readable text, not binary content')
    size = len(text.encode('utf-8'))
    if existing_bytes + size > MAX_INPUT_BYTES:
        raise ValueError(f'Text exceeds the {MAX_INPUT_BYTES:,}-byte project limit ({existing_bytes + size:,} UTF-8 bytes supplied). Nothing was saved or truncated. Use a shorter document or a separate project.')
    return text


def split_text(text, limit=CHUNK_BYTES):
    """Lossless, UTF-8-bounded sections; prefer paragraph/word boundaries."""
    if limit < 4:
        raise ValueError('Chunk size must accommodate a UTF-8 character')
    start = 0
    while start < len(text):
        end, size = start, 0
        while end < len(text):
            width = len(text[end].encode('utf-8'))
            if size + width > limit:
                break
            size += width; end += 1
        if end < len(text):
            boundary = text.rfind('\n', start + (end-start)//2, end)
            if boundary < 0:
                boundary = text.rfind(' ', start + (end-start)//2, end)
            if boundary >= start:
                end = boundary + 1
        yield start, end, text[start:end]
        start = end
