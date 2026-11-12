from pathlib import Path

def test_recruiter_final_context_files():
    nav=Path('templates/_recruiter_demo_nav.html').read_text(encoding='utf-8')
    assert "session.get('username'" in nav
    assert 'Switch role</a>' not in nav
    assert 'Portfolio demo</span>' not in nav
    source=Path('routes/recruiter_demo.py').read_text(encoding='utf-8')
    assert 'if expected_role == "admin":\n        return redirect("/")' in source
    bar=Path('templates/_production_context_bar.html').read_text(encoding='utf-8')
    assert "not session.get('recruiter_demo')" in bar
    assert 'Viewing as' in bar
    assert 'read-only' not in bar.lower()
