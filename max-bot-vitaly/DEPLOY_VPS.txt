================================================================================
  ДЕПЛО НА VPS — Контент-машина napitki133.ru
================================================================================

Бот один: индексация сайта, выборка по кругу/вразнобой, ИИ-текст, публикация
в 3 канала Telegram и 3 канала MAX по расписанию (МСК).

Python: 3.9+ (3.10, 3.11, 3.12). Проверка: python3 --version

--------------------------------------------------------------------------------
1. SSH, клон, venv
--------------------------------------------------------------------------------
   ssh root@IP_СЕРВЕРА
   cd ~
   git clone https://github.com/blockscrafting-arch/vitaly1.git
   cd vitaly1/max-bot-vitaly

   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

--------------------------------------------------------------------------------
2. Конфиг
--------------------------------------------------------------------------------
   cp .env.example .env
   nano .env

   Заполнить переменные с префиксом V2_:
   V2_OPENROUTER_API_KEY, V2_TELEGRAM_BOT_TOKEN, V2_TELEGRAM_CHANNEL_*,
   V2_MAX_BOT_TOKEN, V2_MAX_CHANNEL_*, V2_GOOGLE_SHEET_ID (если есть таблица).
   service_account.json положить в max-bot-vitaly/ при использовании Google Таблицы.

--------------------------------------------------------------------------------
3. Проверка
--------------------------------------------------------------------------------
   python bot.py
   (Ctrl+C для остановки)

--------------------------------------------------------------------------------
4. Systemd
--------------------------------------------------------------------------------
   sudo nano /etc/systemd/system/max-bot.service

   [Unit]
   Description=Content bot napitki133
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/vitaly1/max-bot-vitaly
   ExecStart=/root/vitaly1/max-bot-vitaly/venv/bin/python bot.py
   Restart=always
   RestartSec=10
   Environment=PATH=/root/vitaly1/max-bot-vitaly/venv/bin

   [Install]
   WantedBy=multi-user.target

   sudo systemctl daemon-reload
   sudo systemctl enable max-bot
   sudo systemctl start max-bot
   sudo journalctl -u max-bot -f

--------------------------------------------------------------------------------
ПОСЛЕ git pull
--------------------------------------------------------------------------------
   cd ~/vitaly1 && git pull origin main
   cd max-bot-vitaly && source venv/bin/activate && pip install -r requirements.txt
   sudo systemctl restart max-bot

================================================================================
