from __future__ import annotations

import ast
import itertools
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _local_imports(module_name: str) -> set[str]:
    path = ROOT / "rulespace_v3" / f"{module_name}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("rulespace_v3."):
                    imports.add(alias.name.split(".", 2)[1])
    return imports


class V3M0ImportDagTests(unittest.TestCase):
    def test_task10_import_dag_has_no_ablation_dynamics_cycle(self):
        self.assertNotIn("dynamics", _local_imports("ablation"))
        self.assertNotIn("ablation", _local_imports("dynamics"))
        self.assertIn("prestructure", _local_imports("dynamics"))
        self.assertIn("ablation", _local_imports("prestructure"))
        self.assertIn("registry", _local_imports("prestructure"))
        self.assertIn("ablation", _local_imports("qualification"))
        self.assertIn("dynamics", _local_imports("qualification"))

    def test_fresh_interpreter_import_permutations_have_no_registration(self):
        modules = (
            "rulespace_v3.ablation",
            "rulespace_v3.dynamics",
            "rulespace_v3.qualification",
        )
        for order in itertools.permutations(modules):
            script = (
                "import importlib\n"
                f"mods={order!r}\n"
                "loaded=[importlib.import_module(name) for name in mods]\n"
                "q=importlib.import_module('rulespace_v3.qualification')\n"
                "assert not hasattr(q, 'qualify_ablation_from_certificate')\n"
            )
            result = subprocess.run(
                (sys.executable, "-c", script),
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=result.stdout + result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
