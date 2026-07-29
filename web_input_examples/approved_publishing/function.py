def analyze_data(id, path):
    import datetime
    import pathlib

    report_path = pathlib.PurePosixPath(path) / "report.pdf"
    # ...analyze the data, create the report and write it to `report_path`...

    return {
        "title": "Report title",
        "date": str(datetime.date.today()),
        "low": 2,
        "high": 7,
        "std_dev": 1,
        "confidence": 97,
        "report_path": str(report_path),
    }
