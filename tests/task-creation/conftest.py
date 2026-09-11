"""Reuse the owned temporary PostgreSQL fixture, without existing databases."""
import importlib.util
import sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('creation_owned_pg',Path(__file__).parents[1]/'control-plane'/'conftest.py')
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
draft_database=module.draft_database
draft_case=module.draft_case
