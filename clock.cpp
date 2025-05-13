/*
--Clock App Documentation--
	Overview
This Clock App is designed to display the current time, date, and weekday on your Windows desktop. It runs as a small window at the top of the screen, with a close button and a clear, easy-to-read display.

	Features:
Displays Time: Current hour, minute, and second.
Displays Date: Shows the current date in the format YYYY-MM-DD.
Displays Weekday: The full name of the current day of the week.
Close Button: An "X" button to close the app.
*/


// Compile: g++ c.cpp -o c.exe -mwindows -lgdi32


#define UNICODE
#define _UNICODE

#include <windows.h>
#include <time.h>
#include <stdio.h>

// Function prototypes
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
void UpdateClock(HWND hwnd);

// Global variables
HFONT hFontSmall, hFontItalic, hFontButton;
HWND hwndButton;
POINT ptPrev;

// **WinMain: Entry point**
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    const wchar_t CLASS_NAME[] = L"ClockWindow";
    WNDCLASS wc = { };
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);

    RegisterClass(&wc);

    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);

    HWND hwnd = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        CLASS_NAME,
        L"Clock",
        WS_POPUP | WS_BORDER,
        (screenW - 300) / 2, 0, 310, 15,  // Centered at top of screen
        NULL, NULL, hInstance, NULL
    );

    if (!hwnd) return -1;

    // Create Close Button
    hwndButton = CreateWindowW(
        L"BUTTON", L"X", WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        300, 2, 9, 9, hwnd, (HMENU)1, hInstance, NULL
    );

    ShowWindow(hwnd, SW_SHOW);
    UpdateClock(hwnd);
    SetTimer(hwnd, 1, 1000, NULL);  // Clock update every second

    MSG msg = { };
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    return 0;
}

// **Window procedure (handles events)**
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        case WM_CREATE:
            // Normal font (time/date)
            hFontSmall = CreateFontW(12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                                     OUT_OUTLINE_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY, VARIABLE_PITCH, L"Arial");

            // Italic font (weekday)
            hFontItalic = CreateFontW(12, 0, 0, 0, FW_NORMAL, TRUE, FALSE, FALSE, DEFAULT_CHARSET,
                                      OUT_OUTLINE_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY, VARIABLE_PITCH, L"Arial");

            hFontButton = CreateFontW(13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                                      OUT_OUTLINE_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY, VARIABLE_PITCH, L"Arial");
            break;

        case WM_TIMER:
            UpdateClock(hwnd);  // Update time every second
            break;

        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            RECT rect;
            GetClientRect(hwnd, &rect);
            SetTextColor(hdc, RGB(255, 255, 255));
            SetBkMode(hdc, TRANSPARENT);

            // Draw Time
            time_t now = time(0);
            struct tm t;
            localtime_s(&t, &now);

            wchar_t timeStr[9], dateStr[40];
            swprintf(timeStr, 9, L"%02d:%02d:%02d", t.tm_hour, t.tm_min, t.tm_sec);
            swprintf(dateStr, 40, L"%04d-%02d-%02d", t.tm_year + 1900, t.tm_mon + 1, t.tm_mday);

            const wchar_t* weekdays[] = { L"Sunday", L"Monday", L"Tuesday", L"Wednesday", L"Thursday", L"Friday", L"Saturday" };

            // Set the font for the time/date (normal font)
            SelectObject(hdc, hFontSmall);
            RECT timeRect = { 0, 0, 90, rect.bottom };
            DrawTextW(hdc, timeStr, -1, &timeRect, DT_LEFT | DT_VCENTER | DT_SINGLELINE);

            // Set the font for the date (normal font)
            SelectObject(hdc, hFontSmall);
            RECT dateRect = { 100, 0, 200, rect.bottom };
            DrawTextW(hdc, dateStr, -1, &dateRect, DT_LEFT | DT_VCENTER | DT_SINGLELINE);

            // Set the font for the weekday name (italic font)
            SelectObject(hdc, hFontItalic);
            RECT weekdayRect = { 210, 0, rect.right, rect.bottom };
            DrawTextW(hdc, weekdays[t.tm_wday], -1, &weekdayRect, DT_LEFT | DT_VCENTER | DT_SINGLELINE);

            EndPaint(hwnd, &ps);
            break;
        }

        case WM_COMMAND:
            if (LOWORD(wParam) == 1) PostMessage(hwnd, WM_CLOSE, 0, 0);  // Close button clicked
            break;

        case WM_LBUTTONDOWN:
            ptPrev.x = LOWORD(lParam);
            ptPrev.y = HIWORD(lParam);
            return 0;

        case WM_MOUSEMOVE:
            if (wParam & MK_LBUTTON) {
                POINT pt;
                GetCursorPos(&pt);
                SetWindowPos(hwnd, NULL, pt.x - ptPrev.x, pt.y - ptPrev.y, 0, 0, SWP_NOZORDER | SWP_NOSIZE);
            }
            return 0;

        case WM_DESTROY:
            DeleteObject(hFontSmall);
            DeleteObject(hFontItalic);
            DeleteObject(hFontButton);
            PostQuitMessage(0);
            break;

        default:
            return DefWindowProc(hwnd, uMsg, wParam, lParam);
    }
    return 0;
}

// **Updates the clock every second**
void UpdateClock(HWND hwnd) {
    InvalidateRect(hwnd, NULL, TRUE);
}
