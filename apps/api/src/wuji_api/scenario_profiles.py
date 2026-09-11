"""Versioned, inert built-in goal templates."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
class ScenarioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    id: str
    version: int
    scenario: Literal["ctf","web_single","comprehensive","exercise","code_audit"]
    name: str
    objective: str
    completion_criteria: list[str]
    digest: str
    can_create: bool
class ScenarioProfilePage(BaseModel):
    items: list[ScenarioProfile] = Field(min_length=5,max_length=5)
def scenario_profiles():
    return ScenarioProfilePage(items=json.loads((Path(__file__).parent / "scenario_profiles" / "builtin.json").read_text()))
def valid_template(reference, scenario):
    return reference is None or any(p.id == reference["id"] and p.version == reference["version"] and p.digest == reference["digest"] and p.scenario == scenario for p in scenario_profiles().items)
