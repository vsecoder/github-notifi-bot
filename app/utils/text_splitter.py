"""Split a long Telegram-HTML message into per-message-limit-friendly chunks.

Telegram's hard limit for ``sendMessage.text`` is 4096 characters. The
splitter walks a hierarchy of safe boundaries:

1. **Between blockquotes** — gap between ``</blockquote>`` and ``<blockquote>``.
   This is the natural per-item boundary in event formatters
   (push commits, PR review summaries, …).
2. **Between paragraphs** — double newlines.
3. **Between lines** — single newlines.
4. **Hard-cut** — last resort. May split inside a tag in extreme edge cases.

We assume callers don't span inline tags (``<b>``, ``<i>``, ``<a>``,
``<code>``) across blockquotes / paragraphs / newlines. All event
formatters in this codebase follow that convention, so HTML stays balanced
through the first three split levels.
"""
import re


# Telegram's limit is 4096; leave headroom for HTML overhead and any
# safe-margin transformations.
SAFE_LIMIT = 4000


def split_html_message(text: str, max_len: int = SAFE_LIMIT) -> list[str]:
    """Return a list of chunks, each ≤ ``max_len`` characters long.

    For text already short enough, returns ``[text]`` unchanged.
    """
    if len(text) <= max_len:
        return [text]
    return _greedy_pack(_split_blockquote_boundaries(text), max_len)


# ---- internal helpers ----

# Match the whitespace gap between an end-blockquote and a start-blockquote.
# Lookbehind/lookahead keep the tags themselves attached to their pieces.
_BLOCKQUOTE_GAP = re.compile(
    r'(?<=</blockquote>)\s*\n+\s*(?=<blockquote)'
)


def _split_blockquote_boundaries(text: str) -> list[str]:
    return _BLOCKQUOTE_GAP.split(text)


def _greedy_pack(pieces: list[str], max_len: int) -> list[str]:
    """Pack adjacent pieces into chunks ≤ ``max_len``. Pieces longer than
    ``max_len`` get split by paragraph / line as needed."""
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(piece) > max_len:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_by_paragraphs(piece, max_len))
            continue

        if current and len(current) + len(piece) + 1 > max_len:
            chunks.append(current)
            current = piece
        else:
            current = piece if not current else f"{current}\n{piece}"

    if current:
        chunks.append(current)
    return chunks


def _split_by_paragraphs(text: str, max_len: int) -> list[str]:
    paragraphs = text.split("\n\n")
    if len(paragraphs) <= 1:
        return _split_by_lines(text, max_len)

    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if len(p) > max_len:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_by_lines(p, max_len))
            continue
        if current and len(current) + len(p) + 2 > max_len:
            chunks.append(current)
            current = p
        else:
            current = p if not current else f"{current}\n\n{p}"

    if current:
        chunks.append(current)
    return chunks


def _split_by_lines(text: str, max_len: int) -> list[str]:
    lines = text.split("\n")
    chunks: list[str] = []
    current = ""
    for line in lines:
        if len(line) > max_len:
            if current:
                chunks.append(current)
                current = ""
            # Last resort — hard-cut. Risks an unbalanced inline tag in
            # extreme cases but keeps delivery flowing.
            for i in range(0, len(line), max_len):
                chunks.append(line[i : i + max_len])
            continue
        if current and len(current) + len(line) + 1 > max_len:
            chunks.append(current)
            current = line
        else:
            current = line if not current else f"{current}\n{line}"

    if current:
        chunks.append(current)
    return chunks
