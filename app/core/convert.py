from __future__ import annotations

from pathlib import Path
from typing import Optional


def compute_cache_key(
    docx: Path,
    conf: Optional[Path],
    xsl: Optional[Path],
    evolve_xsl: Optional[Path] = None,
    mtef_source: Optional[str] = None,
    table_model: Optional[str] = None,
    fontmaps_zip: Optional[Path] = None,
) -> str:
    import hashlib

    h = hashlib.sha256()
    # docx
    with open(docx, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    # conf (use provided path)
    conf_path = conf if conf else docx.with_suffix(".conf.xml")
    with open(conf_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            h.update(b"|CONF|")
            h.update(chunk)
    # xsl (optional)
    if xsl and xsl.exists():
        with open(xsl, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 512), b""):
                h.update(b"|XSL|")
                h.update(chunk)
    else:
        h.update(b"|XSL|NONE")
    # evolve driver (optional)
    if evolve_xsl and evolve_xsl.exists():
        with open(evolve_xsl, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 512), b""):
                h.update(b"|EVOLVE|")
                h.update(chunk)
    else:
        h.update(b"|EVOLVE|NONE")
    # mtef/table
    h.update(("|MTEF|" + (mtef_source or "NONE")).encode("utf-8"))
    h.update(("|TABLE|" + (table_model or "NONE")).encode("utf-8"))
    # fontmaps zip content
    if fontmaps_zip and fontmaps_zip.exists():
        with open(fontmaps_zip, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 512), b""):
                h.update(b"|FONTS|")
                h.update(chunk)
    else:
        h.update(b"|FONTS|NONE")
    return h.hexdigest()


def rewrite_conf_imports_to_default(conf_path: Path, default_conf: Path) -> bool:
    """Rewrite <import href="conf.xml"/> to default conf absolute URI.
    Returns True if a rewrite was performed.
    """
    target_uri = default_conf.resolve().as_uri()
    changed = False
    # Try XML parse first
    try:
        from xml.etree import ElementTree as ET

        tree = ET.parse(conf_path)
        root = tree.getroot()
        for el in root.iter():
            tag = el.tag
            if isinstance(tag, str) and tag.endswith('import'):
                href = (el.get('href') or '').strip()
                if href and '://' not in href and href.lower().endswith('conf.xml'):
                    el.set('href', target_uri)
                    changed = True
        if changed:
            tree.write(conf_path, encoding='utf-8', xml_declaration=True)
            return True
    except Exception:
        pass
    # Fallback: textual replace
    try:
        s = conf_path.read_text(encoding='utf-8', errors='ignore')
        s2 = s.replace('href="conf.xml"', f'href="{target_uri}"').replace("href='conf.xml'", f"href='{target_uri}'")
        if s2 != s:
            conf_path.write_text(s2, encoding='utf-8')
            return True
    except Exception:
        pass
    return False

