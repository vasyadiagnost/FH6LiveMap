# GitHub web upload checklist / памятка для загрузки через браузер

Эта памятка для владельца репозитория. GitHub **не распаковывает ZIP автоматически** при загрузке файлов в репозиторий: если загрузить ZIP через `Add file -> Upload files`, он появится как один файл. Для нормального репозитория нужно сначала распаковать архив локально.

## A. Создать репозиторий

1. Открой GitHub.
2. Нажми `+` -> `New repository`.
3. Название, например: `FH6LiveMap`.
4. Public/Private — как хочешь.
5. Лучше не ставить галочки `Add a README`, `.gitignore`, `license`, потому что они уже подготовлены в этом пакете.
6. Нажми `Create repository`.

## B. Загрузить файлы проекта через web UI

1. Скачай и распакуй архив `FH6LiveMap_v0.9.15_github_upload_ready.zip`.
2. Открой распакованную папку `FH6LiveMap_v0.9.15_github_upload_ready`.
3. Выдели **содержимое папки**, а не саму папку целиком:
   - `README.md`
   - `fh6_live_map_server.py`
   - `data/`
   - `tools/`
   - остальные файлы
4. На GitHub в пустом репозитории нажми `uploading an existing file` или `Add file -> Upload files`.
5. Перетащи выделенные файлы/папки в окно браузера.
6. Дождись окончания загрузки.
7. Commit message:

```text
Initial upload: FH6 Live Map v0.9.15
```

8. Нажми `Commit changes` / `Propose changes`.
9. Проверь, что `README.md` красиво отобразился на главной странице репозитория.

## C. Создать GitHub Release для Reddit-ссылки

1. На главной странице репозитория справа нажми `Releases`.
2. Нажми `Draft a new release`.
3. В поле tag введи:

```text
v0.9.15
```

4. Нажми `Create new tag`.
5. Release title:

```text
FH6 Live Map v0.9.15 compact nearest POI
```

6. В описание вставь текст из `RELEASE_NOTES_v0.9.15.md`.
7. В блок assets / binaries перетащи архив:

```text
FH6LiveMap_v0.9.15_compact_nearest_poi.zip
```

8. Нажми `Publish release`.

## D. Ссылка для Reddit

Если asset называется точно так:

```text
FH6LiveMap_v0.9.15_compact_nearest_poi.zip
```

то direct download link обычно будет таким:

```text
https://github.com/YOUR_GITHUB_NAME/YOUR_REPO_NAME/releases/latest/download/FH6LiveMap_v0.9.15_compact_nearest_poi.zip
```

Замени:

```text
YOUR_GITHUB_NAME
YOUR_REPO_NAME
```

После этого открой `REDDIT_POST_TEMPLATE.md`, вставь прямую ссылку в `Download:` и ссылку на репозиторий в `GitHub:`.

## E. Проверка перед публикацией Reddit-поста

1. Открой release в браузере.
2. Нажми на ZIP asset и проверь, что скачивание начинается.
3. Скопируй получившуюся ссылку.
4. Открой README в репозитории и проверь quick start.
5. В Reddit-пост вставь direct download link и repo link.
