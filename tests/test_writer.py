from apps.writer.main import process_task


def test_format_report_task():
    response = process_task("format-report", "Research note with facts")
    assert response["status"] == "success"
    assert "REPORT" in response["result"]


def test_unknown_capability_is_rejected():
    response = process_task("not-supported", "Research note")
    assert response["status"] == "error"
    assert "supported" in response["message"].lower()
