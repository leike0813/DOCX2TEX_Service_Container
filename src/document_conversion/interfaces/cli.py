from __future__ import annotations

import argparse
import os
import shutil
import sys

from document_conversion.infrastructure.config import get_config


def _check_binary(name: str) -> dict[str, object]:
    path = shutil.which(name)
    return {"name": name, "available": path is not None, "path": path or ""}


def check_system() -> int:
    cfg = get_config()
    checks = [
        _check_binary("java"),
        _check_binary("inkscape"),
        _check_binary("pandoc"),
        _check_binary("pandoc-tex-numbering"),
    ]
    checks.append(
        {
            "name": "DOCX2TEX_HOME",
            "available": cfg.docx2tex_home.exists(),
            "path": str(cfg.docx2tex_home),
        }
    )
    checks.append(
        {
            "name": "XML_CATALOG_FILES",
            "available": cfg.catalog_file.exists(),
            "path": str(cfg.catalog_file),
        }
    )
    for item in checks:
        flag = "OK" if item["available"] else "MISSING"
        print(f"[{flag}] {item['name']}: {item['path']}")
    return 0 if all(bool(item["available"]) for item in checks) else 1


def serve(reload: bool = False) -> int:
    import uvicorn

    uvicorn.run(
        "document_conversion.interfaces.api.app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=reload,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="document-conversion")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-system")
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "check-system":
        return check_system()
    if args.command == "serve":
        return serve(reload=bool(args.reload))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
