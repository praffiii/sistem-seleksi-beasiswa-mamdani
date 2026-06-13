import matplotlib

matplotlib.use("Agg")

from streamlit.testing.v1 import AppTest


def test_app_runs_without_exception():
    app = AppTest.from_file("streamlit_app.py").run(timeout=60)
    assert not app.exception
