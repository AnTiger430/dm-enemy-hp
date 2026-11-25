# -*- coding: utf-8 -*-
from __future__ import absolute_import

import ast
import os
import shutil
import sys
import tempfile
import types
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, 'src')
TESTS_DIR = os.path.join(ROOT_DIR, 'tests')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def _iter_py_files(*roots):
    for base in roots:
        for r, _dirs, files in os.walk(base):
            for fn in sorted(files):
                if fn.endswith('.py'):
                    yield os.path.join(r, fn)


def _layer_of(path):
    norm = path.replace('\\', '/')
    marker = '/dm_enemy_hp/'
    if marker not in norm:
        return 'entrypoint'
    rel = norm.split(marker, 1)[1]
    return rel.split('/', 1)[0]


def _extract_imports(tree, cur_path):
    mods = []
    rel_parts = cur_path.replace('\\', '/').split('/')
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            level = getattr(node, 'level', 0) or 0
            if level > 0 and 'dm_enemy_hp' in rel_parts:
                idx = rel_parts.index('dm_enemy_hp')
                pkg_parts = rel_parts[idx:-level] if len(rel_parts) - level > idx else ['dm_enemy_hp']
                base = '.'.join(pkg_parts)
                if node.module:
                    mods.append(base + '.' + node.module)
                else:
                    mods.append(base)
            elif node.module:
                mods.append(node.module)
    return mods


class _StrictEntities(object):
    """Forbids len()/bool() just like WoT C++ BigWorld.entities."""

    def __init__(self):
        self._d = {}

    def get(self, k, default=None):
        return self._d.get(k, default)

    def __setitem__(self, k, v):
        self._d[k] = v

    def __delitem__(self, k):
        del self._d[k]

    def values(self):
        return self._d.values()

    def __len__(self):
        raise AssertionError('BigWorld.entities.__len__() is forbidden!')

    def __nonzero__(self):
        raise AssertionError('BigWorld.entities.__nonzero__() is forbidden!')


class _Ev(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, fn):
        self.handlers.append(fn)
        return self

    def __isub__(self, fn):
        if fn in self.handlers:
            self.handlers.remove(fn)
        return self

    def fire(self, *args, **kwargs):
        for fn in list(self.handlers):
            fn(*args, **kwargs)


def _build_wot_stubs():
    class Vehicle(object):
        def onEnterWorld(self, _prereqs):
            pass

        def onLeaveWorld(self):
            pass

        def onHealthChanged(self, newHealth, _oldHealth, _attackerID, _attackReasonID, _attackReasonExtID=0):
            self.health = newHealth

        def isAlive(self):
            return getattr(self, 'health', 0) > 0

    class BattleFieldCtrl(object):
        def __init__(self):
            self._alive = {}

        def getVehicleHealthInfo(self, vid):
            return self._alive.get(vid)

        def setVehicleHealth(self, vid, new_h):
            if vid in self._alive:
                self._alive[vid] = [new_h, self._alive[vid][1]]

        def setVehicleVisible(self, vid, health):
            cur = self._alive.get(vid)
            self._alive[vid] = [health, cur[1] if cur else health]

        def stopVehicleVisual(self, _vid):
            pass

        def updateVehiclesInfo(self, _updated, _dp):
            pass

        def invalidateVehicleStatus(self, _flags, _vo, _dp):
            pass

    class PlayersPanelMeta(object):
        def _populate(self):
            pass

        def _dispose(self):
            pass

        def as_setPanelModeS(self, mode):
            self._mode = mode

    class PlayersPanel(PlayersPanelMeta):
        def _PlayersPanel__setMode(self, mode):
            self._mode = mode
            self.as_setPanelModeS(mode)

    class BattlePageMeta(object):
        def __init__(self):
            self._vis = set(['playersPanel'])

        def as_setComponentsVisibilityS(self, visible=(), hidden=()):
            for k in visible or ():
                self._vis.add(k)
            for k in hidden or ():
                self._vis.discard(k)

        def as_setComponentsVisibilityWithFadeS(self, visible=(), hidden=()):
            self.as_setComponentsVisibilityS(visible, hidden)

        def as_isComponentVisibleS(self, alias):
            return alias in self._vis

    bf_ctrl = BattleFieldCtrl()
    entities = _StrictEntities()

    class _VType(object):
        def __init__(self, max_hp, lvl, cls_tag, sname):
            self.maxHealth = max_hp
            self.level = lvl
            self.classTag = cls_tag
            self.shortName = sname

    class _PlayerVO(object):
        def __init__(self, name):
            self.name = name

    class _VInfoVO(object):
        def __init__(self, vid, team, max_hp, lvl, cls_tag, sname, pname, alive=True):
            self.vehicleID = vid
            self.team = team
            self.vehicleType = _VType(max_hp, lvl, cls_tag, sname)
            self.player = _PlayerVO(pname)
            self._alive = alive

        def isObserver(self):
            return False

        def isAlive(self):
            return self._alive

    v10 = _VInfoVO(10, 2, 1500, 8, 'heavyTank', 'IS-3', 'Enemy1')
    v11 = _VInfoVO(11, 2, 1100, 8, 'mediumTank', 'T-44', 'Enemy2')
    v20 = _VInfoVO(20, 1, 1400, 8, 'heavyTank', 'Tiger II', 'Ally1')
    vos = {10: v10, 11: v11, 20: v20}

    bf_ctrl._alive[10] = [1500, 1500]
    bf_ctrl._alive[11] = [1100, 1100]

    class _ArenaDP(object):
        def getVehiclesInfoIterator(self):
            return [v10, v11, v20]

        def getVehicleInfo(self, vid):
            return vos.get(vid)

        def isEnemyTeam(self, team):
            return team == 2

    arena_dp = _ArenaDP()

    class _Arena(object):
        def __init__(self):
            self.vehicles = {10: {'team': 2, 'maxHealth': 1500, 'isAlive': True}, 11: {'team': 2, 'maxHealth': 1100, 'isAlive': True}, 20: {'team': 1, 'maxHealth': 1400, 'isAlive': True}}
            self.onNewVehicleListReceived = _Ev()
            self.onVehicleAdded = _Ev()
            self.onVehicleUpdated = _Ev()
            self.onVehicleKilled = _Ev()
            self.onVehicleHealthChanged = _Ev()

    arena = _Arena()
    player = types.ModuleType('_Player')
    player.arena = arena
    player.team = 1
    player.inputHandler = types.ModuleType('_IH')
    player.inputHandler.ctrlModeName = 'arcade'

    bigworld = types.ModuleType('BigWorld')
    bigworld.entities = entities
    bigworld.player = lambda: player
    bigworld.isKeyDown = lambda _k: False
    bigworld._cbs = {}
    bigworld._next_cb = 1

    def _cb(delay, fn):
        cid = bigworld._next_cb
        bigworld._next_cb += 1
        bigworld._cbs[cid] = (delay, fn)
        return cid

    bigworld.callback = _cb
    bigworld.cancelCallback = lambda cid: bigworld._cbs.pop(cid, None)

    gui_mod = types.ModuleType('GUI')
    gui_mod.screenResolution = lambda: (1920, 1080)

    keys_mod = types.ModuleType('Keys')
    keys_mod.KEY_TAB = 15

    pe_mod = types.ModuleType('PlayerEvents')
    pe_mod.g_playerEvents = types.ModuleType('_PE')
    pe_mod.g_playerEvents.onAvatarReady = _Ev()
    pe_mod.g_playerEvents.onAvatarBecomeNonPlayer = _Ev()
    pe_mod.g_playerEvents.onPlayerEntityChanging = _Ev()

    re_mod = types.ModuleType('ReplayEvents')
    re_mod.g_replayEvents = types.ModuleType('_RE')
    re_mod.g_replayEvents.onTimeWarpStart = _Ev()
    re_mod.g_replayEvents.onTimeWarpFinish = _Ev()

    helpers_mod = types.ModuleType('helpers')
    helpers_mod._is_avatar = True
    helpers_mod.isPlayerAvatar = lambda: helpers_mod._is_avatar
    dep_mod = types.ModuleType('dependency')

    class _SP(object):
        shared = types.ModuleType('_Shared')
        getArenaDP = staticmethod(lambda: arena_dp)

    _SP.shared.battleField = bf_ctrl
    sp_iface = object()
    gui_loader_iface = object()

    class _ViewFlags(object):
        VIEW = 1

    class _WindowFlags(object):
        WINDOW = 1

    class _WindowLayer(object):
        VIEW = 0
        WINDOW = 1
        FULLSCREEN_WINDOW = 2
        TOP_WINDOW = 3
        OVERLAY = 4

    class _WindowStatus(object):
        LOADED = 1
        DESTROYING = 2
        DESTROYED = 3

    class _ViewSettings(object):
        def __init__(self, layoutID=0, flags=0, model=None):
            self.layoutID = layoutID
            self.flags = flags
            self.model = model

    class _TxnCtx(object):
        def __init__(self, obj):
            self._obj = obj

        def __enter__(self):
            return self._obj

        def __exit__(self, _exc_type, _exc_val, _exc_tb):
            return False

    class _ViewModel(object):
        def __init__(self, properties=0, commands=0):
            self._last_payload = None
            self._initialize()

        def _initialize(self):
            pass

        def _addStringProperty(self, _name, val):
            self._last_payload = val

        def _addCommand(self, _name):
            return _Ev()

        def _setString(self, _idx, val):
            self._last_payload = val

        def transaction(self):
            return _TxnCtx(self)

    class _ViewImpl(object):
        def __init__(self, settings):
            self._model = settings.model
            if hasattr(self, '_getEvents'):
                for ev, handler in self._getEvents() or ():
                    ev += handler

        def getViewModel(self):
            return self._model

        def _finalize(self):
            pass

    class _WindowImpl(object):
        def __init__(self, _flags, content=None, layer=1, name='', parent=None):
            self.proxy = object()
            self.windowStatus = _WindowStatus.LOADED
            self.layer = layer
            self.name = name
            self.parent = parent
            self.uniqueID = id(self)
            self.content = content
            self._hidden = False
            self._pos = None

        def load(self):
            if hasattr(self, '_onReady'):
                self._onReady()

        def show(self, _focus=False):
            self._hidden = False

        def hide(self):
            self._hidden = True

        def move(self, px, py):
            self._pos = (px, py)

        def isHidden(self):
            return self._hidden

        def destroy(self):
            self.windowStatus = _WindowStatus.DESTROYED
            self.proxy = None
            if self.content is not None and hasattr(self.content, '_finalize'):
                self.content._finalize()

    main_win = _WindowImpl(_WindowFlags.WINDOW, layer=_WindowLayer.WINDOW, name='MainWindow')

    class _WindowsManager(object):
        def getMainWindow(self):
            return main_win

        def findWindows(self, _pred):
            return []

        def findViews(self, _pred):
            return []

    class _GuiLoader(object):
        windowsManager = _WindowsManager()

    gui_loader_inst = _GuiLoader()
    sp_inst = _SP()

    def _dep_instance(iface):
        if iface is sp_iface:
            return sp_inst
        if iface is gui_loader_iface:
            return gui_loader_inst
        return None

    dep_mod.instance = _dep_instance
    helpers_mod.dependency = dep_mod

    sk_bs = types.ModuleType('skeletons.gui.battle_session')
    sk_bs.IBattleSessionProvider = sp_iface
    sk_impl = types.ModuleType('skeletons.gui.impl')
    sk_impl.IGuiLoader = gui_loader_iface

    fw_pkg = types.ModuleType('frameworks')
    fw_wulf = types.ModuleType('frameworks.wulf')
    fw_wulf.ViewFlags = _ViewFlags
    fw_wulf.WindowFlags = _WindowFlags
    fw_wulf.WindowLayer = _WindowLayer
    fw_wulf.WindowStatus = _WindowStatus
    fw_wulf.ViewSettings = _ViewSettings
    fw_wulf.ViewModel = _ViewModel

    def _args2params(*param_types):
        def _dec(fn):
            varnames = fn.func_code.co_varnames[1:1 + len(param_types)]

            def _wrapper(self, args=None):
                args = args or {}
                kwargs = {}
                for name, ptype in zip(varnames, param_types):
                    kwargs[name] = ptype(args[name])
                return fn(self, **kwargs)
            return _wrapper
        return _dec

    gui_impl = types.ModuleType('gui.impl')
    gui_impl_dec = types.ModuleType('gui.impl.gui_decorators')
    gui_impl_dec.args2params = _args2params
    gui_impl_pub = types.ModuleType('gui.impl.pub')
    gui_impl_pub.ViewImpl = _ViewImpl
    gui_impl_pub.WindowImpl = _WindowImpl

    class _RNode(object):
        pass

    r_root = _RNode()
    r_root.mods = _RNode()
    r_root.mods.dm = _RNode()
    r_root.mods.dm.enemy_hp = _RNode()
    r_root.mods.dm.enemy_hp.views = _RNode()
    r_root.mods.dm.enemy_hp.views.EnemyHpOverlay = lambda: 42001
    gui_impl_gen = types.ModuleType('gui.impl.gen')
    gui_impl_gen.R = r_root

    pe_pkg = types.ModuleType('gui.battle_control.controllers.battle_field_ctrl')
    pe_pkg.BattleFieldCtrl = BattleFieldCtrl

    pp_mod = types.ModuleType('gui.Scaleform.daapi.view.battle.classic.players_panel')
    pp_mod.PlayersPanel = PlayersPanel
    pp_mod.PlayerPanelStateSetting = types.ModuleType('_PPS')
    pp_mod.PlayerPanelStateSetting.read = staticmethod(lambda: 1)

    pp_meta_mod = types.ModuleType('gui.Scaleform.daapi.view.meta.PlayersPanelMeta')
    pp_meta_mod.PlayersPanelMeta = PlayersPanelMeta
    bp_meta_mod = types.ModuleType('gui.Scaleform.daapi.view.meta.BattlePageMeta')
    bp_meta_mod.BattlePageMeta = BattlePageMeta
    bva_mod = types.ModuleType('gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES')
    bva_mod.BATTLE_VIEW_ALIASES = types.ModuleType('_BVA')
    bva_mod.BATTLE_VIEW_ALIASES.PLAYERS_PANEL = 'playersPanel'

    vo_mod = types.ModuleType('gui.battle_control.arena_info.vos_collections')
    vo_mod.VehicleInfoSortKey = object()

    class _EnemyCol(object):
        def __init__(self, sortKey=None):
            pass

        def iterator(self, _dp):
            return [(v11, None), (v10, None)]  # T-44 above IS-3 or sorted by DP

    vo_mod.EnemyItemsCollection = _EnemyCol

    ev_bus = types.ModuleType('_EB')
    ev_bus._listeners = {}
    ev_bus.addListener = lambda name, fn, scope=None: ev_bus._listeners.setdefault(name, []).append(fn)
    ev_bus.removeListener = lambda name, fn, scope=None: ev_bus._listeners.get(name, []).remove(fn) if fn in ev_bus._listeners.get(name, []) else None
    gui_shared = types.ModuleType('gui.shared')
    gui_shared.g_eventBus = ev_bus
    gui_shared.events = types.ModuleType('_Events')
    gui_shared.events.GameEvent = types.ModuleType('_GE')
    gui_shared.events.GameEvent.GUI_VISIBILITY = 'gui_vis'
    gui_shared.events.GameEvent.FULL_STATS = 'full_stats'
    gui_shared.EVENT_BUS_SCOPE = types.ModuleType('_Scope')
    gui_shared.EVENT_BUS_SCOPE.BATTLE = 'battle'

    veh_mod = types.ModuleType('Vehicle')
    veh_mod.Vehicle = Vehicle

    stubs = {
        'BigWorld': bigworld,
        'GUI': gui_mod,
        'Keys': keys_mod,
        'PlayerEvents': pe_mod,
        'ReplayEvents': re_mod,
        'helpers': helpers_mod,
        'helpers.dependency': dep_mod,
        'skeletons': types.ModuleType('skeletons'),
        'skeletons.gui': types.ModuleType('skeletons.gui'),
        'skeletons.gui.battle_session': sk_bs,
        'skeletons.gui.impl': sk_impl,
        'frameworks': fw_pkg,
        'frameworks.wulf': fw_wulf,
        'gui': types.ModuleType('gui'),
        'gui.impl': gui_impl,
        'gui.impl.gui_decorators': gui_impl_dec,
        'gui.impl.pub': gui_impl_pub,
        'gui.impl.gen': gui_impl_gen,
        'gui.shared': gui_shared,
        'gui.battle_control': types.ModuleType('gui.battle_control'),
        'gui.battle_control.controllers': types.ModuleType('gui.battle_control.controllers'),
        'gui.battle_control.controllers.battle_field_ctrl': pe_pkg,
        'gui.battle_control.arena_info': types.ModuleType('gui.battle_control.arena_info'),
        'gui.battle_control.arena_info.vos_collections': vo_mod,
        'gui.Scaleform': types.ModuleType('gui.Scaleform'),
        'gui.Scaleform.daapi': types.ModuleType('gui.Scaleform.daapi'),
        'gui.Scaleform.daapi.view': types.ModuleType('gui.Scaleform.daapi.view'),
        'gui.Scaleform.daapi.view.meta': types.ModuleType('gui.Scaleform.daapi.view.meta'),
        'gui.Scaleform.daapi.view.meta.PlayersPanelMeta': pp_meta_mod,
        'gui.Scaleform.daapi.view.meta.BattlePageMeta': bp_meta_mod,
        'gui.Scaleform.genConsts': types.ModuleType('gui.Scaleform.genConsts'),
        'gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES': bva_mod,
        'gui.Scaleform.daapi.view.battle': types.ModuleType('gui.Scaleform.daapi.view.battle'),
        'gui.Scaleform.daapi.view.battle.classic': types.ModuleType('gui.Scaleform.daapi.view.battle.classic'),
        'gui.Scaleform.daapi.view.battle.classic.players_panel': pp_mod,
        'Vehicle': veh_mod,
    }
    return stubs, {
        'bf_ctrl': bf_ctrl,
        'BattleFieldCtrl': BattleFieldCtrl,
        'Vehicle': Vehicle,
        'PlayersPanel': PlayersPanel,
        'BattlePageMeta': BattlePageMeta,
        'entities': entities,
        'v10': v10,
        'arena': arena,
        'bigworld': bigworld,
        'pe': pe_mod.g_playerEvents,
        'ev_bus': ev_bus,
    }


class TestArchitectureAndSmoke(unittest.TestCase):
    def test_python27_ast_and_encoding_headers(self):
        count = 0
        for path in _iter_py_files(SRC_DIR, TESTS_DIR):
            count += 1
            with open(path, 'rb') as f:
                raw_bytes = f.read()
            first_line = raw_bytes.decode('utf-8').splitlines()[0]
            self.assertIn('# -*- coding: utf-8 -*-', first_line, path)
            ast.parse(raw_bytes, filename=path)
        self.assertGreaterEqual(count, 20)

    def test_clean_architecture_layer_boundaries(self):
        forbidden_domain = set([
            'BigWorld', 'GUI', 'Keys', 'PlayerEvents', 'ReplayEvents', 'Vehicle',
            'helpers', 'gui', 'frameworks', 'skeletons', 'os', 'sys', 'json', 'codecs', 'shutil',
            'dm_enemy_hp.application', 'dm_enemy_hp.adapters', 'dm_enemy_hp.infrastructure', 'dm_enemy_hp.bootstrap',
        ])
        forbidden_app = set([
            'BigWorld', 'GUI', 'Keys', 'PlayerEvents', 'ReplayEvents', 'Vehicle',
            'helpers', 'gui', 'frameworks', 'skeletons', 'os', 'json', 'shutil',
            'dm_enemy_hp.adapters', 'dm_enemy_hp.infrastructure', 'dm_enemy_hp.bootstrap',
        ])
        for path in _iter_py_files(SRC_DIR):
            layer = _layer_of(path)
            with open(path, 'rb') as f:
                tree = ast.parse(f.read(), filename=path)
            imports = _extract_imports(tree, path)
            if layer == 'domain':
                for imp in imports:
                    top = imp.split('.')[0]
                    self.assertNotIn(top, forbidden_domain, '%s imports forbidden %s' % (path, imp))
                    for bad in forbidden_domain:
                        self.assertFalse(imp.startswith(bad), '%s imports forbidden %s' % (path, imp))
            elif layer == 'application':
                for imp in imports:
                    top = imp.split('.')[0]
                    self.assertNotIn(top, forbidden_app, '%s imports forbidden %s' % (path, imp))
                    for bad in forbidden_app:
                        self.assertFalse(imp.startswith(bad), '%s imports forbidden %s' % (path, imp))

    def test_no_cyclic_dependencies_between_layers_and_modules(self):
        path_to_mod = {}
        mod_to_layer = {}
        for path in _iter_py_files(SRC_DIR):
            rel = os.path.relpath(path, SRC_DIR).replace('\\', '/')
            if rel.endswith('/__init__.py'):
                mod = rel[:-len('/__init__.py')].replace('/', '.')
            elif rel == '__init__.py':
                mod = ''
            else:
                mod = rel[:-3].replace('/', '.')
            if mod:
                path_to_mod[path] = mod
                mod_to_layer[mod] = _layer_of(path)

        known_mods = set(path_to_mod.values())
        mod_graph = dict((m, set()) for m in known_mods)
        layer_graph = {}
        for layer in set(mod_to_layer.values()):
            layer_graph[layer] = set()

        def _resolve_mod(imp):
            cur = imp
            while cur:
                if cur in known_mods:
                    return cur
                if '.' not in cur:
                    break
                cur = cur.rsplit('.', 1)[0]
            return None

        for path, src_mod in path_to_mod.items():
            src_layer = mod_to_layer[src_mod]
            with open(path, 'rb') as f:
                tree = ast.parse(f.read(), filename=path)
            raw_imports = list(_extract_imports(tree, path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        if alias.name != '*':
                            raw_imports.append(node.module + '.' + alias.name)
            for imp in raw_imports:
                target_mod = _resolve_mod(imp)
                if target_mod and target_mod != src_mod:
                    mod_graph[src_mod].add(target_mod)
                    target_layer = mod_to_layer[target_mod]
                    if target_layer != src_layer:
                        layer_graph[src_layer].add(target_layer)

        def _find_cycle(graph):
            WHITE, GRAY, BLACK = 0, 1, 2
            state = dict((node, WHITE) for node in graph)
            stack = []

            def dfs(node):
                state[node] = GRAY
                stack.append(node)
                for nxt in sorted(graph[node]):
                    st = state.get(nxt, WHITE)
                    if st == GRAY:
                        idx = stack.index(nxt)
                        return stack[idx:] + [nxt]
                    if st == WHITE:
                        cyc = dfs(nxt)
                        if cyc:
                            return cyc
                stack.pop()
                state[node] = BLACK
                return None

            for node in sorted(graph):
                if state[node] == WHITE:
                    cyc = dfs(node)
                    if cyc:
                        return cyc
            return None

        layer_cycle = _find_cycle(layer_graph)
        self.assertIsNone(layer_cycle, 'Cyclic dependency between layers: %r' % (layer_cycle,))
        mod_cycle = _find_cycle(mod_graph)
        self.assertIsNone(mod_cycle, 'Cyclic dependency between modules: %r' % (mod_cycle,))

    def test_wot_package_relative_imports_and_entrypoint(self):
        entry_path = os.path.join(SRC_DIR, 'mod_enemy_hp.py')
        with open(entry_path, 'rb') as f:
            entry_tree = ast.parse(f.read(), filename=entry_path)
        entry_imports = _extract_imports(entry_tree, entry_path)
        self.assertIn(
            'gui.mods.dm_enemy_hp.bootstrap.container',
            entry_imports,
            'Entrypoint must support gui.mods.dm_enemy_hp for WoT loader',
        )
        pkg_dir = os.path.join(SRC_DIR, 'dm_enemy_hp')
        for path in _iter_py_files(pkg_dir):
            with open(path, 'rb') as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name.startswith('dm_enemy_hp'),
                            'Absolute import %s inside package breaks gui.mods namespace: %s' % (alias.name, path),
                        )
                elif isinstance(node, ast.ImportFrom):
                    level = getattr(node, 'level', 0) or 0
                    if level == 0 and node.module:
                        self.assertFalse(
                            node.module.startswith('dm_enemy_hp'),
                            'Absolute import %s inside package breaks gui.mods namespace: %s' % (node.module, path),
                        )

    def test_smoke_init_battle_unspot_respot_hardening_and_fini(self):
        stubs, ctx = _build_wot_stubs()
        saved = {}
        orig_bf_set = ctx['BattleFieldCtrl'].__dict__['setVehicleHealth']
        orig_veh_enter = ctx['Vehicle'].__dict__['onEnterWorld']
        orig_pp_mode = ctx['PlayersPanel'].__dict__['_PlayersPanel__setMode']

        for k, v in stubs.items():
            saved[k] = sys.modules.get(k)
            sys.modules[k] = v

        # Clear previously imported infrastructure modules so they bind our stubs cleanly
        for mname in list(sys.modules.keys()):
            if mname == 'mod_enemy_hp' or mname.startswith('dm_enemy_hp.'):
                sys.modules.pop(mname, None)

        tmp_dir = tempfile.mkdtemp(prefix='dm_enemy_hp_smoke_')
        orig_cwd = os.getcwd()
        os.chdir(tmp_dir)

        try:
            stubs['helpers']._is_avatar = False
            import mod_enemy_hp
            mod_enemy_hp.init()

            self.assertIsNot(ctx['BattleFieldCtrl'].__dict__['setVehicleHealth'], orig_bf_set)
            self.assertIsNot(ctx['Vehicle'].__dict__['onEnterWorld'], orig_veh_enter)
            self.assertIsNot(ctx['PlayersPanel'].__dict__['_PlayersPanel__setMode'], orig_pp_mode)

            # Simulate WoT countdown starting PlayersPanel in FULL(4) BEFORE onAvatarReady
            stubs['helpers']._is_avatar = True
            pp_early = ctx['PlayersPanel']()
            pp_early._populate()
            pp_early._PlayersPanel__setMode(4)

            # Start battle -> must keep 'large' mode rather than overwriting with PlayerPanelStateSetting.read()
            ctx['pe'].onAvatarReady.fire()
            app = mod_enemy_hp._app
            tracker = app._session._tracker
            self.assertEqual(app._panel_monitor.get_mode(), 'large')
            self.assertTrue(app._panel_monitor.is_hud_visible())
            self.assertIsNotNone(app._session._panel_view.window)
            app._session._panel_view.model.onReady.fire({'message': 'enemy_hp_ready'})
            self.assertTrue(app._session._panel_view._ready)
            self.assertEqual(app._session._panel_view.window._pos, (1920 - 382 - 54, 67))

            # Sorted 2 enemies: 10 (1500), 11 (1100); ally 20 excluded
            self.assertEqual(tracker.get(10).hp, 1500)
            self.assertEqual(tracker.get(11).hp, 1100)
            self.assertIsNone(tracker.get(20))

            # >564m un-entered entity damage via BattleFieldCtrl.setVehicleHealth
            bf = ctx['bf_ctrl']
            bf.setVehicleHealth(11, 740)
            self.assertEqual(tracker.get(11).hp, 740)

            # Enemy 10 spotted with Hardening (maxHealth becomes 1650 via updateVehiclesInfo + setVehicleVisible)
            ctx['v10'].vehicleType.maxHealth = 1650
            bf._alive[10] = [1650, 1650]
            bf.updateVehiclesInfo([(0, ctx['v10'])], None)
            bf.setVehicleVisible(10, 1650)
            self.assertEqual((tracker.get(10).hp, tracker.get(10).max_hp, tracker.get(10).is_spotted), (1650, 1650, True))

            # Takes damage in AOI, then leaves world (unspot) -> HP preserved!
            v10_ent = ctx['Vehicle']()
            v10_ent.id = 10
            v10_ent.isPlayerTeam = False
            v10_ent.isStarted = True
            v10_ent.health = 1650
            v10_ent.maxHealth = 1650
            ctx['entities'][10] = v10_ent
            v10_ent.onHealthChanged(920, 1650, 1, 0, 0)
            self.assertEqual(tracker.get(10).hp, 920)
            v10_ent.onLeaveWorld()
            del ctx['entities']._d[10]
            bf.stopVehicleVisual(10)
            self.assertEqual((tracker.get(10).hp, tracker.get(10).is_spotted), (920, False))

            # Blind shot + fire in unspot -> re-spots with 310 HP via setVehicleVisible + onEnterWorld
            bf._alive[10] = [310, 1650]
            bf.setVehicleVisible(10, 310)
            v10_ent.health = 310
            ctx['entities'][10] = v10_ent
            v10_ent.onEnterWorld(None)
            self.assertEqual((tracker.get(10).hp, tracker.get(10).is_spotted), (310, True))

            # Overkill kill via onHealthChanged(-150) & arena death -> clamped 0
            v10_ent.onHealthChanged(-150, 310, 1, 0, 0)
            ctx['arena'].onVehicleKilled.fire(10, 1, 0, 0, 1)
            self.assertEqual((tracker.get(10).hp, tracker.get(10).is_alive), (0, False))

            # Mod panel mode switch & visibility toggle (GUI_VISIBILITY + BattlePageMeta 'playersPanel')
            pp = ctx['PlayersPanel']()
            pp._populate()
            pp._PlayersPanel__setMode(4)
            self.assertEqual(app._panel_monitor.get_mode(), 'large')
            bp = ctx['BattlePageMeta']()
            bp.as_setComponentsVisibilityS([], ['playersPanel'])
            self.assertFalse(app._panel_monitor.is_hud_visible())
            bp.as_setComponentsVisibilityS(['playersPanel'], [])
            self.assertTrue(app._panel_monitor.is_hud_visible())
            for fn in ctx['ev_bus']._listeners.get('gui_vis', []):
                fn(types.SimpleNamespace(ctx={'visible': False}) if hasattr(types, 'SimpleNamespace') else type('_E', (), {'ctx': {'visible': False}})())
            self.assertFalse(app._panel_monitor.is_hud_visible())

            mod_enemy_hp.fini()
            self.assertIsNone(mod_enemy_hp._app)
            self.assertIs(ctx['BattleFieldCtrl'].__dict__['setVehicleHealth'], orig_bf_set)
            self.assertIs(ctx['Vehicle'].__dict__['onEnterWorld'], orig_veh_enter)
            self.assertIs(ctx['PlayersPanel'].__dict__['_PlayersPanel__setMode'], orig_pp_mode)
            self.assertEqual(ctx['bigworld']._cbs, {})

            log_path = os.path.join(tmp_dir, 'mods', 'configs', 'dm_enemy_hp', 'enemy_hp.log')
            self.assertTrue(os.path.isfile(log_path), 'Missing smoke log file: %s' % log_path)
            with open(log_path, 'rb') as lf:
                log_text = lf.read().decode('utf-8')
            self.assertNotIn('[ERROR]', log_text, 'Unexpected [ERROR] in enemy_hp.log:\n%s' % log_text)
        finally:
            os.chdir(orig_cwd)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            for mname in list(sys.modules.keys()):
                if mname == 'mod_enemy_hp' or mname.startswith('dm_enemy_hp.'):
                    sys.modules.pop(mname, None)
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_no_overlay_in_modes_without_players_panel(self):
        stubs, ctx = _build_wot_stubs()
        saved = {}
        for k, v in stubs.items():
            saved[k] = sys.modules.get(k)
            sys.modules[k] = v
        for mname in list(sys.modules.keys()):
            if mname == 'mod_enemy_hp' or mname.startswith('dm_enemy_hp.'):
                sys.modules.pop(mname, None)

        tmp_dir = tempfile.mkdtemp(prefix='dm_enemy_hp_nope_')
        orig_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            stubs['helpers']._is_avatar = False
            import mod_enemy_hp
            mod_enemy_hp.init()

            # Simulate entering a battle without standard PlayersPanel (e.g. Steel Hunter / Frontline / PvE)
            stubs['helpers']._is_avatar = True
            ctx['pe'].onAvatarReady.fire()
            app = mod_enemy_hp._app
            self.assertFalse(app._panel_monitor.is_hud_visible())
            self.assertIsNone(app._session._panel_view.window)
            mod_enemy_hp.fini()
        finally:
            os.chdir(orig_cwd)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            for mname in list(sys.modules.keys()):
                if mname == 'mod_enemy_hp' or mname.startswith('dm_enemy_hp.'):
                    sys.modules.pop(mname, None)
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v


if __name__ == '__main__':
    unittest.main()
