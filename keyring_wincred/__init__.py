"""Windows Credential Manager keyring backend for WSL."""

import os
from typing import Optional

from keyring import backend, credentials
from jaraco.classes import properties
from keyring.errors import PasswordDeleteError, PasswordSetError

from . import powershell


def _is_wsl() -> bool:
    """Check if we're running under WSL."""
    # Check for WSL-specific indicators
    if os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop"):
        return True

    # Alternative: check /proc/version for Microsoft
    try:
        with open("/proc/version", "r") as f:
            version = f.read().lower()
            return "microsoft" in version or "wsl" in version
    except (FileNotFoundError, PermissionError):
        pass

    return False


def _make_target(service: str, username: str) -> str:
    """Create a credential target name from service and username."""
    return f"{service}:{username}"


class WinCredKeyring(backend.KeyringBackend):
    """
    Keyring backend that stores credentials in Windows Credential Manager.

    This backend is designed for use in WSL (Windows Subsystem for Linux),
    allowing Python applications running in WSL to store secrets in the
    Windows Credential Manager for secure, persistent storage.
    """

    @properties.classproperty
    def priority(cls) -> float:
        """
        Return the priority of this backend.

        Returns a high priority (9.0) when running under WSL,
        otherwise returns a negative value to disable this backend.
        """
        if _is_wsl():
            return 9.0
        return -1.0

    def get_password(self, service: str, username: str) -> Optional[str]:
        """
        Get a password from Windows Credential Manager.

        Args:
            service: The service name.
            username: The username.

        Returns:
            The password string, or None if not found.
        """
        target = _make_target(service, username)
        return powershell.get_credential(target)

    def set_password(self, service: str, username: str, password: str) -> None:
        """
        Store a password in Windows Credential Manager.

        Args:
            service: The service name.
            username: The username.
            password: The password to store.

        Raises:
            PasswordSetError: If the password could not be stored.
        """
        target = _make_target(service, username)
        if not powershell.set_credential(target, username, password):
            raise PasswordSetError(
                f"Failed to store credential for {service}/{username}"
            )

    def delete_password(self, service: str, username: str) -> None:
        """
        Delete a password from Windows Credential Manager.

        Args:
            service: The service name.
            username: The username.

        Raises:
            PasswordDeleteError: If the password could not be deleted.
        """
        target = _make_target(service, username)
        if not powershell.delete_credential(target):
            raise PasswordDeleteError(
                f"Failed to delete credential for {service}/{username}"
            )

    def get_credential(
        self, service: str, username: Optional[str]
    ) -> Optional[credentials.SimpleCredential]:
        """
        Get a credential (username and password) from Windows Credential Manager.

        Args:
            service: The service name.
            username: The username, or None to get any credential for the service.

        Returns:
            A SimpleCredential with username and password, or None if not found.
        """
        if username is None:
            # Cannot search without username in this implementation
            return None

        password = self.get_password(service, username)
        if password is not None:
            return credentials.SimpleCredential(username, password)
        return None
