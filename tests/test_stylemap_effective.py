from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.core.stylemap import prepare_effective_xsls


def test_stylemap_prepares_effective_evolve_xsl():
    """Ensure stylemap + conf generate an effective evolve driver."""
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        conf = Path('conf') / 'conf-ctexbook-zh.xml'
        assert conf.exists(), f'missing conf: {conf}'

        style = {'Title': 'Main Title', 'Heading1': 'Level 1 Heading'}
        ee, style_map, role_cmds = prepare_effective_xsls(
            json.dumps(style, ensure_ascii=False),
            [conf],
            user_custom_evolve=None,
            work_dir=work,
        )

        assert ee is not None and ee.exists(), 'effective evolve XSL not created'
        text = ee.read_text(encoding='utf-8')
        assert 'evolve-hub-driver.xsl' in text or 'docx2tex-preprocess' in text
        assert any(k in style_map for k in ('Title', 'Heading1'))
        assert set(role_cmds.keys()).issuperset(style_map.keys())


def test_stylemap_prefers_later_conf_entries():
    """Later conf files override earlier ones for role command mapping."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        base_conf = td_path / 'base.xml'
        user_conf = td_path / 'user.xml'
        base_conf.write_text(
            """
<set xmlns='http://transpect.io/xml2tex'>
  <template context="dbk:para[@role='Heading1']">
    <rule type="cmd" name="chapter"/>
  </template>
</set>
""".strip(),
            encoding='utf-8',
        )
        user_conf.write_text(
            """
<set xmlns='http://transpect.io/xml2tex'>
  <template context="dbk:para[@role='Heading1']">
    <rule type="cmd" name="section"/>
  </template>
</set>
""".strip(),
            encoding='utf-8',
        )

        style = {'Heading1': 'Level 1 Heading'}
        ee, style_map, role_cmds = prepare_effective_xsls(
            json.dumps(style, ensure_ascii=False),
            [base_conf, user_conf],
            user_custom_evolve=None,
            work_dir=td_path,
        )

        assert role_cmds.get('Heading1') == 'section', 'later conf should override earlier definitions'
        assert list(style_map.keys()) == ['Heading1']
        assert ee is not None and ee.exists()
