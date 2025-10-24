import json, re

NEXT_PUSH_RE = re.compile(
    r'(?:self\.)?__next_f\.push\(\s*(\[[\s\S]*?\])\s*\)\s*;?',
    re.DOTALL
)

def _re_escape_ctrl(s: str) -> str:
    """Re-escape literal control chars back into JSON-safe sequences."""
    # Be conservative; only the common ones we see in these payloads:
    return (s
        .replace("\r\n", "\\r\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

def _collapse_overescaped_quotes(s: str) -> str:
    # Turn \\\" back into \", but leave \\n etc. untouched.
    # Replace a backslash that precedes a quote.
    return re.sub(r'\\\\(?=")', r'\\', s)

def iter_next_f_payloads(text: str):
    """
    Yield (channel_id, inner_python_obj) for each __next_f.push(...) block found.
    Uses multiple strategies to survive different escaping variants.
    """
    for m in NEXT_PUSH_RE.finditer(text):
        raw_arg = m.group(1)

        # Strategy A: one unicode_escape, then outer json
        arg1 = raw_arg.encode("utf-8").decode("unicode_escape")
        try:
            outer = json.loads(arg1)
        except Exception:
            # Strategy B: re-escape control chars before outer loads
            arg1b = _re_escape_ctrl(arg1)
            try:
                outer = json.loads(arg1b)
            except Exception:
                # Strategy C: avoid unicode_escape entirely; only collapse over-escaped quotes
                arg2 = _collapse_overescaped_quotes(raw_arg)
                try:
                    outer = json.loads(arg2)
                except Exception:
                    # give up on this block
                    continue

        if not (isinstance(outer, list) and len(outer) >= 2 and isinstance(outer[1], str)):
            continue

        chan_str = outer[1]
        channel_id, inner_text = (chan_str.split(":", 1) + [None])[:2] if ":" in chan_str else (None, chan_str)

        # Parse inner JSON. Try direct; if it fails, fallback to re-escaping controls once.
        try:
            inner = json.loads(inner_text)
        except Exception:
            inner = json.loads(_re_escape_ctrl(inner_text))

        yield channel_id, inner


def extract_next_f_json(block: str):
    """
    Convenience: return the FIRST (inner, channel_id) pair found in block.
    """
    for channel_id, inner in iter_next_f_payloads(block):
        return inner, channel_id
    raise ValueError("No parsable __next_f.push payload found in the provided block.")