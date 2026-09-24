class FBIAPIError(Exception):
    """Safe integration error that may be translated for API clients."""


class FBIAPITimeout(FBIAPIError):
    pass


class FBICaseNotFound(FBIAPIError):
    pass


class FBIImageError(FBIAPIError):
    pass
