# Tuya 5 Relay Dashboard

Веб-панель на русском для мониторинга и управления пятью устройствами Tuya Smart / Smart Life.

## Возможности
- Индивидуальные кнопки Вкл/Выкл и общее управление всеми пятью реле.
- Напряжение, ток и мощность, если устройство отдаёт эти данные.
- Отдельный график каждого устройства, опрос каждые 10 секунд, история последних 30 точек.
- Сводка устройств на связи, включённых реле и суммарной мощности.
- Ключи Tuya хранятся на сервере.

## Настройка Tuya
1. Войдите на https://iot.tuya.com/ и создайте Cloud Project для Smart Home.
2. Выберите регион проекта и привяжите аккаунт Tuya Smart/Smart Life через Link Tuya App Account.
3. Проверьте доступность API для получения статуса и управления устройствами.
4. Скопируйте Access ID, Access Secret и Device ID пяти реле.
5. Выберите endpoint региона проекта (например, Европа: `https://openapi.tuyaeu.com`).

## Запуск на Windows
Нужен Python 3.10+.
```powershell
git clone https://github.com/vittagan/tuayapp.git
cd tuayapp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Открой `.env`, впиши ключи Tuya и реальные ID устройств, затем:
```powershell
python app.py
```
Открой http://127.0.0.1:5000

## Linux/macOS
```bash
git clone https://github.com/vittagan/tuayapp.git
cd tuayapp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Важно: datapoint и масштабы
Коды `switch_1`, `cur_power`, `cur_current`, `cur_voltage` и множители — распространённые примеры, но они зависят от модели. Сверьте ответ `GET /v1.0/devices/{device_id}/status`; поправьте `switch_code`, `dps` и `scale` в `.env`. Если модель не измеряет параметр, интерфейс покажет `—`.

Графики пока хранят данные в памяти открытой вкладки браузера; после перезагрузки история пропадает. Это не долговременный архив.

## Безопасность
- Не добавляйте `.env` с ключами в GitHub.
- Не публикуйте сервер напрямую в интернет без HTTPS и авторизации: API управления в этом примере не защищён входом.
- Общая команда отправляется каждому реле по отдельности; ошибки отдельных устройств показываются в уведомлении.
