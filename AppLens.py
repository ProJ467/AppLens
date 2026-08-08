
import tkinter as tk
from tkinter import messagebox
import ctypes
from ctypes import wintypes
import psutil
import time
from datetime import datetime


# ============================================================
# Windows API
# ============================================================

user32 = ctypes.WinDLL(
    "user32",
    use_last_error=True
)

EnumWindows = user32.EnumWindows
IsWindowVisible = user32.IsWindowVisible
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextW = user32.GetWindowTextW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowRect = user32.GetWindowRect


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]


# ============================================================
# Windows
# ============================================================

def get_windows():

    windows = []

    CALLBACK = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )

    @CALLBACK
    def callback(hwnd, lparam):

        try:

            if not IsWindowVisible(hwnd):
                return True

            length = GetWindowTextLengthW(hwnd)

            if length <= 0:
                return True

            buffer = ctypes.create_unicode_buffer(
                length + 1
            )

            GetWindowTextW(
                hwnd,
                buffer,
                length + 1
            )

            title = buffer.value.strip()

            if title:
                windows.append(
                    (hwnd, title)
                )

        except Exception:
            pass

        return True

    EnumWindows(
        callback,
        0
    )

    return windows


def get_pid(hwnd):

    pid = wintypes.DWORD()

    result = GetWindowThreadProcessId(
        hwnd,
        ctypes.byref(pid)
    )

    if result == 0:
        return None

    return pid.value


def get_window_rect(hwnd):

    rect = RECT()

    result = GetWindowRect(
        hwnd,
        ctypes.byref(rect)
    )

    if not result:
        return None

    return (
        rect.left,
        rect.top,
        rect.right,
        rect.bottom
    )


# ============================================================
# Formatting
# ============================================================

def format_bytes(value):

    if value is None:
        return "N/A"

    if value < 1024:
        return f"{value} B"

    if value < 1024 ** 2:
        return f"{value / 1024:.2f} KB"

    if value < 1024 ** 3:
        return f"{value / 1024 ** 2:.2f} MB"

    return f"{value / 1024 ** 3:.2f} GB"


def format_time(seconds):

    seconds = int(seconds)

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    if days:
        return f"{days}d {hours}h {minutes}m"

    if hours:
        return f"{hours}h {minutes}m {seconds}s"

    if minutes:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


# ============================================================
# AppLens
# ============================================================

class AppLens:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "AppLens v3"
        )

        self.root.geometry(
            "1100x700"
        )

        self.root.minsize(
            900,
            600
        )

        self.windows = []

        self.selected_pid = None
        self.selected_hwnd = None

        self.live_monitoring = True

        self.create_ui()

        self.refresh_windows()

        self.update_stats()


    # ========================================================
    # UI
    # ========================================================

    def create_ui(self):

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            self.root
        )

        header.pack(
            fill="x",
            padx=15,
            pady=15
        )

        tk.Label(
            header,
            text="AppLens",
            font=(
                "Arial",
                26,
                "bold"
            )
        ).pack(
            side="left"
        )

        tk.Label(
            header,
            text="  Windows Application Monitor",
            font=(
                "Arial",
                10
            )
        ).pack(
            side="left",
            padx=10
        )


        # ----------------------------------------------------
        # Toolbar
        # ----------------------------------------------------

        toolbar = tk.Frame(
            self.root
        )

        toolbar.pack(
            fill="x",
            padx=15
        )

        tk.Button(
            toolbar,
            text="🔄 Refresh",
            width=15,
            command=self.refresh_windows
        ).pack(
            side="left",
            padx=(0, 5)
        )

        self.monitor_button = tk.Button(
            toolbar,
            text="⏸ Stop Live",
            width=15,
            command=self.toggle_monitor
        )

        self.monitor_button.pack(
            side="left",
            padx=5
        )

        tk.Button(
            toolbar,
            text="📋 Copy Info",
            width=15,
            command=self.copy_info
        ).pack(
            side="left",
            padx=5
        )


        # ----------------------------------------------------
        # Main
        # ----------------------------------------------------

        main = tk.Frame(
            self.root
        )

        main.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )


        # ----------------------------------------------------
        # Window list
        # ----------------------------------------------------

        left = tk.Frame(
            main
        )

        left.pack(
            side="left",
            fill="both",
            expand=True
        )

        tk.Label(
            left,
            text="Open Windows",
            font=(
                "Arial",
                12,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(0, 5)
        )


        list_frame = tk.Frame(
            left
        )

        list_frame.pack(
            fill="both",
            expand=True
        )


        scrollbar = tk.Scrollbar(
            list_frame
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )


        self.window_list = tk.Listbox(
            list_frame,
            font=(
                "Consolas",
                10
            ),
            yscrollcommand=scrollbar.set
        )

        self.window_list.pack(
            side="left",
            fill="both",
            expand=True
        )


        scrollbar.config(
            command=self.window_list.yview
        )


        self.window_list.bind(
            "<<ListboxSelect>>",
            self.select_window
        )


        # ----------------------------------------------------
        # Right side
        # ----------------------------------------------------

        right = tk.Frame(
            main
        )

        right.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(15, 0)
        )


        tk.Label(
            right,
            text="Application Information",
            font=(
                "Arial",
                12,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(0, 5)
        )


        # ----------------------------------------------------
        # Stats cards
        # ----------------------------------------------------

        stats = tk.Frame(
            right
        )

        stats.pack(
            fill="x"
        )


        self.ram_label = self.create_stat(
            stats,
            "RAM",
            "N/A"
        )

        self.cpu_label = self.create_stat(
            stats,
            "CPU",
            "N/A"
        )

        self.threads_label = self.create_stat(
            stats,
            "Threads",
            "N/A"
        )

        self.status_label = self.create_stat(
            stats,
            "Status",
            "N/A"
        )


        # ----------------------------------------------------
        # Information
        # ----------------------------------------------------

        info_frame = tk.Frame(
            right
        )

        info_frame.pack(
            fill="both",
            expand=True,
            pady=15
        )


        self.info = tk.Text(
            info_frame,
            font=(
                "Consolas",
                10
            ),
            wrap="word",
            state="disabled"
        )

        self.info.pack(
            fill="both",
            expand=True
        )


        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        self.status = tk.Label(
            self.root,
            text="Ready",
            anchor="w"
        )

        self.status.pack(
            fill="x",
            padx=15,
            pady=(0, 10)
        )


    # ========================================================
    # Stat card
    # ========================================================

    def create_stat(
        self,
        parent,
        title,
        value
    ):

        frame = tk.Frame(
            parent,
            relief="groove",
            borderwidth=1
        )

        frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=3
        )


        tk.Label(
            frame,
            text=title,
            font=(
                "Arial",
                9
            )
        ).pack(
            pady=(8, 0)
        )


        label = tk.Label(
            frame,
            text=value,
            font=(
                "Arial",
                15,
                "bold"
            )
        )

        label.pack(
            pady=(2, 8)
        )


        return label


    # ========================================================
    # Refresh windows
    # ========================================================

    def refresh_windows(self):

        self.window_list.delete(
            0,
            tk.END
        )

        self.windows = get_windows()

        for hwnd, title in self.windows:

            self.window_list.insert(
                tk.END,
                title
            )


        self.status.config(
            text=f"Found {len(self.windows)} windows"
        )


    # ========================================================
    # Select
    # ========================================================

    def select_window(self, event=None):

        selection = (
            self.window_list.curselection()
        )

        if not selection:
            return

        index = selection[0]

        if index >= len(self.windows):
            return

        hwnd, title = self.windows[index]

        pid = get_pid(hwnd)

        self.selected_hwnd = hwnd
        self.selected_pid = pid

        self.show_information(
            hwnd,
            title,
            pid
        )


    # ========================================================
    # Information
    # ========================================================

    def show_information(
        self,
        hwnd,
        title,
        pid
    ):

        try:

            process = psutil.Process(
                pid
            )

            name = process.name()

            try:
                path = process.exe()
            except:
                path = "Access denied"

            try:
                status = process.status()
            except:
                status = "Unknown"

            try:
                create_time = process.create_time()

                start_time = datetime.fromtimestamp(
                    create_time
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            except:
                start_time = "Unknown"


            try:

                memory = process.memory_info()

                ram = format_bytes(
                    memory.rss
                )

                virtual_memory = format_bytes(
                    memory.vms
                )

            except:
                ram = "N/A"
                virtual_memory = "N/A"


            try:

                threads = process.num_threads()

            except:

                threads = "N/A"


            rect = get_window_rect(
                hwnd
            )

            if rect:

                left, top, right, bottom = rect

                position = (
                    f"{left}, {top}"
                )

                size = (
                    f"{right - left} × "
                    f"{bottom - top}"
                )

            else:

                position = "N/A"
                size = "N/A"


            text = (
                f"TITLE\n"
                f"{title}\n\n"

                f"PROCESS\n"
                f"{name}\n\n"

                f"PID\n"
                f"{pid}\n\n"

                f"STATUS\n"
                f"{status}\n\n"

                f"RAM\n"
                f"{ram}\n\n"

                f"VIRTUAL MEMORY\n"
                f"{virtual_memory}\n\n"

                f"THREADS\n"
                f"{threads}\n\n"

                f"START TIME\n"
                f"{start_time}\n\n"

                f"POSITION\n"
                f"{position}\n\n"

                f"WINDOW SIZE\n"
                f"{size}\n\n"

                f"EXE PATH\n"
                f"{path}"
            )

            self.set_information(
                text
            )

        except psutil.NoSuchProcess:

            self.set_information(
                "Process has already exited."
            )

        except psutil.AccessDenied:

            self.set_information(
                "Access denied by Windows."
            )

        except Exception as error:

            self.set_information(
                f"Error:\n{error}"
            )


    # ========================================================
    # Live stats
    # ========================================================

    def update_stats(self):

        if self.live_monitoring:

            if self.selected_pid:

                try:

                    process = psutil.Process(
                        self.selected_pid
                    )

                    ram = process.memory_info().rss

                    cpu = process.cpu_percent(
                        interval=None
                    )

                    threads = process.num_threads()

                    status = process.status()


                    self.ram_label.config(
                        text=format_bytes(ram)
                    )

                    self.cpu_label.config(
                        text=f"{cpu:.1f}%"
                    )

                    self.threads_label.config(
                        text=str(threads)
                    )

                    self.status_label.config(
                        text=status
                    )


                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied
                ):

                    self.ram_label.config(
                        text="N/A"
                    )

                    self.cpu_label.config(
                        text="N/A"
                    )

                    self.threads_label.config(
                        text="N/A"
                    )

                    self.status_label.config(
                        text="Exited"
                    )


        self.root.after(
            1000,
            self.update_stats
        )


    # ========================================================
    # Live monitor toggle
    # ========================================================

    def toggle_monitor(self):

        self.live_monitoring = (
            not self.live_monitoring
        )

        if self.live_monitoring:

            self.monitor_button.config(
                text="⏸ Stop Live"
            )

            self.status.config(
                text="Live monitoring enabled"
            )

        else:

            self.monitor_button.config(
                text="▶ Start Live"
            )

            self.status.config(
                text="Live monitoring paused"
            )


    # ========================================================
    # Set information
    # ========================================================

    def set_information(
        self,
        text
    ):

        self.info.config(
            state="normal"
        )

        self.info.delete(
            "1.0",
            tk.END
        )

        self.info.insert(
            tk.END,
            text
        )

        self.info.config(
            state="disabled"
        )


    # ========================================================
    # Copy
    # ========================================================

    def copy_info(self):

        text = self.info.get(
            "1.0",
            tk.END
        ).strip()

        if not text:
            return

        self.root.clipboard_clear()

        self.root.clipboard_append(
            text
        )

        self.root.update()

        self.status.config(
            text="Information copied"
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = AppLens(
        root
    )

    root.mainloop()

