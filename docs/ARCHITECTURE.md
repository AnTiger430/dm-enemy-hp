# Архитектура мода `dm.enemy_hp` («ХП противников в ушах»)

Мод спроектирован по принципам **Clean Architecture + Ports & Adapters (Hexagonal Architecture) + SOLID** с полной совместимостью с **Python 2.7 (`win64\python27.dll`)** клиента World of Tanks **2.4.1.1**.

---

## 1. Подтверждённые API клиента WoT 2.4.1.1 (инспекция `scripts.pkg`)

При проектировании все сигнатуры проверены напрямую по байткоду `F:\game\TankiEU\World_of_Tanks_EU\res\packages\scripts.pkg`:

1. **`gui.battle_control.controllers.battle_field_ctrl.BattleFieldCtrl`** (доступен через `IBattleSessionProvider.shared.battleField`):
   - `setVehicleHealth(self, vehicleID, newHealth)` — вызывается сервером как для видимых в AOI танков, так и для техники в засвете за пределами круга отрисовки (`> 564 м`, когда `BigWorld.entities.get(vehID) is None`).
   - `setVehicleVisible(self, vehicleID, health)` — вызывается при засвете и повторном появлении после отсвета, передаёт актуальное серверное здоровье `health` (критично для улавливания блайнд-урона, пожара и падения в отсвете).
   - `stopVehicleVisual(self, vehicleID)` — уход танка из засвета/AOI (`VehicleSpottedStatus.UNSPOTTED`). **Не сбрасывает ХП** — сохраняет последнее известное значение.
   - `updateVehiclesInfo(self, updated, arenaDP)` — обновляет `vInfoVO.vehicleType.maxHealth` (когда после засвета приходит реальный `maxHealth` от Закалки / Полевой модернизации).
   - `invalidateVehicleStatus(self, flags, vInfoVO, arenaDP)` — фиксация гибели техники (`not vInfoVO.isAlive()`).
   - `getVehicleHealthInfo(self, vehicleID)` — возвращает `(currentHealth, maxHealth)` (или `None`) из внутреннего словаря `_aliveEnemies`.

2. **`Vehicle` (`scripts/client/Vehicle.pyc`)**:
   - `onEnterWorld(self, prereqs)` — при загрузке 3D-модели в AOI читает `self.id`, `self.health`, `self.maxHealth` (`publicInfo['maxHealth']`) и `self.isAlive()`.
   - `onLeaveWorld(self)` — пометка выхода из AOI (ХП сохраняется).
   - `onHealthChanged(self, newHealth, oldHealth, attackerID, attackReasonID)` — мгновенное обновление при уроне в AOI (прямые попадания, пожар, таран, взрыв БК, падение, затопление).

3. **`ClientArena` (`scripts/client_common/ClientArena.pyc`)**:
   - События `onNewVehicleListReceived`, `onVehicleAdded`, `onVehicleUpdated`, `onVehicleKilled`, `onVehicleHealthChanged`, а также словарь `arena.vehicles`.

4. **Сортировка строк правых «ушей»**:
   - `gui.battle_control.arena_info.vos_collections.EnemyItemsCollection(sortKey=VehicleInfoSortKey).iterator(arenaDP)`.
   - Подтверждённый компаратор `VehicleInfoSortKey._cmp`: `team` → `isAlive` по убыванию (живые сверху, погибшие снизу) → `vehicleType` → `player`.
   - Для автономной работы и доменных тестов реализована чистая резервная политика `RowOrderPolicy` с тем же порядком.

5. **`PlayersPanel` и режимы отображения (`PLAYERS_PANEL_STATE`)**:
   - Подтверждённые константы (`scripts/client/gui/Scaleform/genConsts/PLAYERS_PANEL_STATE.pyc`):
     - `HIDDEN = 0`, `SHORT = 1`, `MEDIUM = 2`, `LONG = 3`, `FULL = 4`,
     - `MEDIUM_NO_BADGES = 5`, `FULL_NO_BADGES = 6`, `SHORT_NO_BADGES = 20`, `LONG_NO_BADGES = 21`,
     - `EPIC_RANDOM_*` (`7..19`).
   - Перехватываются `PlayersPanel._PlayersPanel__setMode` и `PlayersPanel.as_setPanelModeS`, начальный режим читается через `PlayerPanelStateSetting.read()`.
   - Скрытие HUD (`V`), Tab (`SHOW_FULL_STATS`) и Esc/Killcam отслеживаются через `GameEvent.GUI_VISIBILITY`, `GameEvent.SHOW_FULL_STATS` (`EVENT_BUS_SCOPE.BATTLE`), `Keys.KEY_TAB`, `BigWorld.player().inputHandler.ctrlModeName` и `BattleVisibilityGuard` (проверка перекрывающих окон WULF/Scaleform).

6. **Особенности C++-контейнеров `BigWorld` в WoT 2.4.1.1**:
   - У `BigWorld.entities` запрещён вызов `len()` / `bool()` (`TypeError: __len__()`), допускается только `.get(vehID)` или `list(entities.values())`.
   - У `BigWorld.spaces` используется только индексация `spaces[spaceID]` (не оператор `in`).

---

## 2. Выбор способа рендера колонки ХП (Вариант B — Gameface / WULF Overlay)

| Критерий | Вариант A (Scaleform / ActionScript `PlayersPanel`) | Вариант B (Gameface / WULF Overlay) |
|---|---|---|
| Вывод отдельной числовой колонки слева от иконок | `PlayersPanelMeta` имеет лишь `as_setPlayerHPS(isAlly, index, percent)` для полоски %, но не текстовой колонки вне SWF | Полный контроль над колонкой цифр слева от иконок с `tabular-nums` и тенью без правки SWF |
| Устойчивость к микропатчам WoT | Требует модификации/подмены `battle.swf` | 0 правок клиентских `.swf`, только штатный WULF/Gameface (`WindowLayer.WINDOW`) |
| Взаимодействие с кликами / фокусом | Встроено в Flash | `show(False)` + CSS `pointer-events: none` — клики и курсор полностью проходят сквозь оверлей |
| Точная подгонка под разные разрешения и UI Scale | Зависит от внутреннего AS3 layout | Автоматический учёт `viewEnv.getScale()` (`uiScale`), режима панели и пользовательских `offsetX` / `offsetY` / `rowHeight` в `config.json` |

**Решение:** выбран **Вариант B** — лёгкий прозрачный неинтерактивный WULF/Gameface-оверлей (`DmEnemyHpOverlay`, `R.mods.dm.enemy_hp.views.EnemyHpOverlay`), по проверенному в `dm.threemarks` паттерну, управляемый чистым пайплайном `BattleHealthSession` → `EnemyHpPayloadPresenter` → `GamefaceEnemyPanelAdapter`.

---

## 3. Слои Clean Architecture и правило зависимостей

```text
src/mod_enemy_hp.py                 # Тонкий entrypoint WoT (init / fini)
  └─ dm_enemy_hp/
       ├─ domain/                   # ЧИСТОЕ ЯДРО: 0 импортов WoT, OS, IO, UI и внешних слоёв
       │    ├─ entities/            # EnemyVehicleHealth
       │    ├─ value_objects/       # ColorSpec, HealthRowView, PanelLayoutConfig, PanelModeLayout
       │    └─ services/            # EnemyHealthTracker, RowOrderPolicy
       ├─ application/              # Use Cases и порты (зависит ТОЛЬКО от domain + stdlib)
       │    ├─ ports/               # IConfigRepository, IEnemyPanelView, IBattleStateProvider, ILogger, IScheduler
       │    ├─ config/              # defaults, schema, validator
       │    └─ use_cases/           # BattleHealthSession
       ├─ adapters/                 # Презентеры и UI-адаптер (Gameface / WULF + VisibilityGuard)
       │    ├─ presenters/          # EnemyHpPayloadPresenter
       │    └─ ui/                  # GamefaceEnemyPanelAdapter, wulf_views, visibility_guard
       ├─ infrastructure/           # Конкретные адаптеры WoT 2.4.1.1, JSON-конфиг и файловый логгер
       │    ├─ storage/             # JsonConfigRepository
       │    ├─ logging_adapter/     # ModFileLogger
       │    └─ wot/                 # MethodHookRegistry, BattleFieldHook, VehicleHook,
       │                            # WotArenaBridge, PlayersPanelMonitor, WotScheduler
       └─ bootstrap/                # Composition Root (ручной Constructor DI)
            ├─ container.py
            └─ application.py
```

Правило зависимостей автоматически проверяется через Python `ast` в `tests/test_architecture_rules.py`:
- `domain` не может импортировать `application`, `adapters`, `infrastructure`, `bootstrap` или системные/игровые модули (`BigWorld`, `GUI`, `os`, `json` и т.п.).
- `application` зависит только от `domain` и стандартной библиотеки (`abc`, `copy`, `re`).

---

## 4. Матрица переходов состояния ХП (нулевой рассинхрон)

| Событие | Источник в WoT 2.4.1.1 | Действие `EnemyHealthTracker` | Поведение ХП |
|---|---|---|---|
| Старт боя / добавление танка | `arena.vehicles`, `onVehicleAdded` | `register_enemy(vid, max_hp, is_alive)` | Устанавливается базовый `hp = max_hp` |
| Увеличение `maxHealth` (Закалка / Полевая) | `updateVehiclesInfo`, `Vehicle.onEnterWorld`, `arena.onVehicleUpdated` | `update_max_health(vid, new_max_hp)` | Если урон ещё не получал (`not ever_spotted` или `hp == old_max`), `hp` увеличивается на `Δmax_hp`; иначе обновляется `max_hp` с клампом |
| Урон в засвете в AOI | `Vehicle.onHealthChanged`, `BattleFieldCtrl.setVehicleHealth` | `update_health(vid, new_hp)` | Мгновенное обновление `0 <= hp <= max_hp` |
| Урон в засвете `> 564 м` (вне AOI) | `BattleFieldCtrl.setVehicleHealth`, `ClientArena.onVehicleHealthChanged` | `update_health(vid, new_hp)` | Мгновенное обновление даже при `BigWorld.entities.get(vid) is None` |
| Уход в отсвет | `BattleFieldCtrl.stopVehicleVisual`, `Vehicle.onLeaveWorld` | `mark_unspotted(vid)` | `is_spotted = False`, **последнее ХП строго сохраняется** |
| Повторный засвет после урона в отсвете | `BattleFieldCtrl.setVehicleVisible(vid, health)` + `Vehicle.onEnterWorld` | `mark_spotted(vid, server_hp, max_hp)` | Мгновенная синхронизация до реального серверного `hp` |
| Повторный засвет без изменений | `setVehicleVisible` / `onEnterWorld` | `mark_spotted(vid, server_hp)` | Обновляется только `is_spotted=True`; UI dirty-check пропускает лишний push, если формат строки не изменился |
| Гибель (в засвете или в отсвете) / оверкилл | `arena.onVehicleKilled`, `invalidateVehicleStatus`, `hp <= 0` | `mark_dead(vid)` / `clamp(new_hp)` | Строго `hp = 0`, `is_alive = False`, `is_spotted = False` (отрицательные зажимаются в `0`) |
| Страховочная сверка | `WotScheduler` каждые `0.5с` | `reconcile_from_snapshot(...)` | Читает `battleField.getVehicleHealthInfo(vid)` + `BigWorld.entities.get(vid)` и устраняет любой возможный дрейф |
| Вход в середину боя / перемотка реплея | `onAvatarReady` / `onTimeWarpStart` → `onTimeWarpFinish` | `reset()` + `start_battle()` | Пересчитывает всех врагов из живого состояния `arena` + `battleField` + `entities` |
