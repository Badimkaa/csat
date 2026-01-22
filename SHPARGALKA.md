# CSAT Шпаргалка: Самые нужные команды

Копируй и пасти прямо в терминал. Всё работает на сервере `/opt/csat`.

---

## 🔴 СРОЧНО! Сервис не работает?

```bash
# 1. Проверить статус
sudo systemctl status csat

# 2. Если "inactive" - запустить
sudo systemctl start csat

# 3. Посмотреть ошибку
sudo journalctl -u csat -n 20

# 4. Если всё сломалось - восстановить
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo systemctl restart csat
```

---

## 📋 Проверка здоровья (10 секунд)

```bash
# Статус?
sudo systemctl is-active csat

# Должно быть: active

# Слушает порт?
sudo ss -tulpn | grep 8000

# Должно быть: LISTEN

# Ошибки?
sudo journalctl -u csat -n 20 | grep -i error

# Ничего не должно быть выведено
```

---

## 🔄 Перезагрузить сервис

```bash
# После изменения конфига или обновления
sudo systemctl restart csat

# Проверить
sudo systemctl status csat
```

---

## 📊 Посмотреть активные ссылки

```bash
# Все ссылки красиво
sudo cat /var/lib/csat/surveys.json | jq .

# Только количество
sudo cat /var/lib/csat/surveys.json | jq 'length'

# Какие уже использованы?
sudo cat /var/lib/csat/surveys.json | jq '.[] | select(.is_used==true)'

# Какие ещё активны?
sudo cat /var/lib/csat/surveys.json | jq '.[] | select(.is_used==false)'

# Посмотреть по конкретному issue
sudo cat /var/lib/csat/surveys.json | jq '.[] | select(.issue_key=="ABC-123")'
```

---

## 📝 Логи

```bash
# В реальном времени (Ctrl+C чтобы выйти)
sudo journalctl -u csat -f

# Последние 50 строк
sudo journalctl -u csat -n 50

# Только ошибки
sudo journalctl -u csat -p err -n 20

# За последний час
sudo journalctl -u csat --since "1 hour ago"

# За конкретный день
sudo journalctl -u csat --since "2025-12-01" --until "2025-12-02"

# Файл логов
sudo tail -f /var/log/csat/app.log

# Все файлы логов
ls -lh /var/log/csat/
```

---

## 🔧 Конфигурация

```bash
# Посмотреть текущие настройки
sudo cat /opt/csat/.env

# Отредактировать
sudo nano /opt/csat/.env

# Не забыть перезагрузить сервис!
sudo systemctl restart csat
```

### Основные параметры для редактирования

```bash
# Время жизни ссылок (в часах)
CSAT_SURVEY_EXPIRY_HOURS=168

# Количество рабочих процессов (если медленно - увеличить)
CSAT_WORKERS=4

# Куда отправлять результаты
JIRA_WEBHOOK_URL=https://...
```

---

## 💾 Бэкапы

```bash
# Сделать бэкап
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Посмотреть все бэкапы
ls -lh /var/lib/csat/surveys.json.backup*

# Восстановить из конкретного бэкапа
sudo cp /var/lib/csat/surveys.json.backup.20251201_153000 /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json
sudo systemctl restart csat
```

---

## 🚀 Обновить сервис

```bash
# Перейти в папку
cd /opt/csat

# Сделать бэкап
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Подтянуть новый код
sudo git pull origin master

# Установить зависимости (если что-то изменилось)
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt

# Перезагрузить
sudo systemctl restart csat

# Проверить
sudo systemctl status csat
```

---

## 🧹 Очистить старые ссылки

```bash
# Сервис делает это автоматически, но если нужно срочно:
sudo bash -c 'echo "{}" > /var/lib/csat/surveys.json'
sudo systemctl restart csat

# Или очистить только использованные:
sudo cat /var/lib/csat/surveys.json | jq 'del(.[] | select(.is_used==true))' > /tmp/clean.json
sudo mv /tmp/clean.json /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json
sudo systemctl restart csat
```

---

## 📦 Информация о системе

```bash
# Размер данных
du -sh /var/lib/csat/surveys.json

# Размер логов
du -sh /var/log/csat/

# Общее использование
df -h /var/lib/csat

# Сколько памяти использует?
ps aux | grep uvicorn

# Когда создан файл?
stat /var/lib/csat/surveys.json

# Кто владелец файлов?
ls -la /var/lib/csat/
```

---

## 🔐 Права доступа (если что-то сломалось)

```bash
# Исправить права
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat

# Проверить
ls -la /var/lib/csat/
```

---

## 🌐 Тестирование API

```bash
# Создать ссылку
curl -X POST https://survey.ostrovok.ru/survey/create \
  -F "issue_key=TEST-123" \
  -F "language=ru"

# Отправить ответ (замени ТУТ_ТОКЕН на реальный)
curl -X POST https://survey.ostrovok.ru/survey/ТУТ_ТОКЕН/submit \
  -F "score=5" \
  -F "comment=Спасибо"

# Проверить доступность
curl -I https://survey.ostrovok.ru/

# Проверить localhost
curl -X POST http://localhost:8000/survey/create \
  -F "issue_key=TEST-456" \
  -F "language=en"
```

---

## 🔍 Поиск по логам

```bash
# Ошибки при создании ссылки
sudo journalctl -u csat | grep "create"

# Ошибки Jira webhook
sudo journalctl -u csat | grep -i "jira\|webhook"

# Все 403 ошибки
sudo journalctl -u csat | grep "403"

# Конкретное issue
sudo journalctl -u csat | grep "ABC-123"

# Конкретный токен
sudo journalctl -u csat | grep "qVVWqneYVSv"
```

---

## 🆘 Частые проблемы

### Nginx 502 Bad Gateway

```bash
# Проверить backend
sudo ss -tulpn | grep 8000

# Проверить сервис
sudo systemctl status csat

# Посмотреть nginx ошибку
sudo tail -f /var/log/nginx/csat.error.log

# Перезагрузить nginx
sudo systemctl restart nginx
```

### Permission Denied

```bash
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
sudo systemctl restart csat
```

### JSON Corrupted

```bash
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json
sudo systemctl restart csat
```

### Слишком много памяти

```bash
# Уменьшить рабочие процессы в .env
CSAT_WORKERS=2

# Перезагрузить
sudo systemctl restart csat
```

---

## 📞 Git операции

```bash
# Посмотреть текущий коммит
cd /opt/csat && git log --oneline -1

# Посмотреть историю
git log --oneline -10

# Проверить статус
git status

# Увидеть изменения
git diff

# Откатить последнее изменение
git revert HEAD
sudo systemctl restart csat
```

---

## ⏰ Планировщик задач (cron)

Сервис делает cleanup автоматически каждый час. Но если нужно вручную:

```bash
# Проверить crontab
sudo -u csat crontab -l

# Отредактировать
sudo -u csat crontab -e

# Добавить cleanup каждый день в 3:00
0 3 * * * /opt/csat/venv/bin/python -c "from main import cleanup_expired_surveys; cleanup_expired_surveys()"
```

---

## 📱 Мониторинг в реальном времени

```bash
# Все в одном окне (Ctrl+C чтобы выйти)
watch -n 1 'echo "=== STATUS ===" && sudo systemctl is-active csat && echo "=== LINKS ===" && sudo cat /var/lib/csat/surveys.json | jq length && echo "=== ERRORS ===" && sudo journalctl -u csat -n 5 | grep -i error || echo "No errors"'
```

---

## 🎯 Быстрые проверки перед презентацией

```bash
# 1. Сервис работает?
sudo systemctl is-active csat && echo "✅ OK" || echo "❌ DOWN"

# 2. Сколько ссылок активно?
echo -n "Active links: " && sudo cat /var/lib/csat/surveys.json | jq 'length'

# 3. Нет ошибок?
sudo journalctl -u csat -n 10 | grep -i error && echo "❌ ERRORS FOUND" || echo "✅ No errors"

# 4. Диск не переполнен?
echo -n "Disk: " && du -sh /var/lib/csat/ && du -sh /var/log/csat/

# 5. HTTPS работает?
curl -I https://survey.ostrovok.ru/ 2>/dev/null | head -1
```

---

## 💡 Pro Tips

### Скопировать команду быстро

```bash
# Если часто нужна одна команда, создай alias
echo 'alias csat-status="sudo systemctl status csat"' >> ~/.bashrc
source ~/.bashrc
csat-status

# Или функцию
cat >> ~/.bashrc << 'EOF'
csat-check() {
  echo "=== Service Status ===" && sudo systemctl is-active csat
  echo "=== Active Links ===" && sudo cat /var/lib/csat/surveys.json | jq 'length'
  echo "=== Recent Errors ===" && sudo journalctl -u csat -n 5 | grep ERROR || echo "No errors"
}
EOF
source ~/.bashrc
csat-check
```

### Автоматический мониторинг

```bash
# Проверка каждые 30 секунд
watch -n 30 'sudo systemctl is-active csat && date'

# В отдельном окне (screen/tmux)
screen -S csat-monitor
sudo journalctl -u csat -f
# Ctrl+A, затем D чтобы выйти
screen -r csat-monitor  # чтобы вернуться
```

### Быстрое восстановление после сбоя

```bash
# Сохрани в файл и запусти при проблеме
cat > /tmp/fix-csat.sh << 'EOF'
#!/bin/bash
echo "Fixing CSAT service..."
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
sudo systemctl restart csat
echo "Done. Status:"
sudo systemctl status csat
EOF

chmod +x /tmp/fix-csat.sh
/tmp/fix-csat.sh
```

---

## 📋 Чек-лист перед обновлением

```bash
# Перед git pull, выполни:
cd /opt/csat

# ✅ 1. Бэкап
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# ✅ 2. Проверить статус
sudo systemctl status csat

# ✅ 3. Посмотреть количество активных ссылок
sudo cat /var/lib/csat/surveys.json | jq 'length'

# ✅ 4. Сделать git pull
sudo git pull origin master

# ✅ 5. Обновить зависимости
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt

# ✅ 6. Перезагрузить
sudo systemctl restart csat

# ✅ 7. Проверить, что всё работает
sleep 5
sudo systemctl status csat
sudo cat /var/lib/csat/surveys.json | jq 'length'
```

---

**Ещё вопросы?** Читай полный README.md или KOLEGAM.md 🚀
