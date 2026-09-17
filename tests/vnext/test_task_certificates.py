"""Per-Task Service names need a certificate that covers them."""

from __future__ import annotations

import importlib.util
import ssl
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _load_module():
    path = REPOSITORY_ROOT / "scripts" / "vnext" / "k8s.py"
    spec = importlib.util.spec_from_file_location("wuji_vnext_k8s", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


k8s = _load_module()


def test_only_the_task_services_cover_one_extra_label():
    agent = k8s.service_dns("task-agent")
    kali = k8s.service_dns("task-kali")
    runtime = k8s.service_dns("runtime")

    for names in (agent, kali):
        assert "task-agent.wuji-vnext-test.svc" in names or "task-kali.wuji-vnext-test.svc" in names
        assert "*.wuji-vnext-test.svc" in names
        assert "*.wuji-vnext-test.svc.cluster.local" in names
    assert not any(name.startswith("*") for name in runtime)


def test_rotating_the_task_leaves_keeps_the_ca_and_covers_per_task_services(tmp_path):
    state = tmp_path / "tls"
    k8s.certificates(state)
    ca_before = (state / "ca.crt").read_bytes()
    runtime_before = (state / "runtime.crt").read_bytes()

    raw = tmp_path / "raw"
    raw.mkdir()
    fingerprints = k8s.rotate_service_certificates(state, raw=raw)

    assert set(fingerprints) == {"task-agent", "task-kali"}
    assert (state / "ca.crt").read_bytes() == ca_before
    # A Service the rotation did not name keeps its published leaf.
    assert (state / "runtime.crt").read_bytes() == runtime_before
    # The rotated leaf still chains to the same CA and matches a per-Task name.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(state / "ca.crt"))
    for name, host in (
        ("task-agent", f"task-agent-0123456789ab.{k8s.NAMESPACE}.svc"),
        ("task-kali", f"task-kali-0123456789ab.{k8s.NAMESPACE}.svc"),
    ):
        context.load_cert_chain(str(state / f"{name}.crt"), str(state / f"{name}.key"))
        assert context.get_ca_certs()
    with pytest.raises(ValueError):
        k8s.rotate_service_certificates(state, services=("runtime",), raw=raw)
