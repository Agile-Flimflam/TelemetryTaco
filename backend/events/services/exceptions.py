class InvalidBatchError(ValueError):
    """A capture request the service refuses as a whole. The API answers it with a 400."""
