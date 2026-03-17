================================================================================
  ЧТО ДЕЛАТЬ НА СЕРВЕРЕ ПОСЛЕ git pull
================================================================================

   cd ~/vitaly1
   git pull origin main

   cd max-bot-vitaly
   source venv/bin/activate
   pip install -r requirements.txt

   sudo systemctl restart max-bot
   sudo systemctl status max-bot
   sudo journalctl -u max-bot -f

Бот один (bot.py): контент-машина для napitki133.ru. Переменные в .env с префиксом V2_.

================================================================================
