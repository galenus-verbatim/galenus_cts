def _format_critical_edition(edition: dict) -> str:
    """Format a critical edition for display: 'LastName, Date'."""
    editor = None
    for c in edition.get("creators", []):
        if c.get("creatorType") == "editor":
            editor = c
            break
    if editor is None:
        for c in edition.get("creators", []):
            if c.get("lastName"):
                editor = c
                break
    if editor is None:
        return ""
    name = editor.get("lastName") or editor.get("name", "")
    return f"{name}, {edition.get('date', '')}"


def _format_modern_translation(translation: dict) -> str:
    """Format a modern translation for display: 'LastName, Date (language)'."""
    translator = None
    for c in translation.get("creators", []):
        if c.get("creatorType") == "translator":
            translator = c
            break
    if translator is None:
        for c in translation.get("creators", []):
            if c.get("lastName"):
                translator = c
                break
    if translator is None:
        return ""
    name = translator.get("lastName") or translator.get("name", "")
    return f"{name}, {translation.get('date', '')} ({translation.get('language', '')})"


def _int_or_zero(s: str | None) -> int:
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0
