"""P12 trustworthy completion: coverage, precheck, settlement and reports."""

from contextlib import contextmanager

import psycopg

from wuji_core.persistence.uow import DomainError


@contextmanager
def platform_errors():
    """Map a SECURITY DEFINER producer's SQLSTATE onto bounded domain codes.

    The P12 producers raise standard SQLSTATEs on purpose (42501/23505/22023/
    55000/40001); callers must never see a raw driver class or its message.
    """

    try:
        yield
    except psycopg.errors.InsufficientPrivilege as error:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
    except psycopg.errors.UniqueViolation as error:
        raise DomainError("INPUT_DIGEST_CONFLICT", 409) from error
    except psycopg.errors.InvalidParameterValue as error:
        raise DomainError("INVALID_SCHEMA", 422) from error
    except (
        psycopg.errors.ObjectNotInPrerequisiteState,
        psycopg.errors.SerializationFailure,
    ) as error:
        raise DomainError("STALE_EXECUTION", 409) from error
