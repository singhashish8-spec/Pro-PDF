from app.persistence.recent_files import add_recent_file, clear_recent_files, get_recent_files
from app.ui.dashboard.home_dashboard import HomeDashboard
from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager
from app.ui.theme.tokens import DARK, LIGHT, build_qss


def test_theme_qss_builds_for_both_tokens():
    assert "background-color" in build_qss(LIGHT)
    assert "background-color" in build_qss(DARK)


def test_theme_manager_toggle(qapp):
    manager = ThemeManager(qapp)
    manager.set_theme("light")
    assert manager.current.name == "light"
    manager.toggle()
    assert manager.current.name == "dark"


def test_recent_files_roundtrip():
    clear_recent_files()
    add_recent_file("/tmp/a.pdf")
    add_recent_file("/tmp/b.pdf")
    assert get_recent_files() == ["/tmp/b.pdf", "/tmp/a.pdf"]
    clear_recent_files()


def test_dashboard_constructs(qapp):
    dashboard = HomeDashboard()
    assert dashboard.objectName() == "Dashboard"


def test_main_window_constructs(qapp):
    manager = ThemeManager(qapp)
    window = MainWindow(manager)
    assert window.windowTitle() == "PDF Pro"
