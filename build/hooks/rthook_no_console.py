"""Runtime hook: suppress console windows for child processes on Windows."""
import sys

if sys.platform == "win32":
    import subprocess
    _original_popen_init = subprocess.Popen.__init__

    def _popen_no_console(self, *args, **kwargs):
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW
        _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _popen_no_console
