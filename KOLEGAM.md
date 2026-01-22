# CSAT Сервис: Полное руководство для коллег

Это руководство написано понятным языком. Здесь нет лишнего, только то, что нужно знать для работы с сервисом.

---

## Что это такое?

**CSAT** = Customer Satisfaction (удовлетворённость клиентов)

Это сервис, который:
- Генерирует уникальные ссылки на опросы для каждой Jira-задачи
- Позволяет клиентам оставить оценку (1-5 звёзд) и комментарий
- Автоматически отправляет результат обратно в Jira
- Поддерживает два языка: русский и английский
- Автоматически удаляет старые неиспользованные ссылки

**Домены:**
- Русский: https://survey.ostrovok.ru
- Английский: https://survey.emergingtravel.com

---

## Как это работает? (Полный цикл)

### Шаг 1: Получить ссылку на опрос

Кто-то (обычно Jira webhook) делает запрос на `/survey/create`:

```bash
curl -X POST https://survey.ostrovok.ru/survey/create \
  -F "issue_key=ABC-123" \
  -F "language=ru"
```

**Параметры:**
- `issue_key` - идентификатор задачи в Jira (например, `PROJ-456`)
- `language` - язык формы (`ru` или `en`)

**Ответ:**
```json
{
  "link": "https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg"
}
```

Это уникальный токен, созданный для этой задачи. Он больше никогда не повторится.

### Шаг 2: Клиент открывает ссылку

Клиент переходит по ссылке → видит форму с вопросом и 5 звёздочками.

Форма выглядит так:
- Рейтинг 1-5
- Комментарий (обязателен, если оценка ≤4)
- Кнопка "Отправить"

### Шаг 3: Клиент отправляет ответ

Клиент выбирает рейтинг и пишет комментарий → нажимает "Отправить"

```bash
# За кулисами происходит POST запрос:
curl -X POST https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg/submit \
  -F "score=5" \
  -F "comment=Отличный сервис!"
```

### Шаг 4: Результат отправляется в Jira

Сервис делает вебхук запрос на Jira:

```json
{
  "issue_key": "ABC-123",
  "score": 5,
  "comment": "Отличный сервис!"
}
```

Jira получает эту информацию и может сохранить её или отправить дальше.

**Что дальше?**
- Если Jira ответила успешно (200-299) → готово
- Если ошибка 5xx → сервис повторит попытку (максимум 3 раза) с экспоненциальной задержкой
- Если ошибка 4xx → ошибка клиента, повторять не будет

### Шаг 5: Ссылка становится неактивной

После того, как клиент отправит ответ, ссылка удаляется из памяти и больше не работает.

Если клиент не ответит за **168 часов (7 дней)** → ссылка автоматически удалится и будет считаться истекшей.

---

## Настройки (Файл .env)

На сервере находится файл `/opt/csat/.env`. Там хранятся все настройки.

Посмотреть текущие значения:
```bash
sudo cat /opt/csat/.env
```

Отредактировать:
```bash
sudo nano /opt/csat/.env
```

Перезагрузить сервис после изменений:
```bash
sudo systemctl restart csat
```

### Основные параметры

| Параметр | По умолчанию | Что это |
|----------|---------|---------|
| `CSAT_HOST` | `127.0.0.1` | На какой IP слушать (не меняйте, это внутренний адрес) |
| `CSAT_PORT` | `8000` | Какой порт использовать (не меняйте) |
| `CSAT_WORKERS` | `4` | Сколько рабочих процессов (увеличьте, если медленно) |
| `CSAT_SURVEY_EXPIRY_HOURS` | `168` | Через сколько часов удалять неиспользованные ссылки |
| `CSAT_ALLOWED_ORIGINS` | (нужно указать) | Какие домены могут создавать ссылки |
| `JIRA_WEBHOOK_URL` | (нужно указать) | Куда отправлять результаты в Jira |

**Для вас важны только:**
- `CSAT_SURVEY_EXPIRY_HOURS` - если нужно изменить время жизни ссылок (по умолчанию 7 дней = 168 часов)
- `JIRA_WEBHOOK_URL` - адрес, куда отправляются результаты

---

## Как управлять сервисом?

### Проверить статус

```bash
sudo systemctl status csat
```

Должно быть написано **"active (running)"** - значит всё работает.

### Перезагрузить сервис

После изменения конфига или обновления кода:

```bash
sudo systemctl restart csat
```

### Остановить/запустить

```bash
# Остановить
sudo systemctl stop csat

# Запустить
sudo systemctl start csat
```

### Посмотреть логи в реальном времени

```bash
sudo journalctl -u csat -f
```

Нажмите `Ctrl+C` чтобы выйти.

### Посмотреть последние 50 строк логов

```bash
sudo journalctl -u csat -n 50
```

---

## Как работают ссылки? (Файл surveys.json)

Все активные ссылки хранятся в файле: `/var/lib/csat/surveys.json`

Это JSON-файл со всеми текущими опросами:

```json
{
  "qVVWqneYVSv_8kVAZRYMUg": {
    "issue_key": "ABC-123",
    "is_used": false,
    "language": "ru",
    "created_at": "2025-11-24T13:16:31.905300"
  },
  "zdkJQQhdCfVxzu3qzDBIww": {
    "issue_key": "ABC-124",
    "is_used": true,
    "language": "en",
    "created_at": "2025-11-24T14:27:13.826420"
  }
}
```

**Что означает каждое поле:**
- `is_used: false` - ссылка ещё не использована
- `is_used: true` - клиент уже ответил, ссылка больше не работает
- `language` - язык опроса (ru или en)
- `created_at` - когда была создана ссылка

### Посмотреть все активные ссылки

```bash
sudo cat /var/lib/csat/surveys.json | jq .
```

Или просто посмотреть красиво:

```bash
sudo python3 -m json.tool /var/lib/csat/surveys.json
```

### Очистить все ссылки (если что-то сломалось)

```bash
# Сделать бэкап на всякий случай
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup

# Очистить файл
sudo bash -c 'echo "{}" > /var/lib/csat/surveys.json'

# Перезагрузить сервис
sudo systemctl restart csat
```

---

## Как обновить сервис?

Код хранится в Git. Если произошли изменения в коде, нужно их подтянуть на сервер.

### Обновить код

```bash
# Перейти в папку
cd /opt/csat

# Сделать бэкап данных (рекомендуется!)
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Подтянуть новый код
sudo git pull origin master

# Если были новые зависимости
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt

# Перезагрузить сервис
sudo systemctl restart csat

# Проверить, что всё работает
sudo systemctl status csat
```

### Откатить обновление (если что-то сломалось)

```bash
# Посмотреть историю коммитов
cd /opt/csat && git log --oneline -5

# Откатить на предыдущий коммит
git revert HEAD

# Или откатить на конкретный коммит
git revert abc123def

# Перезагрузить сервис
sudo systemctl restart csat
```

---

## Проверка здоровья сервиса

### Быстрая проверка (всё ли работает)

```bash
# 1. Сервис запущен?
sudo systemctl is-active csat

# Должно быть: active

# 2. Слушает ли порт 8000?
sudo ss -tulpn | grep 8000

# Должно быть: LISTEN

# 3. Есть ли ошибки в логах?
sudo journalctl -u csat -n 20 | grep ERROR

# Если ничего не вывелось - ошибок нет
```

### Проверить доступность

```bash
# Проверить русский сайт
curl -I https://survey.ostrovok.ru/

# Проверить английский
curl -I https://survey.emergingtravel.com/

# Должно быть: HTTP/2 200
```

---

## Мониторинг и статистика

### Сколько активных ссылок?

```bash
sudo cat /var/lib/csat/surveys.json | jq 'length'
```

### Размер файлов

```bash
# Данные
du -sh /var/lib/csat/surveys.json

# Логи
du -sh /var/log/csat/
```

### Память и CPU

```bash
# Сколько памяти использует сервис?
ps aux | grep uvicorn
```

---

## Частые ошибки и решения

### Ошибка: "Service is running but unhealthy"

Может быть несколько причин:

```bash
# 1. Посмотреть логи
sudo journalctl -u csat -n 50

# 2. Проверить диск
df -h /var/lib/csat

# 3. Проверить права доступа
ls -la /var/lib/csat/

# 4. Если права неправильные:
sudo chown -R csat:csat /var/lib/csat
sudo chmod 750 /var/lib/csat
```

### Ошибка: "nginx 502 Bad Gateway"

Это значит, что Nginx не может подключиться к сервису.

```bash
# 1. Проверить, запущен ли сервис
sudo systemctl status csat

# 2. Если не запущен - запустить
sudo systemctl start csat

# 3. Если запущен, но всё равно ошибка - посмотреть логи
sudo tail -f /var/log/nginx/csat.error.log
```

### Ошибка: "Permission denied"

Если вы видите в логах "Permission denied", проблема с правами доступа.

```bash
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
sudo systemctl restart csat
```

### Ошибка: "surveys.json is corrupted"

Если JSON-файл повреждён:

```bash
# 1. Восстановить из бэкапа
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# 2. Или просто очистить
sudo bash -c 'echo "{}" > /var/lib/csat/surveys.json'

# 3. Перезагрузить
sudo systemctl restart csat
```

---

## Бэкапы и восстановление

### Сделать бэкап

```bash
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)
```

### Посмотреть все бэкапы

```bash
ls -lh /var/lib/csat/surveys.json.backup*
```

### Восстановить из бэкапа

```bash
# Посмотреть когда был создан бэкап
ls -lh /var/lib/csat/surveys.json.backup*

# Восстановить нужный
sudo cp /var/lib/csat/surveys.json.backup.20251201_153000 /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# Перезагрузить сервис
sudo systemctl restart csat
```

---

## Логи и отладка

### Где хранятся логи?

Два места:

1. **systemd journalctl**
   ```bash
   sudo journalctl -u csat
   ```

2. **Файл логов**
   ```bash
   sudo tail -f /var/log/csat/app.log
   ```

### Посмотреть логи за определённый период

```bash
# За последний час
sudo journalctl -u csat --since "1 hour ago"

# Конкретная дата
sudo journalctl -u csat --since "2025-12-01 10:00:00"

# С ошибками
sudo journalctl -u csat -p err
```

### Ротация логов

Логи автоматически ротируются каждый день в полночь. Старые логи хранятся 7 дней, потом удаляются.

```bash
ls -lh /var/log/csat/
```

---

## API для интеграции

### Создать новую ссылку

```bash
curl -X POST https://survey.ostrovok.ru/survey/create \
  -F "issue_key=ABC-123" \
  -F "language=ru"
```

**Ответ:**
```json
{
  "link": "https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg"
}
```

**Коды ошибок:**
- 200 - OK
- 400 - Неправильные параметры
- 403 - Доступ запрещён (не с нужного IP)

### Отправить ответ

```bash
curl -X POST https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg/submit \
  -F "score=5" \
  -F "comment=Спасибо"
```

**Параметры:**
- `score` - оценка 1-5 (обязательно)
- `comment` - комментарий (обязателен, если score ≤ 4)

**Коды ошибок:**
- 200 - OK
- 400 - Неправильная оценка или не хватает комментария
- 403 - Ссылка неверная или уже использована
- 409 - Уже отправили ответ по этой ссылке

---

## Безопасность

### Что защищено?

- ✅ HTTPS шифрование (SSL/TLS)
- ✅ Rate limiting (максимум 10 запросов в секунду)
- ✅ CORS - только нужные домены
- ✅ Сервис запущен от непривилегированного пользователя (csat)
- ✅ Атомарная запись файлов (без повреждений при сбое)
- ✅ Уникальные токены (невозможно угадать)

### Что нужно помнить?

1. **Сохраняйте бэкапы** - surveys.json содержит все ответы клиентов
2. **Проверяйте логи** - ищите подозрительную активность
3. **Обновляйте регулярно** - безопасность зависит от обновлений
4. **Защищайте /survey/create** - это эндпоинт создания ссылок, должен быть доступен только Jira серверу

---

## Полезные команды (шпаргалка)

```bash
# Статус сервиса
sudo systemctl status csat

# Перезагрузить
sudo systemctl restart csat

# Логи в реальном времени
sudo journalctl -u csat -f

# Посмотреть все ссылки
sudo cat /var/lib/csat/surveys.json | jq .

# Сколько активных ссылок?
sudo cat /var/lib/csat/surveys.json | jq 'length'

# Обновить из Git
cd /opt/csat && sudo git pull origin master

# Сделать бэкап
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Проверить диск
du -sh /var/lib/csat

# Проверить права доступа
ls -la /var/lib/csat/

# Проверить SSL сертификат
sudo certbot certificates
```

---

## Контакты и помощь

Если что-то не работает:

1. **Проверьте логи:**
   ```bash
   sudo journalctl -u csat -n 50
   ```

2. **Убедитесь, что сервис запущен:**
   ```bash
   sudo systemctl status csat
   ```

3. **Перезагрузите:**
   ```bash
   sudo systemctl restart csat
   ```

4. **Восстановите из бэкапа:**
   ```bash
   sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
   sudo systemctl restart csat
   ```

Если ничего не помогает - посмотрите полный README.md в репозитории или свяжитесь с разработчиком.
