from pathlib import Path

import app


def test_app_package_importable():
    assert app.__doc__


def test_fixtures_dir_exists(fixtures_dir: Path):
    assert fixtures_dir.is_dir()
