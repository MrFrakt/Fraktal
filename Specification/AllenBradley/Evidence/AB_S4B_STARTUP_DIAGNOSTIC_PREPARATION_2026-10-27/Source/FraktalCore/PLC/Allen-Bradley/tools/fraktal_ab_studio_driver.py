"""Drive one hidden offline Studio 5000 Logix Designer session through its own menus.

Replaces SendKeys/UI-Automation automation with what the 2026-10-22 black-box
study qualified (notes/studio5000 in ReverseEngineerAgent): the commands a
driver may post are the ids Studio's own menu resource defines, every online
command id is refused before a message leaves this process, results are read
back with WM_GETTEXT, and the session runs hidden on a disposable copy so no
focus is ever taken. The only frame commands used are Verify Controller
(32049) and Edit > Controller Properties (32023); dialog interactions are
limited to standard button ids (IDOK/IDNO/IDCANCEL) on dialogs Studio itself
raised. The SDK is never needed and never contacted.

Subcommands:

  verify    open a disposable copy, Verify Controller, read the Error List
            summary (control 33652) plus the count buttons, emit the same
            ``fraktal.ab.studio-verify`` v1 JSON as ``fraktal_ab_studio_verify.ps1``.
  capacity  open a disposable copy, read the Controller Properties Capacity
            page, emit a ``fraktal.ab.studio-capacity-capture`` v1 JSON that the
            qualified reader ``fraktal_ab_studio_capacity.normalize`` accepts.
  import    open a copied L5X, type the absolute target path into the
            Save Imported Project As dialog, press Import, and report the
            resulting ACD. No SDK entitlement is involved.

Every mode proves the caller's source hash is unchanged and its Studio process
closed itself; a stuck process is reported, never killed.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
STUDIO_ROOT = Path(r'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU')

# Frame WM_COMMAND ids this driver may ever post. Anything else is refused,
# and the online ids Rockwell defines are refused first and by name.
VERIFY_COMMAND = 32049            # Logic > Verify Controller
CONTROLLER_PROPERTIES_COMMAND = 32023  # Edit > Controller Properties
ALLOWED_FRAME_COMMANDS = {
    VERIFY_COMMAND: 'Logic > Verify Controller',
    CONTROLLER_PROPERTIES_COMMAND: 'Edit > Controller Properties',
}
DENIED_ONLINE_COMMANDS = {
    32081: 'Clear Faults and Continue', 32082: 'Go Online', 32085: 'Upload',
    32086: 'Download', 32087: 'Program Mode', 32088: 'Run Mode',
    32089: 'Test Mode', 32093: 'Lock Controller',
}
# The menu-resource walk must land on a command this driver has qualified.
KNOWN_PROPERTIES_COMMANDS = {37: 32023, 38: 32023}
# An allow-listed id only means what the study proved it means in the
# revisions it was read from; other revisions get menu renumbering and would
# turn a "safe" id into an arbitrary - possibly online - command.
VERIFIED_REVISIONS = {37, 38}       # frame command ids (study finding F1)
IMPORT_VERIFIED_REVISIONS = {38}    # import dialog control ids (finding F3)
IDOK, IDCANCEL, IDNO = 1, 2, 7

ERRORS_PANE_ID = 33652            # RICHEDIT50W Error List summary
COUNT_BUTTON_IDS = (33648, 33649, 33650)  # "<n> Errors/Warnings/Messages"
OFFLINE_BUTTON_ID = 1000          # frame button reading "Offline"/"Online"
STATUS_PANE_ID = 59393
FILENAME_EDIT_ID = 1148           # Save Imported Project As file-name edit
REVISION_COMBO_ID = 33930         # target revision combo in the same dialog
SHEET_TAB_ID = 12320              # SysTabControl32 in Controller Properties

SUMMARY_RE = re.compile(r'Complete\s+-\s+(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\)')
COUNT_BUTTON_RE = re.compile(r'^\s*(\d+)\s+(Errors?|Warnings?|Messages?)\s*$')
SAVE_PROMPT_RE = re.compile(r'save changes', re.I)


class StudioDriverError(RuntimeError):
    """The environment or Studio refused the run; no result is claimed."""


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_summary(text):
    """(errors, warnings) from the last Error List summary line, else None."""
    if not text:
        return None
    found = SUMMARY_RE.findall(text)
    if not found:
        return None
    return int(found[-1][0]), int(found[-1][1])


def parse_count_button(text):
    """(count, kind) from a frame count button like '0 Errors', else None."""
    if not text:
        return None
    found = COUNT_BUTTON_RE.match(text)
    return (int(found.group(1)), found.group(2).lower()) if found else None


def postable_command(command):
    """Return the command's purpose, or raise: this is the whole post policy."""
    if command in DENIED_ONLINE_COMMANDS:
        raise StudioDriverError(
            f'refusing online command {command} ({DENIED_ONLINE_COMMANDS[command]})')
    if command not in ALLOWED_FRAME_COMMANDS:
        raise StudioDriverError(
            f'command {command} is not on the driver allow-list {sorted(ALLOWED_FRAME_COMMANDS)}')
    return ALLOWED_FRAME_COMMANDS[command]


def is_save_prompt(texts):
    return any(SAVE_PROMPT_RE.search(t or '') for t in texts)


def assert_safe_source(path, repo_root=REPO_ROOT, suffix='.ACD'):
    path = Path(path).resolve()
    repo_root = Path(repo_root).resolve()
    if not path.is_file() or path.suffix.lower() != suffix.lower():
        raise StudioDriverError(f'input must be an existing {suffix} file: {path}')
    if path == repo_root or repo_root in path.parents:
        raise StudioDriverError(
            f'refusing to touch {path} inside the repository; use a disposable copy')
    return path


def assert_no_running_studio():
    if logix_designer_pids():
        raise StudioDriverError(
            'a Logix Designer process is already running; close it before this isolated probe')


def logix_designer_pids():
    """Every LogixDesigner.exe pid on the machine (tasklist as a plain listing)."""
    try:
        listing = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq LogixDesigner.exe', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        raise StudioDriverError('cannot enumerate Studio processes')
    return {int(row.split('","')[1]) for row in listing.splitlines()
            if row.startswith('"LogixDesigner')}


def assert_revision_qualified(revision, mode):
    allowed = IMPORT_VERIFIED_REVISIONS if mode == 'import' else VERIFIED_REVISIONS
    if int(revision) not in allowed:
        raise StudioDriverError(
            f'Studio v{revision} command/control ids are not qualified for {mode} '
            f'(qualified: {sorted(allowed)}); refusing to post unverified ids')


def studio_executable(revision, studio_root=STUDIO_ROOT):
    exe = Path(studio_root) / f'v{revision}' / 'Bin' / 'LogixDesigner.Exe'
    if not exe.is_file():
        raise StudioDriverError(f'Logix Designer v{revision} not installed at {exe}')
    return exe


def properties_command(resource_path, revision):
    """Read Edit > Controller Properties out of LogixACENU.dll's menu resource.

    Loads the module as data only, walks menu resource 101, and requires the
    caption path 'Edit/Controller Properties' to resolve to exactly the command
    id qualified for this revision.
    """
    module = win32.load_resource_module(str(resource_path))
    try:
        matches = win32.find_menu_caption(module, 101, 'Edit/Controller Properties')
    finally:
        win32.free_resource_module(module)
    if len(matches) != 1:
        raise StudioDriverError(
            f'expected one Controller Properties command, found {matches}')
    command = matches[0]
    if KNOWN_PROPERTIES_COMMANDS.get(int(revision)) != command:
        raise StudioDriverError(
            f'Controller Properties command {command} is not qualified for v{revision}')
    return command


def build_capture(meta, snapshots, error):
    """Assemble the ``fraktal.ab.studio-capacity-capture`` v1 record.

    Pure: the live collector fills ``meta``/``snapshots`` and the qualified
    reader ``fraktal_ab_studio_capacity.normalize`` accepts the result.
    """
    return {
        'Schema': 'fraktal.ab.studio-capacity-capture', 'SchemaVersion': 1,
        **meta, 'Snapshots': snapshots, 'Error': error,
    }


if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    WINEVENTPROC = ctypes.WINFUNCTYPE(
        None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
        wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetDlgCtrlID.argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    user32.SendMessageTimeoutW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.c_void_p,
        wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    user32.SetWinEventHook.restype = wintypes.HANDLE
    user32.SetWinEventHook.argtypes = [
        wintypes.DWORD, wintypes.DWORD, wintypes.HMODULE, WINEVENTPROC,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
    user32.PeekMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
    user32.TranslateMessage.argtypes = [ctypes.c_void_p]
    user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
    user32.LoadMenuW.restype = wintypes.HMENU
    user32.LoadMenuW.argtypes = [wintypes.HMODULE, ctypes.c_void_p]
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.GetMenuItemCount.argtypes = [wintypes.HMENU]
    user32.GetSubMenu.restype = wintypes.HMENU
    user32.GetSubMenu.argtypes = [wintypes.HMENU, ctypes.c_int]
    user32.GetMenuItemID.argtypes = [wintypes.HMENU, ctypes.c_int]
    user32.GetMenuStringW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.LPWSTR, ctypes.c_int, wintypes.UINT]

    WM_GETTEXT, WM_GETTEXTLENGTH, WM_SETTEXT = 0x0D, 0x0E, 0x0C
    WM_COMMAND, WM_CLOSE = 0x111, 0x10
    PSM_SETCURSEL, PSM_GETCURRENTPAGEHWND = 0x465, 0x476
    GWL_STYLE = -16
    WS_CHILD, ES_PASSWORD = 0x40000000, 0x20
    EVENT_OBJECT_SHOW = 0x8002
    SMTO_ABORTIFHUNG = 0x2
    LOAD_LIBRARY_AS_DATA_FILE_OR_IMAGE = 0x22

    class win32:
        @staticmethod
        def window_pid(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value

        @staticmethod
        def class_name(hwnd):
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buffer, 256)
            return buffer.value

        @staticmethod
        def text(hwnd, limit=65536):
            """WM_GETTEXT via the system marshaller; password edits are skipped."""
            kind = win32.class_name(hwnd)
            if 'edit' in kind.lower() and user32.GetWindowLongW(hwnd, GWL_STYLE) & ES_PASSWORD:
                return None
            result = ctypes.c_size_t()
            if not user32.SendMessageTimeoutW(hwnd, WM_GETTEXTLENGTH, 0, None, SMTO_ABORTIFHUNG,
                                              2000, ctypes.byref(result)):
                return None
            length = min(int(result.value), limit)
            buffer = ctypes.create_unicode_buffer(length + 1)
            if not user32.SendMessageTimeoutW(hwnd, WM_GETTEXT, length + 1, buffer,
                                              SMTO_ABORTIFHUNG, 2000, ctypes.byref(result)):
                return None
            return buffer.value

        @staticmethod
        def set_text(hwnd, value):
            buffer = ctypes.create_unicode_buffer(value)
            result = ctypes.c_size_t()
            ok = bool(user32.SendMessageTimeoutW(hwnd, WM_SETTEXT, 0, buffer, SMTO_ABORTIFHUNG,
                                                 2000, ctypes.byref(result)))
            return ok and win32.text(hwnd) == value

        @staticmethod
        def describe(hwnd, skip_password=True):
            """A capture row: the qualified PowerShell collector's Node shape."""
            kind = win32.class_name(hwnd)
            skipped = (skip_password and 'edit' in kind.lower()
                       and user32.GetWindowLongW(hwnd, GWL_STYLE) & ES_PASSWORD)
            name = None if skipped else win32.text(hwnd)
            return {
                'Handle': int(hwnd), 'Parent': int(user32.GetParent(hwnd) or 0),
                'Id': user32.GetDlgCtrlID(hwnd), 'Name': name, 'Class': kind,
                'Visible': bool(user32.IsWindowVisible(hwnd)), 'PasswordSkipped': bool(skipped),
            }

        @staticmethod
        def top_hwnds(pid):
            found = []

            def visit(hwnd, _):
                if win32.window_pid(hwnd) == pid:
                    found.append(hwnd)
                return True
            user32.EnumWindows(WNDENUMPROC(visit), 0)
            return found

        @staticmethod
        def child_hwnds(root):
            found = []

            def visit(child, _):
                found.append(child)
                return True
            user32.EnumChildWindows(root, WNDENUMPROC(visit), 0)
            return found

        @staticmethod
        def send(hwnd, message, wparam=0, lparam=0, timeout_ms=5000):
            result = ctypes.c_size_t()
            ok = user32.SendMessageTimeoutW(hwnd, message, wparam, ctypes.c_void_p(lparam),
                                            SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result))
            return int(result.value) if ok else None

        @staticmethod
        def post(hwnd, message, wparam=0, lparam=0):
            if not user32.PostMessageW(hwnd, message, wparam, lparam):
                raise StudioDriverError(f'PostMessage({message:#x}) to {int(hwnd)} failed')

        @staticmethod
        def control(pid_or_hwnd, ctrl_id, cls_prefix=None, root=None):
            """The unique control with this id under root (default: the frame tree)."""
            candidates = []
            tops = [root] if root else win32.top_hwnds(pid_or_hwnd)
            for top in tops:
                for child in win32.child_hwnds(top):
                    if user32.GetDlgCtrlID(child) == ctrl_id:
                        if cls_prefix and not win32.class_name(child).lower().startswith(cls_prefix.lower()):
                            continue
                        candidates.append(child)
            if len(candidates) != 1:
                return None
            return candidates[0]

        @staticmethod
        def load_resource_module(path):
            module = kernel32.LoadLibraryExW(path, None, LOAD_LIBRARY_AS_DATA_FILE_OR_IMAGE)
            if not module:
                raise StudioDriverError(f'cannot load menu resources from {path}')
            return module

        @staticmethod
        def free_resource_module(module):
            kernel32.FreeLibrary(module)

        @staticmethod
        def find_menu_caption(module, resource, caption_path):
            """Menu item ids whose caption path (with & stripped) matches."""
            menu = user32.LoadMenuW(module, resource)
            if not menu:
                raise StudioDriverError(f'menu resource {resource} missing')
            found = []
            try:
                def walk(submenu, path):
                    for index in range(user32.GetMenuItemCount(submenu)):
                        buffer = ctypes.create_unicode_buffer(1024)
                        user32.GetMenuStringW(submenu, index, buffer, 1024, 0x400)  # MF_BYPOSITION
                        here = path + [buffer.value.replace('&', '')]
                        if '/'.join(here) == caption_path:
                            found.append(user32.GetMenuItemID(submenu, index))
                        child = user32.GetSubMenu(submenu, index)
                        if child:
                            walk(child, here)
                walk(menu, [])
            finally:
                user32.DestroyMenu(menu)
            return found
else:
    win32 = None


class HiddenStudio:
    """One hidden Logix Designer launch whose top-level windows are kept hidden.

    The process is started with a hidden show-state and an EVENT_OBJECT_SHOW
    hook scoped to its pid re-hides anything it tries to show; no focus is
    ever requested. While waiting, this thread pumps messages so the hook and
    our SendMessageTimeout calls are delivered.

    Studio may spawn helper LogixDesigner.exe processes that outlive the pid
    subprocess tracks (seen on L5X open), so every LogixDesigner pid that
    appears during the session is adopted: callers must first prove none was
    running (assert_no_running_studio), then this class owns and closes them
    all. Windows are only ever enumerated for adopted pids.
    """

    def __init__(self, exe, document):
        if win32 is None:
            raise StudioDriverError('the Studio driver only runs on Windows')
        self.exe, self.document = str(exe), str(document)
        self.process = None
        self.hook = None
        self.owned_pids = set()
        self.dialog_log = []
        self._seen_dialogs = set()
        self._callback = WINEVENTPROC(self._on_show)

    def _on_show(self, hook, event, hwnd, object_id, child_id, thread, when):
        if hwnd and object_id == 0 and not user32.GetWindowLongW(hwnd, GWL_STYLE) & WS_CHILD:
            user32.ShowWindow(hwnd, 0)  # SW_HIDE

    def __enter__(self):
        baseline = logix_designer_pids()
        if baseline:
            raise StudioDriverError(
                f'Logix Designer already running (pids {sorted(baseline)}); '
                'close it before this isolated probe')
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = 0  # SW_HIDE
        self.process = subprocess.Popen([self.exe, self.document], startupinfo=info)
        self.owned_pids = {self.process.pid}
        self.hook = user32.SetWinEventHook(
            EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW, None, self._callback, self.process.pid, 0, 0)
        if not self.hook:
            self.process.kill()
            raise StudioDriverError('visibility hook failed; not driving a visible Studio')
        return self

    def __exit__(self, *exc):
        if self.hook:
            user32.UnhookWinEvent(self.hook)
        return False

    def adopt_new_pids(self):
        """Adopt any LogixDesigner pid that appeared since the empty baseline."""
        self.owned_pids |= logix_designer_pids()

    def pump(self, seconds):
        message = (ctypes.c_byte * 48)()
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            while user32.PeekMessageW(message, None, 0, 0, 1):
                user32.TranslateMessage(message)
                user32.DispatchMessageW(message)
            time.sleep(0.01)

    def wait(self, predicate, seconds, step=0.2):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            value = predicate()
            if value:
                return value
            if self.process.poll() is not None:
                return None
            self.pump(step)
        return None

    def exited(self):
        return self.process.poll() is not None and not (self.owned_pids & logix_designer_pids())

    def windows(self, cls=None, text_pred=None):
        found = []
        for hwnd in self.all_top_hwnds():
            row = win32.describe(hwnd, skip_password=False)
            if cls and row['Class'] != cls:
                continue
            if text_pred and not text_pred(row['Name'] or ''):
                continue
            found.append(row)
        return found

    def all_top_hwnds(self):
        """Top-level windows of every adopted pid."""
        found = []
        for pid in self.owned_pids:
            found.extend(win32.top_hwnds(pid))
        return found

    def note_new_dialogs(self):
        """Record any newly appeared #32770 dialog with its control texts."""
        for hwnd in self.all_top_hwnds():
            row = win32.describe(hwnd, skip_password=False)
            if row['Class'] != '#32770' or row['Handle'] in self._seen_dialogs:
                continue
            self._seen_dialogs.add(row['Handle'])
            kids = [win32.describe(child) for child in win32.child_hwnds(hwnd)]
            self.dialog_log.append({
                'title': row['Name'], 'handle': row['Handle'],
                'texts': [kid['Name'] for kid in kids if kid['Name']],
                'controls': kids, 'seenUtc': utc_now(),
            })

    def save_prompt_visible(self):
        return any(is_save_prompt(dialog['texts']) for dialog in self.dialog_log)

    def answer_save_prompt(self, answer=IDNO):
        """Press No (default) on every save-changes prompt Studio raised."""
        answered = 0
        for dialog in self.dialog_log:
            if is_save_prompt(dialog['texts']):
                win32.post(dialog['handle'], WM_COMMAND, answer, 0)
                answered += 1
        return answered

    def post_frame_command(self, frame_hwnd, command):
        purpose = postable_command(command)
        win32.post(frame_hwnd, WM_COMMAND, command, 0)
        return purpose

    def wait_frame(self, document_name, seconds):
        """The main frame once it shows the opened project in its title."""
        marker = f'in {document_name}'
        return self.wait(lambda: next(
            (row for row in self.windows()
             if (row['Name'] or '').startswith('Logix Designer - ') and marker in row['Name']),
            None), seconds)

    def offline_state(self, frame_hwnd):
        button = win32.control(None, OFFLINE_BUTTON_ID, root=frame_hwnd)
        if not button:
            return None
        return (win32.text(button) or '').strip()

    def find_control(self, ctrl_id, cls_prefix=None):
        """The unique control with this id anywhere in this Studio launch.

        Docked panes like the Error List need not live under the main frame's
        hwnd, so the search covers every adopted pid's windows.
        """
        candidates = []
        for top in self.all_top_hwnds():
            for child in win32.child_hwnds(top):
                if user32.GetDlgCtrlID(child) == ctrl_id:
                    if cls_prefix and not win32.class_name(child).lower().startswith(cls_prefix.lower()):
                        continue
                    candidates.append(child)
        return candidates[0] if len(candidates) == 1 else None

    def errors_pane(self, limit=65536):
        pane = self.find_control(ERRORS_PANE_ID, cls_prefix='RICHEDIT')
        return win32.text(pane, limit) if pane else None

    def count_buttons(self):
        found = {}
        for ctrl_id in COUNT_BUTTON_IDS:
            button = self.find_control(ctrl_id)
            if button:
                found[str(ctrl_id)] = win32.text(button)
        return found

    def close_clean(self, frame_hwnd=None, seconds=90):
        """WM_CLOSE everything we own, answering save prompts with No; never kill.

        Adopts helper processes first so nothing this launch spawned survives
        as a hidden zombie. Returns the launcher's exit code when every adopted
        pid has ended itself, else None.
        """
        self.adopt_new_pids()
        if self.exited():
            return self.process.poll()
        for hwnd in ([frame_hwnd] if frame_hwnd else self.all_top_hwnds()):
            win32.post(hwnd, WM_CLOSE, 0, 0)
        until = time.monotonic() + seconds
        while time.monotonic() < until and not self.exited():
            self.pump(0.2)
            self.note_new_dialogs()
            if self.save_prompt_visible():
                self.answer_save_prompt(IDNO)
            self.adopt_new_pids()
        return self.process.poll() if self.exited() else None

    def dialog_evidence(self):
        """Recent dialog titles/texts for error messages."""
        return [f'{d["title"]!r} {d["texts"][:4]}' for d in self.dialog_log[-4:]]


def make_workspace(kind):
    work = Path(tempfile.gettempdir()) / 'FraktalAbStudioDriver' / f'{kind}_{uuid.uuid4().hex}'
    work.mkdir(parents=True)
    return work


def disposable_copy(source, work, prefix):
    review = work / f'{prefix}_{uuid.uuid4().hex[:8]}{source.suffix}'
    shutil.copyfile(source, review)
    return review


def open_offline_session(session, review, timeout):
    """Shared prelude on an entered session: wait for the frame, prove Offline."""
    frame = session.wait_frame(Path(review).name, timeout)
    if not frame:
        raise StudioDriverError(
            f'Studio did not open {review.name} within {timeout} s '
            f'(exit={session.process.poll()})')
    session.pump(1)
    state = session.offline_state(frame['Handle'])
    if state != 'Offline':
        raise StudioDriverError(
            f'project must be Offline before driving it; button reads {state!r}')
    return frame


def run_verify(args):
    assert_revision_qualified(args.revision, 'verify')
    source = assert_safe_source(args.acd)
    exe = studio_executable(args.revision, args.studio_root)
    assert_no_running_studio()
    input_sha = sha256_of(source)
    work = make_workspace('verify')
    review = disposable_copy(source, work, 'Review')
    started = utc_now()
    closed, summary_text, errors = False, None, None
    count_buttons, status_text, cross_check = {}, None, None
    dialogs = []
    with HiddenStudio(exe, review) as studio:
        frame = None
        try:
            frame = open_offline_session(studio, review, args.open_timeout)
            studio.post_frame_command(frame['Handle'], VERIFY_COMMAND)

            def summary():
                value = studio.errors_pane()
                return value if value and SUMMARY_RE.search(value) else None
            summary_text = studio.wait(summary, args.timeout, step=0.5)
            if summary_text is None:
                evidence = '; '.join(studio.dialog_evidence())
                raise StudioDriverError(
                    f'Verify did not complete within {args.timeout} s'
                    + (f'; dialogs seen: {evidence}' if evidence else ''))
            errors, warnings = parse_summary(summary_text)
            count_buttons = studio.count_buttons()
            status = studio.find_control(STATUS_PANE_ID)
            status_text = win32.text(status) if status else None
            parsed = {}
            for value in (parse_count_button(t) for t in count_buttons.values()):
                if value:
                    parsed[value[1]] = value[0]
            cross_check = None
            if 'errors' in parsed and 'warnings' in parsed:
                cross_check = parsed['errors'] == errors and parsed['warnings'] == warnings
        finally:
            code = studio.close_clean(frame['Handle'] if frame else None)
            closed = studio.exited()
            dialogs = studio.dialog_log
    if not closed:
        raise StudioDriverError(
            'Studio did not close itself; a hidden LogixDesigner process remains '
            'and must be closed manually before the next run')
    source_after = sha256_of(source)
    result = {
        'Schema': 'fraktal.ab.studio-verify', 'SchemaVersion': 1,
        'Driver': 'fraktal_ab_studio_driver', 'DriverMode': 'hidden-wmcommand',
        'StudioRevision': args.revision, 'StudioPath': str(exe),
        'Project': source.name, 'InputPath': str(source),
        'InputSha256': input_sha, 'InputUnchanged': input_sha == source_after,
        'SourceOpenedDirectly': False, 'ReviewCopy': str(review),
        'Errors': errors, 'Warnings': warnings,
        'ExpectedErrors': args.expected_errors, 'ExpectedWarnings': args.expected_warnings,
        'CountsMatch': errors == args.expected_errors and warnings == args.expected_warnings,
        'CountButtons': count_buttons, 'SummaryCrossCheck': cross_check,
        'MessageCountText': count_buttons.get(str(COUNT_BUTTON_IDS[2])),
        'StatusText': status_text, 'Summary': summary_text,
        'ClosedCleanly': True, 'ExitCode': code,
        'StartedUtc': started, 'FinishedUtc': utc_now(),
        'Dialogs': [{'title': d['title'], 'texts': d['texts']} for d in dialogs],
    }
    passed = (result['InputUnchanged'] and result['CountsMatch']
              and result['SummaryCrossCheck'] is not False)
    result['Passed'] = bool(passed)
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


def capacity_snapshot(sheet_hwnd):
    """Rows of the Standard Capacity panel plus the page name proof."""
    tree = [win32.describe(child) for child in win32.child_hwnds(sheet_hwnd)]
    standard = [row for row in tree
                if row['Class'] == '#32770' and row['Name'] == 'MemCapacityDlg_Standard']
    page = [row for row in tree if row['Class'] == '#32770' and row['Name'] == 'Capacity']
    if len(standard) != 1 or len(page) != 1:
        raise StudioDriverError(
            f'Capacity page controls missing or ambiguous '
            f'(standard={len(standard)}, page={len(page)})')
    rows = [row for row in tree if row['Parent'] == standard[0]['Handle']]
    return page[0]['Name'], standard[0]['Handle'], rows


def run_capacity(args):
    assert_revision_qualified(args.revision, 'capacity')
    source = assert_safe_source(args.acd)
    output = Path(args.output)
    if output.exists():
        raise StudioDriverError(f'new evidence output required: {output}')
    exe = studio_executable(args.revision, args.studio_root)
    resource = exe.parent / 'LogixACENU.dll'
    if not resource.is_file():
        raise StudioDriverError(f'menu resource missing: {resource}')
    command = properties_command(resource, args.revision)
    assert_no_running_studio()
    source_sha = sha256_of(source)
    work = make_workspace('capacity')
    review = disposable_copy(source, work, 'Capacity')
    review_sha = sha256_of(review)
    started, snapshots, failure = utc_now(), [], None
    closed, offline, frame_title, process_id = False, None, '', 0
    dialogs = []
    try:
        with HiddenStudio(exe, review) as studio:
            frame = None
            try:
                process_id = studio.process.pid
                frame = open_offline_session(studio, review, args.open_timeout)
                offline, frame_title = True, frame['Name']
                studio.post_frame_command(frame['Handle'], command)
                sheet = studio.wait(
                    lambda: next((row for row in studio.windows(
                        cls='#32770',
                        text_pred=lambda t: t.startswith('Controller Properties'))), None),
                    30)
                if not sheet:
                    raise StudioDriverError('Controller Properties did not open')
                studio.pump(1)
                tabs = [row for row in (win32.describe(child) for child in win32.child_hwnds(sheet['Handle']))
                        if row['Class'] == 'SysTabControl32' and row['Id'] == SHEET_TAB_ID]
                if len(tabs) != 1:
                    raise StudioDriverError('Controller Properties tab control missing')
                # Locate the Capacity page by caption, not by tab index: page
                # order differs per controller type (study finding F4).
                selected = False
                for index in range(40):
                    if not win32.send(sheet['Handle'], PSM_SETCURSEL, index, 0):
                        break
                    studio.pump(0.5)
                    page_hwnd = win32.send(sheet['Handle'], PSM_GETCURRENTPAGEHWND)
                    if not page_hwnd:
                        continue
                    if (win32.class_name(page_hwnd) == '#32770'
                            and win32.text(page_hwnd) == 'Capacity'):
                        selected = True
                        break
                if not selected:
                    raise StudioDriverError('no Controller Properties page is named Capacity')
                studio.pump(0.25)
                for _ in range(2):
                    page_name, standard_parent, rows = capacity_snapshot(sheet['Handle'])
                    snapshots.append({
                        'CapturedUtc': utc_now(), 'PageName': page_name,
                        'StandardParent': standard_parent, 'Controls': rows,
                    })
                    studio.pump(0.25)
                win32.post(sheet['Handle'], WM_COMMAND, IDCANCEL, 0)
                studio.pump(0.5)
            finally:
                studio.close_clean(frame['Handle'] if frame else None)
                closed = studio.exited()
                dialogs = studio.dialog_log
        if not closed:
            failure = 'our review process did not close itself'
    except Exception as error:  # recorded like the qualified collector records it
        failure = f'{type(error).__name__}: {error}'
    source_after = sha256_of(source)
    capture = build_capture({
        'Offline': offline, 'SourceAcd': str(source), 'SourceSha256': source_sha,
        'SourceSha256After': source_after,
        'ReviewCopy': str(review), 'ReviewInitialSha256': review_sha,
        'StudioPath': str(exe), 'StudioSha256': sha256_of(exe),
        'MenuResource': str(resource), 'MenuResourceSha256': sha256_of(resource),
        'PropertiesCommand': command,
        'ProcessId': process_id, 'ProcessClosed': closed, 'FrameTitle': frame_title,
        'Collector': 'fraktal_ab_studio_driver',
        'StartedUtc': started, 'FinishedUtc': utc_now(),
    }, snapshots, failure)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(capture, indent=2), encoding='utf-8')
    print(json.dumps({
        'Schema': capture['Schema'], 'Offline': offline, 'ProcessClosed': closed,
        'SourceUnchanged': source_sha == source_after,
        'Snapshots': len(snapshots), 'Error': failure,
        'Output': str(output),
    }))
    clean = (not failure and closed and source_sha == source_after and len(snapshots) == 2)
    return 0 if clean else 1


def run_import(args):
    assert_revision_qualified(args.revision, 'import')
    source = assert_safe_source(args.l5x, suffix='.L5X')
    output = Path(args.output).resolve()
    if output.exists():
        raise StudioDriverError(f'import target already exists: {output}')
    if output == REPO_ROOT or REPO_ROOT in output.parents:
        raise StudioDriverError(f'refusing to write an ACD inside the repository: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    exe = studio_executable(args.revision, args.studio_root)
    assert_no_running_studio()
    source_sha = sha256_of(source)
    work = make_workspace('import')
    l5x = disposable_copy(source, work, 'L5x')
    started, summary_text, revision_text = utc_now(), None, None
    closed, dialogs = False, []
    with HiddenStudio(exe, l5x) as studio:
        frame = None
        try:
            dialog = studio.wait(lambda: next(
                (row for row in studio.windows(
                    cls='#32770', text_pred=lambda t: t == 'Save Imported Project As')), None),
                args.open_timeout)
            if not dialog:
                raise StudioDriverError('Save Imported Project As dialog did not appear')
            studio.pump(1)
            edits = [child for child in win32.child_hwnds(dialog['Handle'])
                     if user32.GetDlgCtrlID(child) == FILENAME_EDIT_ID
                     and win32.class_name(child) == 'Edit']
            if len(edits) != 1:
                raise StudioDriverError('import file-name edit not unique')
            # The dialog opens in Studio's last-used folder, so the full
            # absolute path must be set (study finding F3).
            if not win32.set_text(edits[0], str(output)):
                raise StudioDriverError('could not set the absolute import path')
            combo = win32.control(None, REVISION_COMBO_ID, root=dialog['Handle'])
            revision_text = win32.text(combo) if combo else None
            win32.post(dialog['Handle'], WM_COMMAND, IDOK, 0)

            def summary():
                value = studio.errors_pane()
                if value and 'Importing' in value and SUMMARY_RE.search(value):
                    return value
                return None
            summary_text = studio.wait(summary, args.timeout, step=0.5)
            if summary_text is None:
                evidence = '; '.join(studio.dialog_evidence())
                raise StudioDriverError(
                    f'import did not complete within {args.timeout} s'
                    + (f'; dialogs seen: {evidence}' if evidence else ''))
            studio.pump(2)
            frame = studio.wait(lambda: next(
                (row for row in studio.windows()
                 if (row['Name'] or '').startswith('Logix Designer - ')), None), 60)
        finally:
            code = studio.close_clean(frame['Handle'] if frame else None)
            closed = studio.exited()
            dialogs = studio.dialog_log
    if not closed:
        raise StudioDriverError(
            'Studio did not close itself; a hidden LogixDesigner process remains '
            'and must be closed manually before the next run')
    source_after = sha256_of(source)
    imported = output.is_file()
    errors, warnings = parse_summary(summary_text) if summary_text else (None, None)
    result = {
        'Schema': 'fraktal.ab.studio-import', 'SchemaVersion': 1,
        'Driver': 'fraktal_ab_studio_driver', 'StudioRevision': args.revision,
        'StudioPath': str(exe), 'SourceL5x': str(source), 'SourceSha256': source_sha,
        'SourceSha256After': source_after, 'SourceUnchanged': source_sha == source_after,
        'SourceOpenedDirectly': False, 'WorkL5x': str(l5x),
        'ImportedAcd': str(output), 'ImportedAcdExists': imported,
        'ImportedAcdSha256': sha256_of(output) if imported else None,
        'ImportedAcdBytes': output.stat().st_size if imported else None,
        'TargetRevisionText': revision_text,
        'Errors': errors, 'Warnings': warnings, 'Summary': summary_text,
        'ClosedCleanly': True, 'ExitCode': code,
        'StartedUtc': started, 'FinishedUtc': utc_now(),
        'Dialogs': [{'title': d['title'], 'texts': d['texts']} for d in dialogs],
    }
    result['Passed'] = bool(
        result['SourceUnchanged'] and imported and errors == 0 and warnings == 0)
    print(json.dumps(result, indent=2))
    return 0 if result['Passed'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--studio-root', type=Path, default=STUDIO_ROOT,
                        help='Logix Designer ENU install root (default: %(default)s)')
    sub = parser.add_subparsers(dest='command', required=True)

    verify = sub.add_parser('verify', help='hidden Verify Controller on a disposable copy')
    verify.add_argument('--acd', required=True, type=Path)
    verify.add_argument('--revision', required=True, type=int)
    verify.add_argument('--expected-errors', type=int, default=0)
    verify.add_argument('--expected-warnings', type=int, default=0)
    verify.add_argument('--timeout', type=int, default=240,
                        help='seconds to wait for Verify to complete')
    verify.add_argument('--open-timeout', type=int, default=300)
    verify.set_defaults(run=run_verify)

    capacity = sub.add_parser('capacity', help='hidden Capacity capture on a disposable copy')
    capacity.add_argument('--acd', required=True, type=Path)
    capacity.add_argument('--revision', type=int, default=38)
    capacity.add_argument('--output', required=True, type=Path,
                          help='new file for the fraktal.ab.studio-capacity-capture JSON')
    capacity.add_argument('--open-timeout', type=int, default=300)
    capacity.set_defaults(run=run_capacity)

    imp = sub.add_parser('import', help='hidden L5X import to a new ACD without the SDK')
    imp.add_argument('--l5x', required=True, type=Path)
    imp.add_argument('--output', required=True, type=Path, help='ACD path Studio will create')
    imp.add_argument('--revision', type=int, default=38)
    imp.add_argument('--timeout', type=int, default=600)
    imp.add_argument('--open-timeout', type=int, default=300)
    imp.set_defaults(run=run_import)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except StudioDriverError as error:
        print(json.dumps({'Schema': 'fraktal.ab.studio-driver-error',
                          'Error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
