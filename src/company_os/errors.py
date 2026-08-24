"""Domain exceptions used by the company operating system."""


class CompanyOSError(Exception):
    """Base class for expected company OS errors."""


class StorageError(CompanyOSError):
    """Persistent state could not be read or changed safely."""


class NotFoundError(StorageError):
    """A requested record does not exist."""


class ConflictError(StorageError):
    """A requested change conflicts with existing state."""


class ValidationError(CompanyOSError, ValueError):
    """Input failed a domain validation rule."""
