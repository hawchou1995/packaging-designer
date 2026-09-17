"""Isolated programmatic Qt button test; dummy products, NOT geometry or OS-open acceptance.
Run only with D:/Tools/venvs/fefco0210/Scripts/python.exe -B.
No production functions for export/settings/refresh/signature are replaced.
"""
import os
import sys
from pathlib import Path
import hashlib
import json
import traceback
import time

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
assert PROJECT.as_posix() == 'D:/Tools/tmp/packapp'
assert Path(sys.executable).resolve() == Path('D:/Tools/venvs/fefco0210/Scripts/python.exe').resolve()
sys.dont_write_bytecode = True
os.chdir(ROOT)
for key, sub in {'TEMP': 'temp', 'TMP': 'temp', 'LOCALAPPDATA': 'localappdata',
                 'APPDATA': 'appdata', 'USERPROFILE': 'profile', 'HOME': 'profile',
                 'MPLCONFIGDIR': 'mpl', 'XDG_CACHE_HOME': 'cache'}.items():
    folder = ROOT / sub
    folder.mkdir(exist_ok=True)
    os.environ[key] = str(folder)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
LOG = (ROOT / 'experiment.log').open('w', encoding='utf-8', buffering=1)

def emit(event, **data):
    line = json.dumps({'event': event, **data}, ensure_ascii=False, default=str)
    print(line, flush=True)
    LOG.write(line + '\n')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inside(path):
    try:
        Path(path).resolve().relative_to(ROOT)
        return True
    except (ValueError, TypeError):
        return False

blocked = []
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes, os.PathLike)) and (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
            if not inside(os.fsdecode(path)):
                blocked.append([event, str(path)])
                raise RuntimeError('WRITE OUTSIDE ISOLATION: ' + str(path))
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir'):
        if not inside(args[0]):
            blocked.append([event, str(args[0])])
            raise RuntimeError('MUTATION OUTSIDE ISOLATION: ' + str(args[0]))
    elif event in ('os.rename', 'os.replace'):
        if not all(inside(p) for p in args[:2]):
            blocked.append([event, str(args[:2])])
            raise RuntimeError('RENAME OUTSIDE ISOLATION')
    elif event in ('os.startfile', 'os.startfile/2', 'subprocess.Popen', 'os.system', 'socket.connect'):
        blocked.append([event, str(args)])
        raise RuntimeError('EXTERNAL ACTION BLOCKED: ' + event)

# This protects Python-level operations, not a claim of an OS sandbox.
sys.addaudithook(audit)
source_paths = ['app.py', 'ui/pages.py', 'ui/settings.py', 'ui/dialogs.py',
                'ui/widgets.py', 'ui/theme.py', 'backend.py', 'price_lib.py', 'flute_lib.py']
before = {name: digest(PROJECT / name) for name in source_paths}
(ROOT / 'source_before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
result = {'scope': 'offscreen programmatic buttons; dummy files; no geometry generation; no OS opening',
          'root': str(ROOT), 'python': sys.executable, 'checks': [], 'exports': [],
          'snapshots': {}, 'open_requests': [], 'source_before': before}

def check(name, ok, **details):
    item = {'name': name, 'pass': bool(ok), **details}
    result['checks'].append(item)
    emit('check', **item)

slot_errors = []
def exception_hook(tp, val, tb):
    text = ''.join(traceback.format_exception(tp, val, tb))
    slot_errors.append(text)
    emit('slot_exception', traceback=text)
sys.excepthook = exception_hook

try:
    from PySide6.QtCore import QSettings, QTimer, Qt
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton
    import PySide6
    def forbidden(*args, **kwargs):
        blocked.append(['Qt external dialog/open', repr(args)])
        raise RuntimeError('Directory dialog / external opening prohibited')
    QFileDialog.getExistingDirectory = forbidden
    QDesktopServices.openUrl = forbidden
    sys.path.insert(0, str(PROJECT / 'ui'))
    sys.path.insert(0, str(PROJECT))
    import settings
    ini = ROOT / 'settings.ini'
    initial = ROOT / 'initial_default'
    initial.mkdir()
    q = QSettings(str(ini), QSettings.IniFormat)
    q.setFallbacksEnabled(False)
    q.setValue('outdir', initial.as_posix())
    q.setValue('prefix', '')
    q.setValue('open_after', True)
    q.sync()
    settings_factories = []
    def isolated_qsettings(*args, **kwargs):
        settings_factories.append({'requested_args': list(args), 'actual_ini': str(ini)})
        isolated = QSettings(str(ini), QSettings.IniFormat)
        isolated.setFallbacksEnabled(False)
        return isolated
    # Replace ONLY the storage boundary; real Settings.__init__/save remain intact.
    settings.QSettings = isolated_qsettings
    import app as production
    import pages
    import widgets
    import dialogs
    phase = 'construct'
    def record_open(path):
        item = {'phase': phase, 'requested_path': str(path), 'exists': Path(path).exists(),
                'is_directory': Path(path).is_dir(), 'os_open_verified': False,
                'return_semantics': 'synthetic existence bool, not OS open result'}
        result['open_requests'].append(item)
        emit('open_request', **item)
        return item['exists']
    pages.open_path = record_open
    widgets.open_path = record_open
    counts = {}
    tracked = {('app.py', 'on_settings'), ('dialogs.py', 'on_save'), ('settings.py', 'save'),
               ('pages.py', 'on_export'), ('pages.py', 'on_open_main'), ('pages.py', '_on_generated')}
    def profile(frame, event, arg):
        pair = (Path(frame.f_code.co_filename).name, frame.f_code.co_name)
        if event == 'call' and pair in tracked:
            key = '|'.join(pair)
            counts[key] = counts.get(key, 0) + 1
    sys.setprofile(profile)
    qa = QApplication([])
    qa.setApplicationName('PackagingDesignerIsolatedExportTest')
    qa.setOrganizationName('IsolatedExperiment')
    qa.setStyleSheet(production.theme.qss())
    window = production.MainWindow()
    window.show()  # offscreen only; never desktop/window acceptance
    qa.processEvents()
    emit('environment', python=sys.executable, pyside=PySide6.__version__, platform=qa.platformName(),
         qsettings_file=window.settings.q.fileName(), temp_root=pages.TMP_ROOT,
         replacements=['settings.QSettings -> explicit isolated INI', 'pages/widgets.open_path -> recorder',
                       'QFileDialog.getExistingDirectory/QDesktopServices.openUrl -> fail-closed guard'])
    check('isolated_settings_and_temp', inside(window.settings.q.fileName()) and inside(pages.TMP_ROOT))
    check('real_four_pages', [type(p).__name__ for p in window.pages] == ['SheetPage', 'BlockPage', 'GridPage', 'BoxPage'])

    def snapshot(label):
        data = [{'page': type(p).__name__, 'out_edit': p.out_edit.text(), '_outdir': p._outdir,
                 'settings_outdir': p.settings.outdir,
                 'file_list': [p.file_list.item(i).toolTip() for i in range(p.file_list.count())],
                 '_gen_files': list(p._gen_files), 'status': p.busy.status.text()}
                for p in window.pages]
        result['snapshots'][label] = data
        emit('snapshot', label=label, pages=data)
        return data

    def button(page, label):
        hits = [b for b in page.findChildren(QPushButton) if b.text() == label]
        assert len(hits) == 1, (label, len(hits))
        assert hits[0].isEnabled(), label
        return hits[0]

    fixtures = {}
    destinations = {}
    def click_export(p, target, expected_names, stage):
        global phase
        phase = stage
        assert p._gen_sig == p.sig(), 'Fixture signature must match real current UI'
        assert p.btn_exp.isEnabled(), 'Do not force button enabled'
        assert not target.exists() or not any(target.iterdir()), 'Fresh destination required'
        p.btn_exp.click()
        qa.processEvents()
        checks = []
        for src, name in zip(fixtures[p.temp_key], expected_names):
            dst = target / name
            same = dst.is_file() and dst.read_bytes() == src.read_bytes()
            checks.append({'source': str(src), 'destination': str(dst), 'exists': dst.is_file(),
                           'bytes_equal': same, 'source_sha256': digest(src),
                           'destination_sha256': digest(dst) if dst.is_file() else None})
        actual = sorted(x.name for x in target.iterdir()) if target.exists() else []
        entry = {'phase': stage, 'page': type(p).__name__, 'out_edit': p.out_edit.text(),
                 'expected_names': expected_names, 'actual_names': actual,
                 'files': checks, 'status': p.busy.status.text()}
        result['exports'].append(entry)
        emit('export', **entry)
        check(stage + '.copy_contents_and_exact_target', all(x['bytes_equal'] for x in checks) and actual == sorted(expected_names))
        listed = [p.file_list.item(i).toolTip() for i in range(p.file_list.count())]
        check(stage + '.list_points_to_export', [Path(x) for x in listed] == [target / n for n in expected_names])
        check(stage + '.auto_open_request_target', Path(result['open_requests'][-1]['requested_path']) == target and result['open_requests'][-1]['phase'] == stage)
        phase = stage + '.open_directory'
        button(p, '打开目录').click()
        check(stage + '.open_directory_matches_edit', Path(result['open_requests'][-1]['requested_path']) == target)
        phase = stage + '.open_drawing'
        button(p, '打开图纸').click()
        request = Path(result['open_requests'][-1]['requested_path'])
        check(stage + '.open_drawing_is_export_copy', request == target / expected_names[0],
              actual=str(request), expected=str(target / expected_names[0]),
              requests_original_dummy=request == fixtures[p.temp_key][0])

    snapshot('initial')
    for idx, p in enumerate(window.pages):
        window.group.button(idx).click()
        qa.processEvents()
        source = ROOT / 'generated_dummy' / p.temp_key
        source.mkdir(parents=True)
        marker = 'gen-V1' if p.temp_key == 'grid' else 'gen'
        names = [marker + '_' + p.preview_name + '.pdf', marker + '_轮廓.dxf', marker + '_模型.step']
        paths = []
        for name in names:
            path = source / name
            path.write_bytes(('DUMMY ONLY; NOT A VALID GENERATED DRAWING OR MODEL\n' + ROOT.name + '\n' + p.temp_key + '\n' + name + '\n').encode('utf-8'))
            paths.append(path)
        fixtures[p.temp_key] = paths
        p._on_generated(production.pages.backend.Result([], []) if False else pages.backend.Result([str(x) for x in paths], []), p.sig(), 'gen')
        target = ROOT / 'manual_exports' / (p.temp_key + ' 中文 目录')
        p.out_edit.setText(target.as_posix())
        prefix = '' if idx == 0 else '隔离' + str(idx)
        p.prefix_edit.setText(prefix)
        if idx == 0:
            expected = [p.preview_name + '.pdf', '轮廓.dxf', '模型.step']
        elif p.temp_key == 'grid':
            expected = [prefix + '-V1_' + p.preview_name + '.pdf', prefix + '-V1_轮廓.dxf', prefix + '-V1_模型.step']
        else:
            expected = [prefix + '_' + p.preview_name + '.pdf', prefix + '_轮廓.dxf', prefix + '_模型.step']
        destinations[p.temp_key] = (target, expected)
        click_export(p, target, expected, 'manual.' + p.temp_key)
    state = snapshot('after_four_independent_exports')
    check('four_page_directories_can_diverge', len({x['out_edit'] for x in state}) == 4 and len({x['_outdir'] for x in state}) == 4)
    check('page_export_does_not_save_default', window.settings.outdir == initial.as_posix())

    # Exercise actual icon clicked -> MainWindow.on_settings -> real QDialog.exec ->
    # real Save button -> SettingsDialog.on_save -> Settings.save -> real return/apply loop.
    saved_default = ROOT / 'dialog_saved_default'
    phase = 'settings_dialog'
    dialog_events = []
    def drive_dialog():
        try:
            dlg = qa.activeModalWidget()
            assert isinstance(dlg, dialogs.SettingsDialog), type(dlg)
            dlg.e_out.setText(saved_default.as_posix())
            dlg.c_open.setChecked(True)
            button(dlg, '保存').click()
            dialog_events.append({'class': type(dlg).__name__, 'result': dlg.result(), 'saved': dlg.settings.outdir})
        except Exception:
            exception_hook(*sys.exc_info())
            modal = qa.activeModalWidget()
            if modal is not None:
                modal.reject()
    watchdog = QTimer()
    watchdog.setSingleShot(True)
    def timeout_dialog():
        slot_errors.append('Settings dialog watchdog timeout')
        modal = qa.activeModalWidget()
        if modal is not None:
            modal.reject()
    watchdog.timeout.connect(timeout_dialog)
    watchdog.start(10000)
    QTimer.singleShot(0, drive_dialog)
    window.icon_btn.click()
    watchdog.stop()
    qa.processEvents()
    state = snapshot('after_real_settings_save')
    emit('settings_dialog_calls', events=dialog_events, calls=counts, storage=settings_factories)
    check('real_settings_save_chain_called', all(counts.get(k) == 1 for k in ['app.py|on_settings', 'dialogs.py|on_save', 'settings.py|save']))
    check('settings_save_updates_four_out_edit', all(x['out_edit'] == saved_default.as_posix() for x in state))
    check('settings_save_updates_four_internal_outdir', all(Path(x['_outdir']) == saved_default for x in state),
          actual=[x['_outdir'] for x in state], expected=saved_default.as_posix())
    persisted = settings.Settings()
    check('default_persisted_in_isolated_ini', persisted.outdir == saved_default.as_posix() and persisted.q.status() == QSettings.NoError)
    for idx, p in enumerate(window.pages):
        window.group.button(idx).click()
        qa.processEvents()
        phase = 'settings_saved.open_directory.' + p.temp_key
        button(p, '打开目录').click()
        request = Path(result['open_requests'][-1]['requested_path'])
        check(phase + '.matches_current_edit', request == saved_default,
              actual=str(request), expected=str(saved_default), requests_previous_export=request == destinations[p.temp_key][0])

    # Single-page edit must not be silently treated as a global default update.
    p = window.pages[0]
    changed = ROOT / 'single_page_edit_only'
    p.out_edit.setText(changed.as_posix())
    state = snapshot('single_page_edit_after_settings')
    check('single_page_edit_does_not_sync_other_pages', state[0]['out_edit'] == changed.as_posix() and all(x['out_edit'] == saved_default.as_posix() for x in state[1:]))
    check('single_page_edit_does_not_update_internal_outdir', Path(p._outdir) == destinations[p.temp_key][0])
    phase = 'single_page_edit.open_directory'
    button(p, '打开目录').click()
    check('single_page_edit.open_directory_matches_edit', Path(result['open_requests'][-1]['requested_path']) == changed,
          actual=result['open_requests'][-1]['requested_path'], expected=str(changed))

    # Fresh MainWindow confirms saved default is loaded into BOTH fields on construction.
    fresh = production.MainWindow()
    check('new_window_loads_saved_default_into_both_fields', all(p.out_edit.text() == saved_default.as_posix() and Path(p._outdir) == saved_default for p in fresh.pages))
    fresh.close()
    check('no_generation_worker_started', all(p._worker is None for p in window.pages))
    window.close()
    qa.processEvents()
    sys.setprofile(None)
    result['call_counts'] = counts
    result['settings_storage'] = settings_factories
    result['dialog_events'] = dialog_events
except Exception:
    result['fatal_error'] = traceback.format_exc()
    emit('fatal_error', traceback=result['fatal_error'])
finally:
    after = {name: digest(PROJECT / name) for name in source_paths}
    result['source_after'] = after
    check('nine_relevant_source_files_unchanged', before == after)
    check('no_unhandled_qt_slot_errors', not slot_errors, errors=slot_errors)
    check('no_forbidden_external_or_outside_write_attempts', not blocked, attempts=blocked)
    failed = [c['name'] for c in result['checks'] if not c['pass']]
    result['summary'] = {'checks': len(result['checks']), 'passed': len(result['checks']) - len(failed),
                         'failed_behavior_checks': failed, 'fatal_error': bool(result.get('fatal_error')),
                         'os_open_verified': False, 'geometry_generation_tested': False,
                         'real_desktop_window_acceptance': False}
    (ROOT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (ROOT / 'source_after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
    emit('SUMMARY', **result['summary'])
    LOG.close()
sys.exit(2 if result.get('fatal_error') or slot_errors or blocked else 0)
