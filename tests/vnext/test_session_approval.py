"""P08 SessionManifest and native approval acceptance tests."""

from inspect import Parameter

from support.p08 import REQUIRED, parameter_shape, session_repository_type


def test_session_repository_exposes_frozen_publish_and_load_contract():
    repository_type = session_repository_type()

    assert parameter_shape(repository_type) == (
        ("uow", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("artifacts", Parameter.KEYWORD_ONLY, REQUIRED),
        ("registry", Parameter.KEYWORD_ONLY, REQUIRED),
    )
    assert parameter_shape(repository_type.publish) == (
        ("self", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("access", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("assignment", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("manifest", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("expected_revision", Parameter.KEYWORD_ONLY, REQUIRED),
    )
    assert parameter_shape(repository_type.load_published) == (
        ("self", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("access", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("task_id", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("session_id", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("revision", Parameter.KEYWORD_ONLY, None),
    )
