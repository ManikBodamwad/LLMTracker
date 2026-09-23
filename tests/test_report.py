from click.testing import CliRunner

from llmtrack.report.alerts import AlertManager
from llmtrack.report.cli import main, print_report
from llmtrack.report.html import generate_html_report
from llmtrack.storage.memory import MemoryStorage
from llmtrack.storage.sqlite import SQLiteStorage
from llmtrack.tracker import CostTracker


def test_print_report_outputs():
    # Empty
    print_report([])

    # Populated
    tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
    with tracker.feature("summarization"):
        tracker.log_call("gpt-4o", 500, 200)
    events = tracker.storage.query(days=7)
    print_report(events, days=7)


def test_generate_html_report(tmp_path):
    tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
    with tracker.feature("feature_x"):
        tracker.log_call("gpt-4o", 1000, 500)
    with tracker.feature("feature_y"):
        tracker.log_call("claude-sonnet-4-5", 2000, 800)

    events = tracker.storage.query(days=7)
    html_file = tmp_path / "sub" / "report.html"
    generate_html_report(events, filepath=html_file, days=7)

    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "feature_x" in content
    assert "feature_y" in content
    assert "llmtrack Cost Report" in content


def test_alert_manager_and_callback():
    storage = MemoryStorage()
    triggered = []

    def my_callback(feat, spent, limit):
        triggered.append((feat, spent, limit))

    AlertManager.register(
        storage=storage,
        feature="expensive_feature",
        daily_limit_usd=0.01,
        callback=my_callback,
    )

    tracker = CostTracker(storage=storage, auto_patch=False)
    with tracker.feature("expensive_feature"):
        # 10,000 input & 5,000 output tokens on gpt-4 = (10000/1M)*30 + (5000/1M)*60 = $0.30 + $0.30 = $0.60 > $0.01
        tracker.log_call("gpt-4", 10_000, 5_000)

    res = AlertManager.check_all()
    assert len(res) == 1
    assert res[0]["feature"] == "expensive_feature"
    assert len(triggered) == 1
    assert triggered[0][0] == "expensive_feature"


def test_cli_report_and_clear(tmp_path):
    runner = CliRunner()
    db_file = tmp_path / "cli_test.db"

    # Setup some data in sqlite db
    storage = SQLiteStorage(db_path=db_file)
    tracker = CostTracker(storage=storage, auto_patch=False)
    with tracker.feature("cli_feature"):
        tracker.log_call("gpt-4o", 500, 200)

    # Test report command (terminal)
    res = runner.invoke(main, ["report", "--db", str(db_file), "--days", "7"])
    assert res.exit_code == 0
    assert "cli_feature" in res.output

    # Test report command (html)
    out_html = tmp_path / "cli_out.html"
    res_html = runner.invoke(
        main,
        ["report", "--db", str(db_file), "--html", "--output", str(out_html)],
    )
    assert res_html.exit_code == 0
    assert out_html.exists()

    # Test clear command
    res_clear = runner.invoke(main, ["clear", "--db", str(db_file)])
    assert res_clear.exit_code == 0
    assert "Database cleared" in res_clear.output
    assert storage.query(days=7) == []
