/* The Windows download's start program: crazy-streamer-toolbox.exe.
 *
 * Does what "Start streamer-toolbox.bat" does, as a program to double-click, without a console window:
 * starts the Python that lies next to it (python\python.exe -m streamer_toolbox --open window, plus whatever
 * was given to this program) in its own folder, and waits until the toolbox ends.
 * What the toolbox prints goes into start.log in that folder. If the toolbox can't be started or ends with
 * an error, a message says so and names that file.
 *
 * Built by WindowsLauncher (windows_launcher.py):   gcc -O2 -municode -mwindows windows_launcher.c -o <exe>
 */
#include <windows.h>
#include <wchar.h>

#define LONGEST 32768
#define NAME L"crazy-streamer-toolbox"

static wchar_t folder[LONGEST], python[LONGEST], logfile[LONGEST], command[LONGEST], text[LONGEST];

static int failed(const wchar_t *what)
{
    MessageBoxW(NULL, what, NAME, MB_OK | MB_ICONERROR);
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show)
{
    (void) instance; (void) previous; (void) show;
    DWORD length = GetModuleFileNameW(NULL, folder, LONGEST);
    if (length == 0 || length >= LONGEST)
        return failed(L"Can't find out which folder this program is in.");
    wchar_t *slash = wcsrchr(folder, L'\\');
    if (slash == NULL)
        return failed(L"Can't find out which folder this program is in.");
    *slash = L'\0';

    swprintf(python, LONGEST, L"%ls\\python\\python.exe", folder);
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES) {
        swprintf(text, LONGEST, L"The folder \"python\" is missing next to this program:\n%ls\n\n"
                 L"Unpack the whole archive and start it from there.", folder);
        return failed(text);
    }
    swprintf(command, LONGEST, L"\"%ls\" -m streamer_toolbox --open window %ls", python, arguments ? arguments : L"");
    swprintf(logfile, LONGEST, L"%ls\\start.log", folder);

    SECURITY_ATTRIBUTES inherit = { sizeof(inherit), NULL, TRUE };
    HANDLE log = CreateFileW(logfile, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &inherit, CREATE_ALWAYS,
                             FILE_ATTRIBUTE_NORMAL, NULL);
    HANDLE nothing = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, &inherit, OPEN_EXISTING,
                                 0, NULL);
    STARTUPINFOW start;
    PROCESS_INFORMATION process;
    ZeroMemory(&start, sizeof(start));
    start.cb = sizeof(start);
    if (log != INVALID_HANDLE_VALUE) {  /* a folder that can't be written to: start anyway, without the log */
        start.dwFlags = STARTF_USESTDHANDLES;
        start.hStdInput = nothing;
        start.hStdOutput = log;
        start.hStdError = log;
    }
    if (!CreateProcessW(NULL, command, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, folder, &start, &process)) {
        swprintf(text, LONGEST, L"Can't start the toolbox's Python (Windows error %lu):\n%ls", GetLastError(), python);
        return failed(text);
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hProcess);
    CloseHandle(process.hThread);
    if (code != 0) {
        swprintf(text, LONGEST, L"The toolbox stopped with an error (%lu).\n\nWhat it said is in:\n%ls", code, logfile);
        return failed(text);
    }
    return 0;
}
