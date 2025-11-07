import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from xml.etree import ElementTree as ET


XML2TEX_NS = "http://transpect.io/xml2tex"
DBK_NS = "http://docbook.org/ns/docbook"
CSS_NS = "http://www.w3.org/1996/css"


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")
    )


def parse_style_map(style_str: Optional[str]) -> Dict[str, List[str]]:
    """Parse the user-provided JSON StyleMap.
    Returns role->list of visible names (strings) limited to accepted roles.
    """
    roles = {"Title", "Heading1", "Heading2", "Heading3"}
    result: Dict[str, List[str]] = {}
    if not style_str:
        return result
    try:
        obj = json.loads(style_str)
        if not isinstance(obj, dict):
            return {}
        for k, v in obj.items():
            if k not in roles:
                continue
            if isinstance(v, str):
                vals = [v.strip()] if v.strip() else []
            elif isinstance(v, list):
                vals = [str(x).strip() for x in v if str(x).strip()]
            else:
                vals = []
            if vals:
                # de-dup while preserving order
                seen = set()
                uniq = []
                for s in vals:
                    if s not in seen:
                        uniq.append(s)
                        seen.add(s)
                result[k] = uniq
    except Exception:
        return {}
    return result


def extract_role_cmds(conf_paths: List[Path]) -> Dict[str, str]:
    """Extract role->TeX command mapping from provided xml2tex conf files.
    Reads files in order; later files override earlier ones for the same role.
    Only captures roles in {Title, Heading1, Heading2, Heading3}.
    """
    wanted_roles = ["Title", "Heading1", "Heading2", "Heading3"]
    role_cmd: Dict[str, str] = {}
    for p in conf_paths:
        if not p or not p.exists():
            continue
        try:
            tree = ET.parse(str(p))
            root = tree.getroot()
            # template elements reside in XML2TEX_NS
            for tpl in root.findall(f".//{{{XML2TEX_NS}}}template"):
                ctx = tpl.get("context") or ""
                if "dbk:para" not in ctx:
                    continue
                # quick filter: check any role token string is present
                matched_role: Optional[str] = None
                for r in wanted_roles:
                    # Look for quoted token occurrences e.g. 'Heading1' or "Heading1"
                    if re.search(r"['\"]%s['\"]" % re.escape(r), ctx):
                        matched_role = r
                        break
                if not matched_role:
                    continue
                # find first rule with type=cmd and take its name
                for rule in tpl.findall(f".//{{{XML2TEX_NS}}}rule"):
                    if (rule.get("type") or "").strip() == "cmd":
                        name = (rule.get("name") or "").strip()
                        if name:
                            role_cmd[matched_role] = name
                        break
        except Exception:
            continue
    return role_cmd


def build_evolve_snippet(style_map: Dict[str, List[str]]) -> str:
    if not style_map:
        return ""
    # Build variables for visible names and role sets
    lines: List[str] = []
    lines.append("  <!-- style-map preprocess: visible-name lists and normalization -->")
    # visible lists
    for key, values in style_map.items():
        vals = ",".join("'" + _xml_escape(v) + "'" for v in values)
        lines.append(
            f"  <xsl:variable name=\"{key}-visible\" as=\"xs:string*\" select=\"({vals})\"/>"
        )
    # roles lookup via native-name matching (css:rule and dbk:style)
    for key in style_map.keys():
        lines.append(
            "  <xsl:variable name=\"%s-roles\" as=\"xs:string*\"\n"
            "    select=\"(/*//*[local-name()='rule' and namespace-uri()='%s'][@native-name = $%s-visible]/(@name|@role),\n"
            "              /*//*[local-name()='style' and namespace-uri()='%s'][@native-name = $%s-visible]/(@name|@role)) ! normalize-space(.)\"/>"
            % (key, CSS_NS, key, XML2TEX_NS, key)
        )
    # para role rewrite templates
    for key in style_map.keys():
        lines.append(
            "  <xsl:template match=\"*[@role][local-name()='para' and namespace-uri()='%s'][@role=$%s-roles]\" mode=\"docx2tex-preprocess\">\n"
            "    <xsl:copy>\n"
            "      <xsl:apply-templates select=\"@* except @role\" mode=\"#current\"/>\n"
            "      <xsl:attribute name=\"role\">%s</xsl:attribute>\n"
            "      <xsl:apply-templates mode=\"#current\"/>\n"
            "    </xsl:copy>\n"
            "  </xsl:template>" % (DBK_NS, key, key)
        )
    # Inject alias clones inside hub (avoid top-level xsl:if)
    lines.append(
        "  <xsl:template match=\"*[(local-name() = 'hub') and (namespace-uri() = '%s')]\" mode=\"docx2tex-preprocess\">\n"
        "    <xsl:copy>\n"
        "      <xsl:apply-templates select=\"@*\" mode=\"#current\"/>\n"
        "      <xsl:attribute name=\"data-custom-evolve\">1</xsl:attribute>\n"
        % DBK_NS
    )
    def alias_block(alias: str) -> str:
        return (
            "      <xsl:variable name=\"n-{a}\" select=\"${a}-roles[1]\"/>\n"
            "      <xsl:if test=\"$n-{a}\">\n"
            "        <xsl:variable name=\"orig-{a}\" select=\"(/*//*[local-name()='rule' and namespace-uri()='{css}'][@name=$n-{a}] | /*//*[local-name()='style' and namespace-uri()='{xml2tex}'][@name=$n-{a}])[1]\"/>\n"
            "        <xsl:if test=\"$orig-{a} and not(/*//*[local-name()='rule' and namespace-uri()='{css}'][@name='{a}'] | /*//*[local-name()='style' and namespace-uri()='{xml2tex}'][@name='{a}'])\">\n"
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
    for alias in ["Title", "Heading1", "Heading2", "Heading3"]:
        lines.append(alias_block(alias))
    lines.append("      <xsl:apply-templates mode=\"#current\"/>")
    lines.append("    </xsl:copy>")
    lines.append("  </xsl:template>")
    return "\n".join(lines) + "\n"


def build_output_snippet(role_cmd: Dict[str, str], style_roles: List[str]) -> str:
    # Only generate for intersection of parsed roles and style roles
    roles = [r for r in ["Title", "Heading1", "Heading2", "Heading3"] if r in role_cmd and r in style_roles]
    if not roles:
        return ""
    lines = []
    lines.append("  <!-- headlines direct output from StyleMap + conf mapping (via PI 'latex' to avoid escaping) -->")
    for r in roles:
        cmd = role_cmd[r]
        # open/close via processing-instruction('latex') so xml2tex outputs raw TeX
        open_cmd = f"\\{cmd}{{"
        lines.append(
            "  <xsl:template match=\"*[@role='%s'][local-name()='para' and namespace-uri()='%s']\" mode=\"docx2tex-postprocess\">\n"
            "    <xsl:processing-instruction name=\"latex\">%s</xsl:processing-instruction>\n"
            "    <xsl:apply-templates mode=\"#current\"/>\n"
            "    <xsl:processing-instruction name=\"latex\">}</xsl:processing-instruction>\n"
            "  </xsl:template>" % (r, DBK_NS, open_cmd)
        )
    return "\n".join(lines) + "\n"


EVOLVE_SKELETON = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xsl:stylesheet version=\"2.0\"
  xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\"
  xmlns:xs=\"http://www.w3.org/2001/XMLSchema\"
  exclude-result-prefixes=\"#all\">
  <xsl:import href=\"http://transpect.io/docx2tex/xsl/evolve-hub-driver.xsl\"/>
  <xsl:template match=\"/\" mode=\"docx2tex-preprocess\"><xsl:next-match/></xsl:template>
</xsl:stylesheet>
"""


OUTPUT_SKELETON = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xsl:stylesheet version=\"2.0\"
  xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\"
  exclude-result-prefixes=\"#all\">
</xsl:stylesheet>
"""


def merge_or_create_xsl(base_path: Optional[Path], snippet: str, out_path: Path, skeleton: str) -> Optional[Path]:
    if not snippet.strip():
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path and base_path.exists():
        try:
            txt = base_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            txt = ""
        if "</xsl:stylesheet" in txt:
            merged = txt.replace("</xsl:stylesheet>", snippet + "\n</xsl:stylesheet>")
        else:
            merged = txt + "\n" + snippet
        out_path.write_text(merged, encoding="utf-8")
    else:
        # create skeleton
        out_path.write_text(skeleton.replace("</xsl:stylesheet>", snippet + "\n</xsl:stylesheet>"), encoding="utf-8")
    return out_path


def prepare_effective_xsls(
    style_str: Optional[str],
    conf_paths: List[Path],
    user_custom_evolve: Optional[Path],
    user_custom_xsl: Optional[Path],
    work_dir: Path,
) -> Tuple[Optional[Path], Optional[Path], Dict[str, List[str]], Dict[str, str]]:
    """Return (effective_evolve, effective_custom_xsl, style_map, role_cmds)."""
    style_map = parse_style_map(style_str)
    role_cmds: Dict[str, str] = extract_role_cmds(conf_paths)
    evolve_snippet = build_evolve_snippet(style_map)
    # generate command-injection snippet for roles present both in style_map and role_cmds
    output_snippet = build_output_snippet(role_cmds, list(style_map.keys()))
    effective_evolve: Optional[Path] = None
    effective_custom: Optional[Path] = None
    combined = (evolve_snippet or "") + (output_snippet or "")
    if combined.strip():
        effective_evolve = merge_or_create_xsl(
            user_custom_evolve, combined, work_dir / "custom-evolve-effective.xsl", EVOLVE_SKELETON
        )
    # No separate output-layer XSL needed when we inline into evolve driver
    effective_custom = None
    return effective_evolve, effective_custom, style_map, role_cmds
