# FH6 Live Map v0.9.24 — Meme Layer jump tuning + RU/EN UI

Изменения:

- `jump_takeoff` стал менее строгим: теперь трамплины должны срабатывать лучше, но обычный плавный подъём по эстакаде дополнительно фильтруется через вертикальный импульс и long-slope guard.
- Новые элементы интерфейса Meme Layer и Keep Awake подключены к общей RU/EN-системе локализации.
- При смене языка в настройках обновляются не только статичные кнопки, но и динамические статусы: звук, количество сэмплов, old screen-keepalive, сообщения Rescan/Test.
- Если у пользователя уже есть `data/meme_layer/config.json` от v0.9.23, программа мягко мигрирует только старые строгие jump-пороги. Пользовательские ручные настройки сохраняются.

Папки сэмплов не изменились:

```text
data/meme_layer/samples/collision/
data/meme_layer/samples/mega_fail_crash/
data/meme_layer/samples/jump_takeoff/
```
