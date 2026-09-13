from __future__ import annotations

import argparse
import ast
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_SOURCE = REPOSITORY_ROOT / "packages" / "contracts" / "openapi-v2.yaml"
PYTHON_DESTINATION = (
    REPOSITORY_ROOT
    / "packages"
    / "wuji-core"
    / "src"
    / "wuji_core"
    / "contracts"
    / "generated.py"
)
TYPESCRIPT_DESTINATION = (
    REPOSITORY_ROOT / "packages" / "contracts" / "src" / "v2" / "generated.ts"
)
PNPM = REPOSITORY_ROOT / "work" / "toolchain" / "bin" / "pnpm"


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def _generate_python(destination: Path) -> None:
    executable = shutil.which("datamodel-codegen")
    if executable is None:
        raise RuntimeError(
            "datamodel-codegen is unavailable; run scripts/vnext/uv.sh sync --frozen"
        )
    _run(
        [
            executable,
            "--input",
            str(OPENAPI_SOURCE),
            "--input-file-type",
            "openapi",
            "--schema-version",
            "3.1",
            "--schema-version-mode",
            "strict",
            "--strict-refs",
            "--output",
            str(destination),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.13",
            "--target-pydantic-version",
            "2.12",
            "--use-annotated",
            "--use-union-operator",
            "--use-standard-collections",
            "--use-specialized-enum",
            "--enum-field-as-literal",
            "one",
            "--extra-fields",
            "forbid",
            "--strict-types",
            "str",
            "int",
            "float",
            "bool",
            "--generate-schema-validators",
            "--formatters",
            "builtin",
            "--disable-timestamp",
            "--enable-generated-header-marker",
            "--keep-model-order",
        ]
    )
    _executor_receipt_runtime_validator(destination)


def _executor_receipt_runtime_validator(destination: Path) -> None:
    """Preserve this source schema's oneOf when codegen flattens its branches.

    All names/types below come from OpenAPI. Bounds and native bytes validation
    remain in the generated fields/domain consumer; no datetime is re-encoded.
    """
    schema = yaml.safe_load(OPENAPI_SOURCE.read_text())["components"]["schemas"].get(
        "ExecutorReceiptResponse"
    )
    if schema is None:
        return
    branches = []
    for branch in schema["oneOf"]:
        if set(branch) != {"properties"}:
            raise ValueError("ExecutorReceiptResponse oneOf shape requires integration")
        fields = []
        for name, rule in branch["properties"].items():
            if set(rule) != {"type"} or rule["type"] not in {"null", "string"}:
                raise ValueError("unsupported ExecutorReceiptResponse oneOf rule")
            if name not in schema["required"]:
                raise ValueError("ExecutorReceiptResponse oneOf field must be required")
            fields.append((name, rule["type"]))
        branches.append(tuple(fields))
    source = destination.read_text()
    target = next(node for node in ast.parse(source).body
                  if isinstance(node, ast.ClassDef) and node.name == "ExecutorReceiptResponse")
    method = f'''
    @_executor_model_validator(mode="after")
    def _validate_source_one_of(self):
        branches = {tuple(branches)!r}
        value = self.root
        matches = 0
        for branch in branches:
            valid = True
            for name, expected_type in branch:
                field = getattr(value, name)
                field = getattr(field, "root", field)
                valid = valid and (field is None if expected_type == "null" else isinstance(field, str))
            matches += valid
        if matches != 1:
            raise ValueError("ExecutorReceiptResponse must match exactly one source oneOf branch")
        return self
'''
    lines = source.splitlines(keepends=True)
    lines.insert(target.end_lineno, method)
    lines.insert(target.lineno - 1, "from pydantic import model_validator as _executor_model_validator\n\n\n")
    destination.write_text("".join(lines))


def _generate_typescript(destination: Path) -> None:
    if not PNPM.is_file():
        raise RuntimeError(f"missing frozen pnpm toolchain: {PNPM}")
    _run(
        [
            str(PNPM),
            "exec",
            "openapi-typescript",
            str(OPENAPI_SOURCE),
            "--output",
            str(destination),
        ]
    )


def _same(expected: Path, actual: Path) -> bool:
    return actual.is_file() and filecmp.cmp(expected, actual, shallow=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate v2 Python validation models and TypeScript types."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when checked-in generated outputs differ without modifying them",
    )
    arguments = parser.parse_args()

    scratch_root = REPOSITORY_ROOT / "work" / "vnext"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="contracts-v2-", dir=scratch_root) as raw:
        temporary = Path(raw)
        generated_python = temporary / "generated.py"
        generated_typescript = temporary / "generated.ts"
        _generate_python(generated_python)
        _generate_typescript(generated_typescript)

        outputs = (
            (generated_python, PYTHON_DESTINATION),
            (generated_typescript, TYPESCRIPT_DESTINATION),
        )
        if arguments.check:
            stale = [str(destination.relative_to(REPOSITORY_ROOT)) for expected, destination in outputs if not _same(expected, destination)]
            if stale:
                print("Generated v2 contracts are stale:", file=sys.stderr)
                for path in stale:
                    print(f"- {path}", file=sys.stderr)
                return 1
            print("Generated Python and TypeScript v2 contracts match OpenAPI.")
            return 0

        for generated, destination in outputs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(generated, destination)
        print("Generated Python and TypeScript v2 contracts from OpenAPI.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
