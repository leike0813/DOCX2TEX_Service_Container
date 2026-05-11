from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET


XML2TEX_NS = "http://transpect.io/xml2tex"
DBK_NS = "http://docbook.org/ns/docbook"
CSS_NS = "http://www.w3.org/1996/css"
ROLE_SINGLE_RE = re.compile(r"@role\s*=\s*(['\"])([^'\"]+)\1")
ROLE_LIST_RE = re.compile(r"@role\s*=\s*\(([^)]+)\)", re.DOTALL)


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")
    )


def parse_style_map(style_str: str | None) -> dict[str, List[str]]:
    result: dict[str, List[str]] = {}
    if not style_str:
        return result
    try:
        parsed = json.loads(style_str)
    except Exception:
        return result
    if not isinstance(parsed, dict):
        return result
    for key, value in parsed.items():
        if isinstance(value, str):
            values = [value.strip()] if value.strip() else []
        elif isinstance(value, list):
            values = [str(item).strip() for item in value if str(item).strip()]
        else:
            values = []
        if values:
            result[key] = list(dict.fromkeys(values))
    return result


def _roles_from_context(context: str) -> set[str]:
    roles: set[str] = set()
    for match in ROLE_LIST_RE.finditer(context):
        for part in match.group(1).split(","):
            value = part.strip().strip("\"'").strip()
            if value:
                roles.add(value)
    for match in ROLE_SINGLE_RE.finditer(context):
        value = match.group(2).strip()
        if value:
            roles.add(value)
    return roles


def extract_role_cmds(conf_paths: list[Path]) -> dict[str, str]:
    role_cmds: dict[str, str] = {}
    for path in conf_paths:
        if not path.exists():
            continue
        try:
            root = ET.parse(str(path)).getroot()
            for template in root.findall(f".//{{{XML2TEX_NS}}}template"):
                context = template.get("context") or ""
                if "dbk:para" not in context:
                    continue
                matched_roles = _roles_from_context(context)
                if not matched_roles:
                    continue
                for rule in template.findall(f".//{{{XML2TEX_NS}}}rule"):
                    if (rule.get("type") or "").strip() != "cmd":
                        continue
                    name = (rule.get("name") or "").strip()
                    if not name:
                        break
                    for role in matched_roles:
                        role_cmds[role] = name
                    break
        except Exception:
            continue
    return role_cmds


def build_evolve_snippet(style_map: dict[str, List[str]]) -> str:
    if not style_map:
        return ""
    lines: list[str] = ["  <!-- style-map preprocess: visible-name lists and normalization -->"]
    for key, values in style_map.items():
        vals = ",".join("'" + _xml_escape(value) + "'" for value in values)
        lines.append(
            f"  <xsl:variable name=\"{key}-visible\" as=\"xs:string*\" select=\"({vals})\"/>"
        )
    for key in style_map:
        lines.append(
            "  <xsl:variable name=\"%s-roles\" as=\"xs:string*\"\n"
            "    select=\"(/*//*[local-name()='rule' and namespace-uri()='%s'][@native-name = $%s-visible]/(@name|@role),\n"
            "              /*//*[local-name()='style' and namespace-uri()='%s'][@native-name = $%s-visible]/(@name|@role)) ! normalize-space(.)\"/>"
            % (key, CSS_NS, key, XML2TEX_NS, key)
        )
    for key in style_map:
        lines.append(
            "  <xsl:template match=\"*[@role][local-name()='para' and namespace-uri()='%s'][@role=$%s-roles]\" mode=\"docx2tex-preprocess\">\n"
            "    <xsl:copy>\n"
            "      <xsl:apply-templates select=\"@* except @role\" mode=\"#current\"/>\n"
            "      <xsl:attribute name=\"role\">%s</xsl:attribute>\n"
            "      <xsl:apply-templates mode=\"#current\"/>\n"
            "    </xsl:copy>\n"
            "  </xsl:template>"
            % (DBK_NS, key, key)
        )
    lines.append(
        "  <xsl:template match=\"*[(local-name() = 'hub') and (namespace-uri() = '%s')]\" mode=\"docx2tex-preprocess\">\n"
        "    <xsl:copy>\n"
        "      <xsl:apply-templates select=\"@*\" mode=\"#current\"/>\n"
        "      <xsl:attribute name=\"data-custom-evolve\">1</xsl:attribute>\n"
        % DBK_NS
    )
    for alias in style_map:
        lines.append(
            (
                "      <xsl:variable name=\"n-{a}\" select=\"${a}-roles[1]\"/>\n"
                "      <xsl:if test=\"$n-{a}\">\n"
                "        <xsl:variable name=\"orig-{a}\" select=\"(/*//*[local-name()='rule' and namespace-uri()='{css}'][@name=$n-{a}] | "
                "/*//*[local-name()='style' and namespace-uri()='{xml2tex}'][@name=$n-{a}])[1]\"/>\n"
                "        <xsl:if test=\"$orig-{a} and not(/*//*[local-name()='rule' and namespace-uri()='{css}'][@name='{a}'] | "
                "/*//*[local-name()='style' and namespace-uri()='{xml2tex}'][@name='{a}'])\">\n"
                "          <xsl:choose>\n"
                "            <xsl:when test=\"local-name($orig-{a})='rule'\">\n"
                "              <xsl:element name=\"rule\" namespace=\"{css}\">\n"
                "                <xsl:copy-of select=\"$orig-{a}/@* except $orig-{a}/@name\"/>\n"
                "                <xsl:attribute name=\"name\">{a}</xsl:attribute>\n"
                "                <xsl:copy-of select=\"$orig-{a}/node()\"/>\n"
                "              </xsl:element>\n"
                "            </xsl:when>\n"
                "            <xsl:otherwise>\n"
                "              <xsl:element name=\"style\" namespace=\"{xml2tex}\">\n"
                "                <xsl:copy-of select=\"$orig-{a}/@* except ($orig-{a}/@name, $orig-{a}/@role)\"/>\n"
                "                <xsl:attribute name=\"name\">{a}</xsl:attribute>\n"
                "                <xsl:attribute name=\"role\">{a}</xsl:attribute>\n"
                "                <xsl:copy-of select=\"$orig-{a}/node()\"/>\n"
                "              </xsl:element>\n"
                "            </xsl:otherwise>\n"
                "          </xsl:choose>\n"
                "        </xsl:if>\n"
                "      </xsl:if>\n"
            ).format(a=alias, css=CSS_NS, xml2tex=XML2TEX_NS)
        )
    lines.extend(
        [
            "      <xsl:apply-templates mode=\"#current\"/>",
            "    </xsl:copy>",
            "  </xsl:template>",
        ]
    )
    return "\n".join(lines) + "\n"


def build_output_snippet(role_cmds: dict[str, str], style_map: dict[str, List[str]]) -> str:
    roles = [role for role in style_map if role in role_cmds]
    if not roles:
        return ""
    lines = [
        "  <!-- headlines direct output from StyleMap + conf mapping (via PI 'latex' to avoid escaping) -->"
    ]
    for role in roles:
        command = role_cmds[role]
        lines.append(
            "  <xsl:template match=\"*[@role='%s'][local-name()='para' and namespace-uri()='%s']\" mode=\"docx2tex-postprocess\">\n"
            "    <xsl:text>&#10;</xsl:text>\n"
            "    <xsl:processing-instruction name=\"latex\">\\%s{{</xsl:processing-instruction>\n"
            "    <xsl:apply-templates mode=\"#current\"/>\n"
            "    <xsl:processing-instruction name=\"latex\">}</xsl:processing-instruction>\n"
            "    <xsl:text>&#10;&#10;</xsl:text>\n"
            "  </xsl:template>"
            % (role, DBK_NS, command)
        )
    return "\n".join(lines) + "\n"


EVOLVE_SKELETON = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  exclude-result-prefixes="#all">
  <xsl:import href="http://transpect.io/docx2tex/xsl/evolve-hub-driver.xsl"/>
  <xsl:template match="/" mode="docx2tex-preprocess"><xsl:next-match/></xsl:template>
</xsl:stylesheet>
"""


def merge_or_create_xsl(
    base_path: Path | None,
    snippet: str,
    out_path: Path,
    skeleton: str,
) -> Path | None:
    if not snippet.strip():
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path and base_path.exists():
        text = base_path.read_text(encoding="utf-8", errors="ignore")
        merged = (
            text.replace("</xsl:stylesheet>", snippet + "\n</xsl:stylesheet>")
            if "</xsl:stylesheet" in text
            else text + "\n" + snippet
        )
        out_path.write_text(merged, encoding="utf-8")
    else:
        out_path.write_text(
            skeleton.replace("</xsl:stylesheet>", snippet + "\n</xsl:stylesheet>"),
            encoding="utf-8",
        )
    return out_path


def prepare_effective_xsls(
    style_str: str | None,
    conf_paths: list[Path],
    user_custom_evolve: Path | None,
    work_dir: Path,
) -> tuple[Path | None, dict[str, List[str]], dict[str, str]]:
    role_cmds = extract_role_cmds(conf_paths)
    style_map = parse_style_map(style_str)
    combined = build_evolve_snippet(style_map) + build_output_snippet(role_cmds, style_map)
    effective_evolve = merge_or_create_xsl(
        user_custom_evolve,
        combined,
        work_dir / "custom-evolve-effective.xsl",
        EVOLVE_SKELETON,
    )
    try:
        role_cmds_filtered = {role: role_cmds[role] for role in style_map if role in role_cmds}
        style_cmds = {
            name: role_cmds[role]
            for role, names in style_map.items()
            if role in role_cmds
            for name in names
        }
        (work_dir / "stylemap_manifest.json").write_text(
            json.dumps(
                {
                    "role_cmds": role_cmds,
                    "role_cmds_filtered": role_cmds_filtered,
                    "style_cmds": style_cmds,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass
    return effective_evolve, style_map, role_cmds
