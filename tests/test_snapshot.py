from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import xingjian

def test_snapshot_maps_each_py_file_to_its_mtime(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n")
    result = xingjian.snapshot(tmp_path)
    assert result == {
        tmp_path / "a.py": 
        (tmp_path / "a.py").stat().st_mtime_ns
    }
