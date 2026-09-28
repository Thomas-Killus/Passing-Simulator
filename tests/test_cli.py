import json

from sim.cli import main


def test_exports_json_and_reports_success(tmp_path, capsys):
    out = tmp_path / "pattern.json"
    code = main(["patterns/6c-4count.txt", "--json", str(out), "--no-serve"])
    assert code == 0
    doc = json.loads(out.read_text())
    assert doc["report"]["ok"] is True
    assert "6 clubs" in capsys.readouterr().out


def test_reports_failure_for_a_broken_pattern(tmp_path, capsys):
    broken = tmp_path / "broken.txt"
    broken.write_text("""
name: broken
beat: 0.35
jugglers:
  A at (0, 0)
start:
  A: R=1 L=0
loop:
  A: 3
""")
    code = main([str(broken), "--no-serve"])
    assert code == 1
    assert "empty" in capsys.readouterr().out


def test_reports_notation_errors_without_a_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.txt"
    bad.write_text("name: bad\nbeat: 0.35\njugglers:\n  A at (0,0)\nstart:\n"
                   "  A: R=1 L=0\nloop:\n  A: 3pZZ\n")
    assert main([str(bad), "--no-serve"]) == 1
    assert "ZZ" in capsys.readouterr().out


def test_a_repeating_failure_is_summarised_not_printed_once_per_beat(tmp_path, capsys):
    broken = tmp_path / "collide.txt"
    broken.write_text("""
name: collide
beat: 0.35
jugglers:
  A at (0, 0)
  B at (0, -2)
start:
  A: R=2 L=1
  B: R=2 L=1
loop:
  A: 4pB 3
  B: 4pA 3
""")
    main([str(broken), "--no-serve"])
    lines = [l for l in capsys.readouterr().out.splitlines() if "ERROR" in l]
    assert len(lines) <= 8
    assert any("more" in l for l in capsys.readouterr().out.splitlines() + lines)


def test_the_report_says_line_or_cross_for_each_pass(tmp_path, capsys):
    main(["patterns/6c-4count.txt", "--no-serve"])
    assert "LINE" in capsys.readouterr().out


def test_the_report_flags_a_wrong_handedness_annotation(tmp_path, capsys):
    bad = tmp_path / "bad.txt"
    bad.write_text("""
name: wrong annotation
beat: 0.32
jugglers:
  A at (0, 1.75)
  B at (0, -1.75)
start:
  A: R=2 L=2
  B: R=2 L=1
loop:
  A: 4pB line 3
  B: 3 4pA
""")
    assert main([str(bad), "--no-serve"]) == 1
    out = capsys.readouterr().out
    assert "CROSS" in out and "start_hand" in out
