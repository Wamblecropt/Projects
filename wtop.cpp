        // wtop.cpp
    // Compile: g++ wtop.cpp -o wtop.exe -lpsapi
/*
    wtop - Windows Task Monitor (lightweight htop alternative)
    -----------------------------------------------------------

    Controls:
    - TAB      : Toggle sorting (CPU % <-> RAM usage)
    - /        : Enter search mode (filter by process name)
    - Enter    : Apply filter
    - Esc      : Cancel search
    - ↑ / ↓    : Scroll process list
    - H        : Toggle help screen
    - Ctrl+C   : Exit

    Display:
    - Shows top processes (default 15 visible)
    - CPU% and RAM usage per process
    - Global CPU and memory usage at top
    - Sorted by CPU (default) or memory

    Notes:
    - Lightweight: No external dependencies
    - Safe: Uses only Windows native APIs (psapi, toolhelp, etc.)
    - Efficient: Updates every second, minimal allocations
*/


#include <windows.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <conio.h>
#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <thread>
#include <chrono>
#include <map>
#include <algorithm>
#include <cwctype>

#pragma comment(lib, "psapi.lib")

struct ProcessInfo {
    DWORD pid;
    std::wstring name;
    SIZE_T memory;
    double cpu;
};

std::map<DWORD, ULONGLONG> lastProcTime;
std::map<DWORD, ULONGLONG> lastSysTime;

ULONGLONG FileTimeToULL(const FILETIME& ft) {
    ULARGE_INTEGER ul;
    ul.LowPart = ft.dwLowDateTime;
    ul.HighPart = ft.dwHighDateTime;
    return ul.QuadPart;
}

void ClearScreen() {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    COORD topLeft = {0, 0};
    SetConsoleCursorPosition(hConsole, topLeft);
}

float GetSystemCPU() {
    static FILETIME prevIdle, prevKernel, prevUser;
    FILETIME idle, kernel, user;
    if (!GetSystemTimes(&idle, &kernel, &user)) return -1;

    ULONGLONG sys = (FileTimeToULL(kernel) + FileTimeToULL(user)) -
                    (FileTimeToULL(prevKernel) + FileTimeToULL(prevUser));
    ULONGLONG idleDiff = FileTimeToULL(idle) - FileTimeToULL(prevIdle);

    prevIdle = idle;
    prevKernel = kernel;
    prevUser = user;

    if (sys == 0) return 0;
    return float(sys - idleDiff) * 100.0f / sys;
}

float GetMemoryUsageMB(DWORDLONG& totalOut, DWORDLONG& availOut) {
    MEMORYSTATUSEX mem = {};
    mem.dwLength = sizeof(mem);
    GlobalMemoryStatusEx(&mem);
    totalOut = mem.ullTotalPhys;
    availOut = mem.ullAvailPhys;
    return float(mem.ullTotalPhys - mem.ullAvailPhys) / (1024 * 1024);
}

void GetProcesses(std::vector<ProcessInfo>& list, bool sortByCpu) {
    list.clear();
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return;

    FILETIME sysIdle, sysKernel, sysUser;
    GetSystemTimes(&sysIdle, &sysKernel, &sysUser);
    ULONGLONG nowSys = FileTimeToULL(sysKernel) + FileTimeToULL(sysUser);

    PROCESSENTRY32W pe = { sizeof(pe) };
    if (Process32FirstW(hSnap, &pe)) {
        do {
            HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pe.th32ProcessID);
            SIZE_T mem = 0;
            double cpu = 0.0;

            if (hProc) {
                PROCESS_MEMORY_COUNTERS pmc;
                if (GetProcessMemoryInfo(hProc, &pmc, sizeof(pmc)))
                    mem = pmc.WorkingSetSize;

                FILETIME create, exit, kernel, user;
                if (GetProcessTimes(hProc, &create, &exit, &kernel, &user)) {
                    ULONGLONG nowProc = FileTimeToULL(kernel) + FileTimeToULL(user);
                    ULONGLONG lastP = lastProcTime[pe.th32ProcessID];
                    ULONGLONG lastS = lastSysTime[pe.th32ProcessID];

                    if (lastS > 0 && nowSys > lastS)
                        cpu = double(nowProc - lastP) * 100.0 / (nowSys - lastS);

                    lastProcTime[pe.th32ProcessID] = nowProc;
                    lastSysTime[pe.th32ProcessID] = nowSys;
                }

                CloseHandle(hProc);
            }

            list.push_back({ pe.th32ProcessID, pe.szExeFile, mem, cpu });
        } while (Process32NextW(hSnap, &pe));
    }

    CloseHandle(hSnap);

    std::sort(list.begin(), list.end(), [=](const ProcessInfo& a, const ProcessInfo& b) {
        return sortByCpu ? (a.cpu > b.cpu) : (a.memory > b.memory);
    });
}

bool MatchesFilter(const std::wstring& name, const std::wstring& filter) {
    if (filter.empty()) return true;
    std::wstring lowerName = name, lowerFilter = filter;
    std::transform(lowerName.begin(), lowerName.end(), lowerName.begin(), towlower);
    std::transform(lowerFilter.begin(), lowerFilter.end(), lowerFilter.begin(), towlower);
    return lowerName.find(lowerFilter) != std::wstring::npos;
}

void PrintHelp() {
    ClearScreen();
    std::wcout << L"wtop - Windows Process Monitor Help\n";
    std::wcout << L"===================================\n\n";
    std::wcout << L"  TAB      - Toggle CPU/RAM sorting\n";
    std::wcout << L"  /        - Search filter by name\n";
    std::wcout << L"  UP/DOWN  - Scroll process list\n";
    std::wcout << L"  H        - Toggle this help screen\n";
    std::wcout << L"  Ctrl+C   - Quit\n\n";
    std::wcout << L"Press H to return to the main screen...\n";
}

int main() {
    SetConsoleOutputCP(CP_UTF8);
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);

    CONSOLE_CURSOR_INFO ci;
    GetConsoleCursorInfo(hConsole, &ci);
    ci.bVisible = FALSE;
    SetConsoleCursorInfo(hConsole, &ci);

    bool sortByCpu = true;
    bool showHelp = false;
    int scroll = 0;
    bool searchMode = false;
    std::wstring searchFilter;

    std::vector<ProcessInfo> allProcesses, filtered;

    while (true) {
        if (_kbhit()) {
            int ch = _getch();
            if (searchMode) {
                if (ch == 27) {
                    searchMode = false;
                    searchFilter.clear();
                } else if (ch == '\r') {
                    searchMode = false;
                } else if (ch == '\b') {
                    if (!searchFilter.empty()) searchFilter.pop_back();
                } else if (iswprint(ch)) {
                    searchFilter += wchar_t(ch);
                }
            } else {
                if (ch == 0 || ch == 224) {
                    ch = _getch();
                    if (!showHelp) {
                        if (ch == 72 && scroll > 0) scroll--;         // UP
                        if (ch == 80 && scroll < int(filtered.size()) - 15) scroll++; // DOWN
                    }
                } else {
                    if (ch == 9) { // TAB
                        sortByCpu = !sortByCpu;
                        scroll = 0;
                    } else if (ch == 'h' || ch == 'H') {
                        showHelp = !showHelp;
                    } else if (ch == '/') {
                        searchMode = true;
                        searchFilter.clear();
                    }
                }
            }
        }

        if (showHelp) {
            PrintHelp();
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        GetProcesses(allProcesses, sortByCpu);
        float cpu = GetSystemCPU();
        DWORDLONG totalMem, availMem;
        float usedMemMB = GetMemoryUsageMB(totalMem, availMem);

        filtered.clear();
        for (const auto& p : allProcesses)
            if (MatchesFilter(p.name, searchFilter))
                filtered.push_back(p);

        ClearScreen();

        std::wcout << L"wtop - Windows Process Monitor [TAB=sort, /=filter, H=help]\n";
        std::wcout << L"===========================================================\n";
        std::wcout << std::fixed << std::setprecision(2)
                   << L"CPU Usage:    " << cpu << L" %\n"
                   << L"Memory Usage: " << usedMemMB << L" MB / "
                   << float(totalMem) / (1024 * 1024) << L" MB\n"
                   << L"Sort Mode:    " << (sortByCpu ? L"CPU %" : L"RAM MB") << L"\n"
                   << L"Filter:       " << (searchFilter.empty() ? L"<none>" : searchFilter) << L"\n\n";

        if (searchMode)
            std::wcout << L"/" << searchFilter << L"_\n\n";

        std::wcout << std::left
                   << std::setw(7) << L"PID"
                   << std::setw(30) << L"Process"
                   << std::setw(10) << L"Memory"
                   << std::setw(8) << L"CPU %"
                   << L"\n";
        std::wcout << L"-------------------------------------------------------------\n";

        for (int i = scroll; i < scroll + 15 && i < filtered.size(); ++i) {
            const auto& p = filtered[i];
            std::wcout << std::left
                       << std::setw(7) << p.pid
                       << std::setw(30) << p.name.substr(0, 28)
                       << std::setw(10) << std::fixed << std::setprecision(1) << (p.memory / (1024.0 * 1024.0))
                       << std::setw(6) << std::fixed << std::setprecision(1) << p.cpu
                       << L"\n";
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    return 0;
}
