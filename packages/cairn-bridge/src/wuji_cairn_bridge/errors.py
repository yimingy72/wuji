class CairnBridgeError(Exception):
    """A redacted platform integration error, without native response bodies."""


class InvalidBridgeInput(CairnBridgeError, ValueError):
    pass


class BindingConflict(CairnBridgeError):
    pass


class OperationConflict(CairnBridgeError):
    pass


class BindingUnavailable(CairnBridgeError):
    pass


class DispatchDenied(CairnBridgeError):
    pass


class CairnUnavailable(CairnBridgeError):
    pass
