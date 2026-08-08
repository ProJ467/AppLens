# AppLens

AppLens is a Windows window inspector built in Python. It scans visible windows on your desktop and shows details for the selected window, including:

- window title
- process name
- PID
- position
- size
- executable path
- Features
- lists all visible windows
- displays detailed window and process information
- copies selected window info to the clipboard
- refreshes the window list on demand
# Requirements
- Windows
- Python 3.x
- psutil library

 With Win+R run
```python AppLens.py```
# Notes
- AppLens uses Windows APIs to enumerate visible windows.
- It works best when run with permissions that allow reading process information.
