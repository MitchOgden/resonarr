class ManualActionError(Exception):
    http_status_code = 400
    code = "manual_action_error"

    def __init__(self, *, action, message, details=None):
        self.action = action
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_details(self):
        return {
            "action": self.action,
            **self.details,
        }


class ActionTargetNotFoundError(ManualActionError):
    http_status_code = 404
    code = "action_target_not_found"


class ActionConflictError(ManualActionError):
    http_status_code = 409
    code = "action_conflict"


class ActionExecutionError(ManualActionError):
    http_status_code = 422
    code = "action_execution_failed"
