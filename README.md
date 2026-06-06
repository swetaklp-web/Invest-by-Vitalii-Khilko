# Invest by Vitalii Khilko — Telegram automation MVP

Система генерирует инвестиционные посты по рынку США из `data/manual_inputs.json`,
создаёт PNG-обложку, отправляет черновик в закрытый Telegram-чат и публикует его
в `@Financebks` только после ручного нажатия кнопки **✅ Опубликовать**.

## Что входит в MVP

- два формата: `morning_brief` и `evening_theme`;
- структурированный JSON от OpenAI;
- отдельный quality-check и служебные предупреждения;
- стабильная HTML/CSS → PNG обложка 1280×720;
- кнопки публикации, отклонения и двух вариантов переработки;
- файловые черновики, опубликованные записи и JSONL-логи;
- заглушки для будущих X/Twitter, Telegram, Yahoo Finance и Barchart источников;
- два расписания GitHub Actions.

Никакие реальные токены или ключи не должны попадать в репозиторий, логи или
workflow-файлы. Все доступы передаются только через переменные окружения и
GitHub Secrets.

## 1. Установка

Требуется Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 2. Локальный `.env`

Создайте локальный `.env` на основе `.env.example`. Файл `.env` исключён из Git.

```dotenv
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_REVIEW_CHAT_ID=-5253592951
TELEGRAM_CHANNEL_ID=@Financebks
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=
X_API_KEY=
BARCHART_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

В MVP используются только `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_REVIEW_CHAT_ID` и `TELEGRAM_CHANNEL_ID`. Остальные переменные
зарезервированы для будущих интеграций.

## 3. GitHub Secrets

Откройте **Settings → Secrets and variables → Actions → New repository secret**
и добавьте:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_REVIEW_CHAT_ID` со значением `-5253592951`
- `TELEGRAM_CHANNEL_ID` со значением `@Financebks`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `X_API_KEY`
- `BARCHART_API_KEY`

Не добавляйте значения секретов в YAML, README, код или логи.

## 4. Telegram-настройка

### Как получить `TELEGRAM_REVIEW_CHAT_ID`

1. Добавьте `@Invest_by_VitaliiKhilko_bot` в закрытый чат согласования.
2. Напишите сообщение в чат.
3. Локально вызовите Bot API `getUpdates` с токеном только через окружение или
   используйте диагностический скрипт, который не печатает токен.
4. Найдите отрицательный `chat.id`. Для текущего чата это `-5253592951`.

### Канал и права бота

Основной канал: [@Financebks](https://t.me/Financebks).

Добавьте бота администратором в канал и разрешите публикацию сообщений. Также
добавьте его в чат согласования, чтобы он мог отправлять сообщения и кнопки.
`TELEGRAM_CHANNEL_ID` можно задавать как публичный username `@Financebks`.

### Перевыпуск bot token

Если токен раскрыт, откройте `@BotFather`, выберите бота, выполните отзыв
текущего токена и создайте новый. После этого обновите только локальный `.env`
и GitHub Secret `TELEGRAM_BOT_TOKEN`.

## 5. Запуск MVP локально

Отредактируйте `data/manual_inputs.json`, затем в одном терминале запустите
постоянный обработчик кнопок:

```bash
python -m app.main bot
```

Во втором терминале создайте тестовый черновик:

```bash
python -m app.main generate --type morning_brief
```

Для вечерней темы:

```bash
python -m app.main generate --type evening_theme
```

Черновик и картинка появятся в `data/drafts/`, после публикации запись также
сохранится в `data/published/`, а события и ошибки — в `data/logs/`.

## 6. Как работает согласование

Бот отправляет обложку и отдельное текстовое сообщение со служебным блоком:

- **✅ Опубликовать** — отправляет картинку и текст в `@Financebks`;
- **🔁 Переделать короче** — повторно вызывает OpenAI и создаёт новый черновик;
- **🧠 Сделать глубже** — создаёт более подробную версию;
- **❌ Отклонить** — сохраняет статус `rejected`.

Quality-check проверяет длину, дату, тикеры, запрещённые формулировки, прямые
рекомендации, обещания доходности, маркировку слухов и `risk_flags`. Не прошедший
проверку пост всё равно приходит в чат, но никогда не публикуется автоматически.
В MVP автоматической публикации вообще нет: любое размещение требует кнопки.

## 7. GitHub Actions

Workflow `morning_post.yml` запускается по будням в `13:10 UTC`, то есть в
`16:10 MSK`. `evening_post.yml` запускается в `18:30 UTC`, то есть в `21:30 MSK`.
Оба workflow также можно запустить вручную во вкладке **Actions**.

Важно: GitHub Actions — краткоживущие машины. Они могут создать и отправить
черновик, но локальные файлы этого запуска исчезнут после завершения job.
Обработчик кнопок должен быть постоянно развёрнут на VPS/Render/Railway и иметь
общее постоянное хранилище с генератором. Для полностью облачного production
варианта замените файловое хранилище на PostgreSQL/S3 и запускайте генерацию на
том же сервисе либо вызывайте его защищённый endpoint из Actions.

## 8. Расширение источников

- **X/Twitter:** реализовать `app/sources/x_reader.py`, читать `X_API_KEY` только
  из окружения и нормализовать сигналы в формат `manual_inputs.json`.
- **Telegram:** реализовать `app/sources/telegram_reader.py` через Telethon/MTProto
  с `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`. Bot API
  оставлять только для отправки и публикации.
- **Yahoo Finance:** добавить сбор публичных рыночных данных в `yahoo.py`.
- **Barchart:** использовать `BARCHART_API_KEY` в `barchart.py`.
- **Oninvest:** добавить отдельный адаптер и нормализацию источников.

Каждый сигнал должен содержать источник, суть, тикеры/секторы, воздействие,
силу, горизонт, дату и тип катализатора. Перед подключением источника проверьте
его условия использования и лицензионные ограничения.

## Проверки

```bash
pytest
```

