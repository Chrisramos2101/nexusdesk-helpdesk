"""Lightweight source/UI guarantees for the recruiter-only final consistency pass."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_recruiter_gateway_keeps_csrf_and_two_role_forms():
    text = (ROOT / 'templates' / 'recruiter_demo.html').read_text(encoding='utf-8')
    assert 'ND-RECRUITER-CONSISTENCY-V1' in text
    assert text.count("url_for('recruiter_demo.enter')") == 2
    assert text.count('name="csrf_token"') == 2
    assert 'value="admin"' in text and 'value="employee"' in text
    assert 'Read-only demo' in text


def test_recruiter_only_panels_are_conditioned_on_session():
    text = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert 'ND-RECRUITER-CONSISTENCY-V1' in text
    assert "{% if session.get('recruiter_demo') %}" in text
    assert 'nd-workflow-guide' in text
    assert 'nd-preview-workflow' in text
    assert 'nd-disabled-feature' in text
    assert 'action="/submit"' in text  # The original production form is retained.


def test_recruiter_css_scopes_change_to_preview_only():
    text = (ROOT / 'static' / 'recruiter_ui.css').read_text(encoding='utf-8')
    assert 'ND-RECRUITER-CONSISTENCY-V1' in text
    for selector in ('.nd-workflow-guide', '.nd-preview-workflow', '.nd-disabled-feature'):
        assert 'body.nexusdesk-recruiter-preview ' + selector in text


def test_production_auth_and_database_guards_are_still_present():
    guard = (ROOT / 'services' / 'recruiter_demo_guard.py').read_text(encoding='utf-8')
    assert 'DEMO_DATABASE_NAME' in guard
    assert 'DEMO_DATABASE_USER' in guard
    assert 'RECRUITER_STRICT_ENDPOINTS' in guard
