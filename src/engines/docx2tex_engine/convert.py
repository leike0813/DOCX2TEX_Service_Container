from __future__ import annotations

from pathlib import Path


def compute_cache_key(
    docx: Path,
    conf: Path | None,
    xsl: Path | None,
    evolve_xsl: Path | None = None,
    mtef_source: str | None = None,
    table_model: str | None = None,
    fontmaps_zip: Path | None = None,
) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(docx, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    conf_path = conf if conf else docx.with_suffix(".conf.xml")
    with open(conf_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 512), b""):
            digest.update(b"|CONF|")
            digest.update(chunk)
    if xsl and xsl.exists():
        with open(xsl, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 512), b""):
                digest.update(b"|XSL|")
                digest.update(chunk)
    else:
        digest.update(b"|XSL|NONE")
    if evolve_xsl and evolve_xsl.exists():
        with open(evolve_xsl, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 512), b""):
                digest.update(b"|EVOLVE|")
                digest.update(chunk)
    else:
        digest.update(b"|EVOLVE|NONE")
    digest.update(("|MTEF|" + (mtef_source or "NONE")).encode("utf-8"))
    digest.update(("|TABLE|" + (table_model or "NONE")).encode("utf-8"))
    if fontmaps_zip and fontmaps_zip.exists():
        with open(fontmaps_zip, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 512), b""):
                digest.update(b"|FONTS|")
                digest.update(chunk)
    else:
        digest.update(b"|FONTS|NONE")
    return digest.hexdigest()


def rewrite_conf_imports_to_default(conf_path: Path, default_conf: Path) -> bool:
    target_uri = default_conf.resolve().as_uri()
    changed = False
    try:
        from xml.etree import ElementTree as element_tree

        tree = element_tree.parse(conf_path)
        root = tree.getroot()
        for element in root.iter():
            tag = element.tag
            if isinstance(tag, str) and tag.endswith("import"):
                href = (element.get("href") or "").strip()
                if href and "://" not in href and href.lower().endswith("conf.xml"):
                    element.set("href", target_uri)
                    changed = True
        if changed:
            tree.write(conf_path, encoding="utf-8", xml_declaration=True)
            return True
    except Exception:
        pass
    try:
        text = conf_path.read_text(encoding="utf-8", errors="ignore")
        replaced = (
            text.replace('href="conf.xml"', f'href="{target_uri}"')
            .replace("href='conf.xml'", f"href='{target_uri}'")
        )
        if replaced != text:
            conf_path.write_text(replaced, encoding="utf-8")
            return True
    except Exception:
        pass
    return False
