"""PowerShell interop for Windows Credential Manager access from WSL."""

import base64
import subprocess
from typing import Optional

# PowerShell script with C# interop to access Windows Credential Manager
# This avoids requiring any external PowerShell modules
_CRED_MANAGER_CS = r'''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class CredManager {
    public const int CRED_TYPE_GENERIC = 1;
    public const int CRED_PERSIST_LOCAL_MACHINE = 2;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CredRead(string target, int type, int reservedFlag, out IntPtr credentialPtr);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CredWrite([In] ref CREDENTIAL userCredential, [In] uint flags);

    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool CredDelete(string target, int type, int flags);

    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern void CredFree([In] IntPtr cred);

    public static string GetCredential(string target) {
        IntPtr credPtr;
        if (!CredRead(target, CRED_TYPE_GENERIC, 0, out credPtr)) {
            return null;
        }
        try {
            CREDENTIAL cred = (CREDENTIAL)Marshal.PtrToStructure(credPtr, typeof(CREDENTIAL));
            if (cred.CredentialBlobSize > 0) {
                byte[] passwordBytes = new byte[cred.CredentialBlobSize];
                Marshal.Copy(cred.CredentialBlob, passwordBytes, 0, cred.CredentialBlobSize);
                return Convert.ToBase64String(passwordBytes);
            }
            return "";
        } finally {
            CredFree(credPtr);
        }
    }

    public static bool SetCredential(string target, string username, string base64Password) {
        byte[] passwordBytes = Convert.FromBase64String(base64Password);

        CREDENTIAL cred = new CREDENTIAL();
        cred.Type = CRED_TYPE_GENERIC;
        cred.TargetName = target;
        cred.UserName = username;
        cred.CredentialBlobSize = passwordBytes.Length;
        cred.CredentialBlob = Marshal.AllocHGlobal(passwordBytes.Length);
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE;

        try {
            Marshal.Copy(passwordBytes, 0, cred.CredentialBlob, passwordBytes.Length);
            return CredWrite(ref cred, 0);
        } finally {
            Marshal.FreeHGlobal(cred.CredentialBlob);
        }
    }

    public static bool DeleteCredential(string target) {
        return CredDelete(target, CRED_TYPE_GENERIC, 0);
    }
}
"@
'''


def _run_powershell(script: str) -> tuple[int, str, str]:
    """Run a PowerShell script and return (returncode, stdout, stderr)."""
    full_script = _CRED_MANAGER_CS + "\n" + script

    # Encode the script as base64 to avoid quoting issues
    script_bytes = full_script.encode('utf-16-le')
    encoded_script = base64.b64encode(script_bytes).decode('ascii')

    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded_script],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_credential(target: str) -> Optional[str]:
    """
    Get a credential from Windows Credential Manager.

    Args:
        target: The target name (e.g., "service:username")

    Returns:
        The password as a string, or None if not found.
    """
    # Escape the target for PowerShell
    escaped_target = target.replace("'", "''")
    script = f'''
$result = [CredManager]::GetCredential('{escaped_target}')
if ($result -eq $null) {{
    exit 1
}}
Write-Output $result
'''
    returncode, stdout, stderr = _run_powershell(script)

    if returncode != 0 or not stdout:
        return None

    # Decode the base64 password
    try:
        password_bytes = base64.b64decode(stdout)
        # Windows stores credentials as UTF-16LE
        return password_bytes.decode('utf-16-le')
    except Exception:
        return None


def set_credential(target: str, username: str, password: str) -> bool:
    """
    Store a credential in Windows Credential Manager.

    Args:
        target: The target name (e.g., "service:username")
        username: The username to store
        password: The password to store

    Returns:
        True if successful, False otherwise.
    """
    # Encode password as UTF-16LE then base64 (Windows credential format)
    password_bytes = password.encode('utf-16-le')
    b64_password = base64.b64encode(password_bytes).decode('ascii')

    escaped_target = target.replace("'", "''")
    escaped_username = username.replace("'", "''")

    script = f'''
$result = [CredManager]::SetCredential('{escaped_target}', '{escaped_username}', '{b64_password}')
if (-not $result) {{
    exit 1
}}
'''
    returncode, stdout, stderr = _run_powershell(script)
    return returncode == 0


def delete_credential(target: str) -> bool:
    """
    Delete a credential from Windows Credential Manager.

    Args:
        target: The target name (e.g., "service:username")

    Returns:
        True if successful, False otherwise.
    """
    escaped_target = target.replace("'", "''")
    script = f'''
$result = [CredManager]::DeleteCredential('{escaped_target}')
if (-not $result) {{
    exit 1
}}
'''
    returncode, stdout, stderr = _run_powershell(script)
    return returncode == 0
