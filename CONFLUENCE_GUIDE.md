# CSAT Survey Service - Руководство для операционной команды

## Обзор сервиса

**CSAT** (Customer Satisfaction) - это сервис автоматического сбора отзывов клиентов о качестве работы через опросы, привязанные к Jira-задачам.

### Что делает?

✅ Генерирует уникальные ссылки на опросы для каждой задачи
✅ Собирает оценки (1-5) и комментарии от клиентов
✅ Автоматически отправляет результаты обратно в Jira
✅ Поддерживает русский и английский языки
✅ Автоматически удаляет старые и использованные ссылки

---

## Как это работает? (Полный цикл)

### Этап 1️⃣: Создание ссылки

```
Jira Server → POST /survey/create
             ↓
CSAT Service: Генерирует уникальный токен
             ↓
Response: https://survey.ostrovok.ru/survey/ABC123XYZ
             ↓
Ссылка отправляется клиенту (в письме, в задаче, итд)
```

**Пример запроса:**
```
POST /survey/create
issue_key=PROJ-456
language=ru
```

**Ответ:**
```json
{
  "link": "https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg"
}
```

### Этап 2️⃣: Клиент открывает ссылку и видит форму

```
Клиент нажимает на ссылку
             ↓
Открывается форма опроса
             ↓
Форма показывает:
  - Вопрос "Как вам наше решение?"
  - 5 звёзд для оценки
  - Поле для комментария
```

### Этап 3️⃣: Клиент отправляет ответ

```
Клиент выбирает оценку (1-5)
             ↓
Если оценка ≤ 4, пишет комментарий (обязательно)
             ↓
Нажимает кнопку "Отправить"
             ↓
POST /survey/ABC123XYZ/submit
  score=5
  comment=Отличный сервис!
```

### Этап 4️⃣: Результат отправляется в Jira

```
CSAT Service получает ответ
             ↓
Проверяет корректность данных
             ↓
Отправляет вебхук в Jira:
{
  "issue_key": "PROJ-456",
  "score": 5,
  "comment": "Отличный сервис!"
}
             ↓
✅ Jira получает результат и может его обработать
```

**Если Jira не ответила:**
- При ошибке 5xx (сервер) → повторит 3 раза с задержкой
- При ошибке 4xx (клиент) → ошибка логируется, повтора нет
- При таймауте → повторит 3 раза

### Этап 5️⃣: Ссылка деактивируется

```
После получения ответа:
  ✅ Ссылка удаляется из памяти
  ✅ Она больше не работает
  ❌ Клиент не может ответить дважды

Если клиент не ответит за 168 часов (7 дней):
  ⏰ Ссылка автоматически удаляется
  ❌ Становится неактивной
```

---

## Где работает сервис?

### Домены

| Язык | Домен | Для кого |
|------|-------|---------|
| 🇷🇺 Русский | https://survey.ostrovok.ru | Российские клиенты |
| 🇬🇧 Английский | https://survey.emergingtravel.com | Зарубежные клиенты |

### Структура на сервере

```
Сервер: /opt/csat/
├── main.py                 ← Основное приложение
├── requirements.txt        ← Зависимости
├── .env                    ← Конфигурация (НЕ в git!)
├── static/
│   ├── index.html         ← Форма опроса
│   ├── csat.js            ← Логика формы
│   └── csat.css           ← Стили
└── README.md, KOLEGAM.md  ← Документация

Данные: /var/lib/csat/
├── surveys.json           ← ВСЕ активные ссылки (в памяти и на диске)
└── surveys.json.backup*   ← Автоматические бэкапы

Логи: /var/log/csat/
├── app.log                ← Текущий лог
└── app.log.*              ← Архивные логи (7 дней)
```

---

## Настройки (Конфигурация)

### Файл .env

```bash
# Слушать на этом адресе (внутренний)
CSAT_HOST=127.0.0.1
CSAT_PORT=8000

# Рабочие процессы (увеличить, если много запросов)
CSAT_WORKERS=4

# Время жизни ссылки (в часах)
CSAT_SURVEY_EXPIRY_HOURS=168          # 7 дней по умолчанию

# CORS - какие домены могут создавать ссылки
CSAT_ALLOWED_ORIGINS=https://survey.ostrovok.ru,https://survey.emergingtravel.com

# Куда отправлять результаты
JIRA_WEBHOOK_URL=https://help.etg.team/rest/cb-automation/latest/hooks/...
```

### Как изменить настройки?

```bash
# 1. Отредактировать
sudo nano /opt/csat/.env

# 2. Изменить нужный параметр (например, время жизни ссылок)
CSAT_SURVEY_EXPIRY_HOURS=240    # Вместо 168

# 3. Сохранить (Ctrl+O, Enter, Ctrl+X)

# 4. Перезагрузить сервис
sudo systemctl restart csat

# 5. Проверить
sudo systemctl status csat
```

### Параметры для редактирования

| Параметр | Когда менять | Пример |
|----------|---------|---------|
| CSAT_SURVEY_EXPIRY_HOURS | Нужно больше времени на ответ | Измени с 168 на 240 |
| CSAT_WORKERS | Сервис медленный под нагрузкой | Увеличь с 4 на 8 |
| JIRA_WEBHOOK_URL | Адрес Jira изменился | Обновить URL |

---

## Управление сервисом

### Проверка здоровья (1 минута)

```bash
# 1. Сервис запущен?
sudo systemctl status csat

# Должно быть "active (running)"

# 2. Слушает порт?
sudo ss -tulpn | grep 8000

# Должно быть "LISTEN"

# 3. Ошибок в логах нет?
sudo journalctl -u csat -n 20 | grep ERROR

# Ничего не должно быть выведено
```

### Базовые команды

```bash
# Проверить статус
sudo systemctl status csat

# Перезагрузить сервис
sudo systemctl restart csat

# Остановить
sudo systemctl stop csat

# Запустить
sudo systemctl start csat

# Логи в реальном времени (Ctrl+C выход)
sudo journalctl -u csat -f

# Последние 50 строк логов
sudo journalctl -u csat -n 50
```

---

## Мониторинг и статистика

### Посмотреть активные ссылки

```bash
# Все ссылки в красивом формате
sudo cat /var/lib/csat/surveys.json | jq .

# Сколько всего активных ссылок?
sudo cat /var/lib/csat/surveys.json | jq 'length'

# Только ещё не использованные
sudo cat /var/lib/csat/surveys.json | jq '.[] | select(.is_used==false)'

# Конкретное задание
sudo cat /var/lib/csat/surveys.json | jq '.[] | select(.issue_key=="ABC-123")'
```

### Размеры

```bash
# Размер файла данных
du -sh /var/lib/csat/surveys.json

# Размер логов
du -sh /var/log/csat/

# Общее использование диска
df -h /var/lib/csat
```

---

## Логи и диагностика

### Где найти логи?

**Способ 1: Системные логи (systemd)**
```bash
sudo journalctl -u csat -f    # В реальном времени
sudo journalctl -u csat -n 50 # Последние 50 строк
```

**Способ 2: Файл логов**
```bash
sudo tail -f /var/log/csat/app.log
```

### Поиск по логам

```bash
# Только ошибки
sudo journalctl -u csat -p err

# Создание ссылок
sudo journalctl -u csat | grep "Survey.*created"

# Ошибки Jira
sudo journalctl -u csat | grep -i "jira\|webhook"

# Конкретная задача
sudo journalctl -u csat | grep "ABC-123"

# За последний час
sudo journalctl -u csat --since "1 hour ago"
```

### Как читать логи?

```
2025-12-01 13:45:22 - INFO - Survey qVVWq created for ABC-123
   ↑ Время          ↑ Уровень  ↑ Что произошло

2025-12-01 13:45:23 - WARNING - Webhook retry for ABC-123
   ↑ Время          ↑ Уровень  ↑ Что произошло

2025-12-01 13:45:25 - ERROR - Connection error to Jira
   ↑ Время          ↑ Уровень  ↑ Ошибка
```

---

## Бэкапы и восстановление

### Бэкапы

Все активные ссылки хранятся в `/var/lib/csat/surveys.json`

```bash
# Сделать бэкап вручную
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Посмотреть все бэкапы
ls -lh /var/lib/csat/surveys.json.backup*
```

### Восстановление

```bash
# Список бэкапов
ls -lh /var/lib/csat/surveys.json.backup*

# Восстановить из конкретного бэкапа
sudo cp /var/lib/csat/surveys.json.backup.20251201_153000 /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# Перезагрузить сервис
sudo systemctl restart csat

# Проверить
sudo systemctl status csat
```

---

## Обновление сервиса

### Перед обновлением (Чек-лист)

- ✅ Сделать бэкап
- ✅ Проверить, что сервис работает
- ✅ Посмотреть количество активных ссылок

### Процесс обновления

```bash
# 1. Перейти в папку
cd /opt/csat

# 2. Сделать бэкап
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# 3. Подтянуть код из Git
sudo git pull origin master

# 4. Установить зависимости (если были изменения)
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt

# 5. Перезагрузить сервис
sudo systemctl restart csat

# 6. Проверить, что всё работает
sudo systemctl status csat
sudo cat /var/lib/csat/surveys.json | jq 'length'  # Проверить ссылки
```

### После обновления

```bash
# Проверить, что сервис работает
sudo systemctl is-active csat

# Посмотреть логи на ошибки
sudo journalctl -u csat -n 20 | grep -i error

# Проверить доступность
curl -I https://survey.ostrovok.ru/
```

---

## Частые проблемы и решения

### ❌ Nginx 502 Bad Gateway

**Причина:** Backend (CSAT) не отвечает

**Решение:**
```bash
# 1. Проверить, запущен ли сервис
sudo systemctl status csat

# 2. Если не запущен - запустить
sudo systemctl start csat

# 3. Если запущен - посмотреть ошибки
sudo journalctl -u csat -n 50

# 4. Перезагрузить nginx
sudo systemctl restart nginx
```

### ❌ Service Won't Start (Сервис не запускается)

**Причина:** Обычно проблемы с правами или синтаксисом

**Решение:**
```bash
# 1. Посмотреть ошибку
sudo journalctl -u csat -n 50

# 2. Проверить права доступа
ls -la /var/lib/csat/
ls -la /var/log/csat/

# 3. Исправить права (если нужно)
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat

# 4. Попробовать запустить
sudo systemctl start csat
sudo systemctl status csat
```

### ❌ Permission Denied

**Причина:** Неправильные права доступа на файлы/папки

**Решение:**
```bash
# Исправить права
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat

# Перезагрузить сервис
sudo systemctl restart csat
```

### ❌ JSON Corrupted (Повреждён файл данных)

**Причина:** Сбой при записи или скачивания

**Решение:**
```bash
# 1. Восстановить из бэкапа
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# 2. Если нет бэкапа - очистить
sudo bash -c 'echo "{}" > /var/lib/csat/surveys.json'
sudo chown csat:csat /var/lib/csat/surveys.json

# 3. Перезагрузить
sudo systemctl restart csat
```

### ❌ High Memory Usage (Высокое потребление памяти)

**Причина:** Слишком много рабочих процессов или ссылок

**Решение:**
```bash
# 1. Проверить рабочие процессы
ps aux | grep uvicorn

# 2. Уменьшить количество рабочих процессов
sudo nano /opt/csat/.env
# Измени: CSAT_WORKERS=2 (вместо 4)

# 3. Перезагрузить
sudo systemctl restart csat
```

---

## API для интеграции

### Создать новую ссылку

```
POST /survey/create

Параметры:
  issue_key (строка)  - ключ задачи в Jira (например, ABC-123)
  language (строка)   - язык (ru или en)

Пример:
  curl -X POST https://survey.ostrovok.ru/survey/create \
    -F "issue_key=ABC-123" \
    -F "language=ru"

Ответ (200):
  {
    "link": "https://survey.ostrovok.ru/survey/qVVWqneYVSv_8kVAZRYMUg"
  }

Ошибки:
  400 - неправильные параметры
  403 - доступ запрещён (не с нужного IP)
```

### Отправить ответ

```
POST /survey/{token}/submit

Параметры:
  score (число)       - оценка 1-5
  comment (строка)    - комментарий

Пример:
  curl -X POST https://survey.ostrovok.ru/survey/qVVWq/submit \
    -F "score=5" \
    -F "comment=Спасибо"

Ответ (200):
  {
    "status": "ok"
  }

Ошибки:
  400 - неправильная оценка или отсутствует комментарий
  403 - ссылка неверная или уже использована
  409 - уже отправили по этой ссылке
```

---

## Быстрые ссылки и команды

### Самое срочное (если что-то сломалось)

```bash
# 1. Проверить статус
sudo systemctl status csat

# 2. Если проблема - перезагрузить
sudo systemctl restart csat

# 3. Посмотреть ошибку
sudo journalctl -u csat -n 50

# 4. Восстановить из бэкапа (если совсем плохо)
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo systemctl restart csat
```

### Полезные команды

| Команда | Для чего |
|---------|---------|
| `sudo systemctl status csat` | Статус сервиса |
| `sudo systemctl restart csat` | Перезагрузить |
| `sudo journalctl -u csat -f` | Логи в реальном времени |
| `sudo cat /var/lib/csat/surveys.json \| jq length` | Количество ссылок |
| `sudo tail -f /var/log/csat/app.log` | Файл логов |
| `sudo systemctl is-active csat && echo "OK" \|\| echo "DOWN"` | Быстрая проверка |

---

## Безопасность

### Что защищено?

✅ **HTTPS** - весь трафик шифруется (SSL/TLS)
✅ **Rate Limiting** - максимум 10 запросов в секунду
✅ **CORS** - только нужные домены могут создавать ссылки
✅ **Уникальные токены** - невозможно угадать или перебрать
✅ **Непривилегированный пользователь** - сервис работает от пользователя `csat`, не от `root`
✅ **Атомарная запись** - файлы не повредятся при сбое

### Рекомендации

1. Регулярно проверяйте логи на подозрительную активность
2. Делайте бэкапы перед обновлениями
3. Обновляйте сервис регулярно (следите за Git репозиторием)
4. Мониторьте размер логов (автоматически ротируются каждый день)
5. Держите SSL сертификаты обновлёнными (автоматически, через Certbot)

---

## Контрольный список для новичка

### Первый день

- [ ] Понять, как работает сервис (прочитать Обзор выше)
- [ ] Посмотреть текущие логи (`sudo journalctl -u csat -n 50`)
- [ ] Проверить статус (`sudo systemctl status csat`)
- [ ] Посмотреть активные ссылки (`sudo cat /var/lib/csat/surveys.json | jq .`)
- [ ] Сделать первый бэкап (`sudo cp /var/lib/csat/surveys.json ...`)

### Регулярно

- [ ] Проверять логи на ошибки (1-2 раза в день)
- [ ] Мониторить размер данных (1 раз в неделю)
- [ ] Проверять SSL сертификат (1 раз в месяц: `sudo certbot certificates`)
- [ ] Делать бэкапы перед обновлениями

### При изменении конфига

- [ ] Отредактировать `/opt/csat/.env`
- [ ] Перезагрузить сервис (`sudo systemctl restart csat`)
- [ ] Проверить, что сервис запущен (`sudo systemctl status csat`)
- [ ] Посмотреть логи на ошибки (`sudo journalctl -u csat -n 20`)

---

## Дополнительные ресурсы

- 📖 **Полное руководство:** `/opt/csat/README.md`
- 📚 **Для коллег:** `/opt/csat/KOLEGAM.md`
- ⚡ **Шпаргалка:** `/opt/csat/SHPARGALKA.md`
- 🔗 **Git репозиторий:** https://gitlab.ostrovok.ru/atlassian_team/csat-service

---

## История изменений

**Последнее обновление:** декабрь 2025

### Что недавно изменилось?

✅ Исправлено удаление истекших ссылок при перезагрузке
✅ Добавлена документация для операционной команды
✅ Улучшено логирование
✅ Оптимизирована работа с большим количеством ссылок

---

**Есть вопросы?** Посмотри секцию "Частые проблемы и решения" выше или обратись к разработчику.
