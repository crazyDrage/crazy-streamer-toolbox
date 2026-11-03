import ctypes
import signal
import subprocess
import sys
from ctypes import wintypes

KILL_ON_JOB_CLOSE = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
EXTENDED_LIMIT_INFORMATION = 9      # JobObjectExtendedLimitInformation
PR_SET_PDEATHSIG = 1


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount",
                                                         "OtherOperationCount", "ReadTransferCount",
                                                         "WriteTransferCount", "OtherTransferCount")]


class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class TiedLaunch:
    """Starts a program that ends when this process ends, however it ends (Ctrl+C, its console window closed,
    a crash): the app window's browser goes with the toolbox (his answer to OPEN 93).

    Windows: the program goes into a job object that kills what is in it once its last handle closes, and only
    this process holds that handle. Linux: the program gets SIGTERM when its parent dies (PR_SET_PDEATHSIG;
    start it from the main thread: Linux counts the thread that started it as the parent).
    Anywhere else, or if the system refuses, it is a plain start. Call it like subprocess.Popen."""

    def __init__(self) -> None:
        self._job = None  # Windows: made at the first start, kept open for as long as this process lives

    def __call__(self, command: list[str]) -> subprocess.Popen:
        if sys.platform == "win32":
            process = subprocess.Popen(command)
            self._into_job(process)
            return process
        if sys.platform.startswith("linux"):
            return subprocess.Popen(command, preexec_fn=_die_with_parent)
        return subprocess.Popen(command)

    def _into_job(self, process: subprocess.Popen) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        if self._job is None:
            job = kernel32.CreateJobObjectW(None, None)
            limits = _ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = KILL_ON_JOB_CLOSE
            if not job or not kernel32.SetInformationJobObject(job, EXTENDED_LIMIT_INFORMATION,
                                                               ctypes.byref(limits), ctypes.sizeof(limits)):
                return
            self._job = job
        kernel32.AssignProcessToJobObject(self._job, int(process._handle))


def _die_with_parent() -> None:
    ctypes.CDLL(None).prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
