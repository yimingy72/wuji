# P02 fix round 1 HTTP consumer handoff

P03 and later route modules must construct routes with `VNextAPIRouter`. `create_app` rejects an `APIRouter` containing ordinary FastAPI routes, so a new route cannot silently bypass the Decimal-preserving request class.

```python
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter

router = VNextAPIRouter()

@router.post("/api/v2/example")
async def example(command: GeneratedCommand) -> DecimalJSONResponse:
    result = GeneratedResult.model_validate(await service.execute(command))
    return DecimalJSONResponse(result.model_dump(mode="python"))
```

Request behavior is automatic for every `VNextAPIRouter` route: `StrictJsonMiddleware` reads within configured byte/time limits, rejects disconnects, duplicate keys, excessive nesting and invalid numeric tokens, and stores the parsed object. `StrictJsonRoute` supplies `StrictJsonRequest`, whose public `json()` override returns that same object to FastAPI/Pydantic without a binary-float reparse.

Response rules:

- A route returning ordinary JSON without `Decimal` may return its usual dict or BaseModel and retain normal FastAPI response-model handling.
- A route that can return unstructured or precision-sensitive JSON numbers must validate its result explicitly, call `model_dump(mode="python")`, and return `DecimalJSONResponse` as above. This preserves Decimal as an unquoted JSON number.
- If a dict or BaseModel containing `Decimal` is returned through the normal FastAPI encoder, the router stops it before encoding and emits a fixed 503/`CAPABILITY_UNAVAILABLE`; it cannot silently become float, string, `null`, or pass response-model validation on changed data.
- Returning a `Response` bypasses FastAPI response-model serialization, so callers must perform the explicit generated/public-wrapper validation shown above before constructing `DecimalJSONResponse`.

Composition can override the protocol safety limits without changing product Task budgets:

```python
from wuji_core.http import JsonBoundaryLimits, create_app

app = create_app(
    token_verifier=verifier,
    routers=[router],
    json_limits=JsonBoundaryLimits(
        max_body_bytes=1_048_576,
        read_timeout_seconds=5.0,
        max_nesting_depth=64,
        max_number_characters=256,
        max_decimal_adjusted_exponent=10_000,
    ),
)
```

Use the policy wrappers from `wuji_core.contracts.knowledge` for FactAssessment/AssessmentCommand. Raw generated assessment DTOs describe wire fields but do not replace the wrapper's model-only-support rule.
