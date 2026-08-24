# Правила структури проекту LiosTimer

## Основний принцип
Кожен великий розділ бота — окремий пакет (папка з `__init__.py`).
Файл не повинен перевищувати ~150 рядків. Якщо більше — ділимо.

---

## Структура папок

```
D:/LiosTimer/
├── main.py                  # тільки запуск polling + init_db
├── config/
│   └── settings.py          # Config dataclass, load_config()
├── data/
│   ├── database.py          # init_db(), DB_PATH
│   └── models_*.py          # одна модель = один файл
├── states/
│   └── states_*.py          # FSM стани, по одному файлу на розділ
└── bot/
    ├── handlers/
    │   ├── __init__.py      # register_all() — тільки імпорти роутерів
    │   └── *.py             # прості хендлери (start, loot, wipe...)
    ├── keyboards/
    │   └── *.py             # прості клавіатури
    └── [розділ]/            # складний розділ — окремий пакет
        ├── __init__.py      # збирає router з усіх handlers_*.py
        ├── handlers_*.py    # хендлери по темі
        └── keyboards_*.py  # клавіатури по темі
```

---

## Коли створювати окремий пакет `bot/[розділ]/`

Створюємо пакет якщо розділ має:
- більше 2 екранів / підменю
- власні FSM стани
- більше ~3 callback-хендлерів
- свою логіку (таймери, клан, сповіщення)

### Готові пакети (зараз)
- `bot/admin/` — адмін-панель

### Плануються
- `bot/loot/` — коли додамо реальні таймери
- `bot/notifications/` — планувальник сповіщень
- `bot/clan/` — логіка клану (запрошення, учасники)
- `bot/wipe/` — таймер вайпу

---

## Правила іменування файлів

| Що | Назва |
|----|-------|
| Хендлери розділу | `handlers_[тема].py` |
| Клавіатури розділу | `keyboards_[тема].py` |
| Модель БД | `models_[таблиця].py` |
| FSM стани | `states_[розділ].py` |

---

## Правила для `__init__.py` пакету

```python
# bot/admin/__init__.py — тільки збирає роутери
from aiogram import Router
from .handlers_main import router as main_router
from .handlers_users import router as users_router

router = Router()
router.include_router(main_router)
router.include_router(users_router)
```

---

## Правила для `data/`

- Один файл = одна таблиця або одна логічна група
- `database.py` — тільки `init_db()` і `DB_PATH`
- Функції назви: `get_`, `save_`, `set_`, `delete_`

---

## Чого НЕ робити

- Не класти всі хендлери в один файл
- Не імпортувати клавіатури з інших розділів (кожен пакет — самодостатній)
- Не писати бізнес-логіку в хендлерах — виносити в `data/` або `utils/`
- Не писати більше одного `router = Router()` на файл
