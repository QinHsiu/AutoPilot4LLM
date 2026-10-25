from pathlib import Path

from prompt.evolve import EvolveResult, exit_code, main


def test_exit_code_map():
    failed = EvolveResult(None, None, None, "seed_score_failed", "runs/x")
    done = EvolveResult(None, 1, 0.25, "no_improvement", "runs/x")
    assert exit_code(failed) == 1
    assert exit_code(done) == 0


def test_cli_preflight_and_docs(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("base_url: http://example.invalid/v1\nmodel: demo\n", encoding="utf-8")
    code = main(["--task", "clean", "--method", "nope", "--config", str(config)])
    assert code == 1
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "python -m prompt.evolve --task distill --method zero_shot --config config.yaml" in readme
    assert "`train` 与 `eval` 尚未实现。" in readme
    assert "/runs" in (root / ".gitignore").read_text(encoding="utf-8")
