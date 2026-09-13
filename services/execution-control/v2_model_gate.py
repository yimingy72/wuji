"""Isolated vNext composition export; never imports the legacy application."""

from wuji_core.admission.models import ModelAdmission, ModelGate, HttpxModelTransport
from wuji_core.http.model_gate import create_model_router

__all__ = ["ModelAdmission", "ModelGate", "HttpxModelTransport", "create_model_router"]
