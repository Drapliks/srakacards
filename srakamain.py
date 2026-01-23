import os
import random
import logging
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ЗАМЕНИТЕ ЭТО НА ВАШ ТОКЕН!
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
CARDS_FOLDER = "cards"
DATA_FILE = "users_data.json"
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
COOLDOWN_MINUTES = 1  # Уменьшил до 1 минуты для тестирования, потом можно вернуть 30

class CardBot:
    def __init__(self):
        self.cards_list = []
        self.user_cards = {}
        self.user_cooldowns = {}
        self.user_vsrakost = {}
        self.user_names = {}
        self.card_points = {}
        self.application = None
        self.load_cards()
        self.load_user_data()
    
    def set_application(self, application: Application):
        """Устанавливает приложение для планирования задач"""
        self.application = application
    
    def load_cards(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cards_path = os.path.join(current_dir, CARDS_FOLDER)
            
            print(f"🔍 Ищем карты в папке: {cards_path}")
            
            if not os.path.exists(cards_path):
                os.makedirs(cards_path)
                print(f"✅ Создана папка: {cards_path}")
                print("📁 Добавьте картинки в эту папку и перезапустите бота")
                return
            
            self.cards_list = []
            files = os.listdir(cards_path)
            print(f"📁 Файлов в папке: {len(files)}")
            
            for filename in files:
                file_path = os.path.join(cards_path, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                if os.path.isfile(file_path) and file_ext in SUPPORTED_EXTENSIONS:
                    self.cards_list.append(filename)
                    print(f"   ✅ Добавлена карта: {filename}")
                else:
                    print(f"   ❌ Пропущен: {filename}")
            
            print(f"🎴 Итог: загружено {len(self.cards_list)} карт")
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке карт: {e}")
    
    def load_user_data(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"📊 Загружаем данные пользователей...")
                
                # Загружаем данные пользователей
                self.user_cards = {int(k): v for k, v in data.get('user_cards', {}).items()}
                self.user_vsrakost = {int(k): v for k, v in data.get('user_vsrakost', {}).items()}
                self.user_names = {int(k): v for k, v in data.get('user_names', {}).items()}
                self.card_points = data.get('card_points', {})
                
                # Загружаем кулдауны
                self.user_cooldowns = {}
                cooldowns_data = data.get('user_cooldowns', {})
                for user_id_str, cooldown_str in cooldowns_data.items():
                    if cooldown_str:
                        try:
                            self.user_cooldowns[int(user_id_str)] = datetime.fromisoformat(cooldown_str)
                        except:
                            pass
                
                # Если есть новые карты без очков, назначаем им очки
                new_cards = [card for card in self.cards_list if card not in self.card_points]
                if new_cards:
                    print(f"🎴 Назначаем очки для {len(new_cards)} новых карт...")
                    for card in new_cards:
                        self.card_points[card] = random.randint(1, 100)
                    self.save_user_data()
                
                print(f"✅ Загружены данные {len(self.user_cards)} пользователей")
                print(f"📊 Всего карт у пользователей: {sum(len(cards) for cards in self.user_cards.values())}")
                print(f"🎴 Всего карт с очками: {len(self.card_points)}")
                
            else:
                print("📁 Файл данных не найден, создаем новый...")
                self.user_cards = {}
                self.user_cooldowns = {}
                self.user_vsrakost = {}
                self.user_names = {}
                
                # Инициализируем очки для карт
                print("🎴 Инициализируем очки для всех карт...")
                for card in self.cards_list:
                    self.card_points[card] = random.randint(1, 100)
                print(f"✅ Инициализированы очки для {len(self.card_points)} карт")
                self.save_user_data()
                
        except Exception as e:
            print(f"❌ Ошибка при загрузке данных: {e}")
            # Создаем пустые структуры данных
            self.user_cards = {}
            self.user_cooldowns = {}
            self.user_vsrakost = {}
            self.user_names = {}
            self.card_points = {card: random.randint(1, 100) for card in self.cards_list}
            self.save_user_data()
    
    def save_user_data(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            # Подготавливаем данные для сохранения
            data = {
                'user_cards': {str(k): v for k, v in self.user_cards.items()},
                'user_cooldowns': {str(k): v.isoformat() if v else None for k, v in self.user_cooldowns.items()},
                'user_vsrakost': {str(k): v for k, v in self.user_vsrakost.items()},
                'user_names': {str(k): v for k, v in self.user_names.items()},
                'card_points': self.card_points
            }
            
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Данные сохранены")
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении данных: {e}")
    
    def get_random_card(self):
        if not self.cards_list:
            return None
        return random.choice(self.cards_list)
    
    def can_open_card(self, user_id):
        if user_id not in self.user_cooldowns:
            return True, None
        
        last_open_time = self.user_cooldowns[user_id]
        cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
        now = datetime.now()
        
        if now < cooldown_end:
            time_left = cooldown_end - now
            minutes_left = int(time_left.total_seconds() // 60)
            seconds_left = int(time_left.total_seconds() % 60)
            return False, (minutes_left, seconds_left)
        
        return True, None
    
    def set_cooldown(self, user_id):
        """Устанавливает кулдаун и планирует уведомление"""
        self.user_cooldowns[user_id] = datetime.now()
        self.save_user_data()
        
        # Планируем уведомление
        self.schedule_notification(user_id)
    
    def schedule_notification(self, user_id: int):
        """Планирует уведомление о завершении кулдауна"""
        if not self.application:
            print(f"⚠️ Application не установлен для пользователя {user_id}")
            return
        
        job_queue = self.application.job_queue
        if not job_queue:
            print(f"⚠️ JobQueue не доступен для пользователя {user_id}")
            return
        
        # Вычисляем время уведомления
        if user_id not in self.user_cooldowns:
            return
        
        last_open_time = self.user_cooldowns[user_id]
        cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
        delay_seconds = (cooldown_end - datetime.now()).total_seconds()
        
        if delay_seconds <= 0:
            return
        
        print(f"⏰ Планирую уведомление для {user_id} через {delay_seconds:.0f} секунд")
        
        # Создаем задачу на уведомление
        job_queue.run_once(
            callback=self.send_notification_callback,
            when=delay_seconds,
            data={'user_id': user_id},
            name=f"notify_{user_id}"
        )
    
    async def send_notification_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Callback для отправки уведомления"""
        user_id = context.job.data['user_id']
        await self.send_notification(user_id)
    
    async def send_notification(self, user_id: int):
        """Отправляет уведомление пользователю"""
        try:
            # Получаем имя пользователя
            user_name = self.get_user_display_name(user_id)
            
            # Отправляем сообщение
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"🎉 {user_name}, таймер окончен!\n\n"
                     "Теперь ты можешь открыть следующую SRAKY!\n"
                     "Используй команду /drop чтобы получить новую карту! 🎴"
            )
            print(f"✅ Уведомление отправлено пользователю {user_id} ({user_name})")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке уведомления: {e}")
    
    def restore_notifications(self):
        """Восстанавливает уведомления при перезапуске бота"""
        if not self.application:
            return
        
        print("🔄 Восстанавливаю уведомления...")
        now = datetime.now()
        
        for user_id, last_open_time in self.user_cooldowns.items():
            cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
            
            # Если таймер еще не истек
            if now < cooldown_end:
                self.schedule_notification(user_id)
    
    def add_card_to_user(self, user_id, card_name):
        if user_id not in self.user_cards:
            self.user_cards[user_id] = []
        
        self.user_cards[user_id].append(card_name)
        
        # Начисляем очки
        card_points = self.card_points.get(card_name, 0)
        if user_id not in self.user_vsrakost:
            self.user_vsrakost[user_id] = 0
        self.user_vsrakost[user_id] += card_points
        
        print(f"🎴 Добавлена карта {card_name} пользователю {user_id} ({card_points} очков)")
        
        self.save_user_data()
        return card_points
    
    def update_user_name(self, user_id, first_name, last_name=None):
        full_name = first_name
        if last_name:
            full_name = f"{first_name} {last_name}"
        
        self.user_names[user_id] = full_name
        return full_name
    
    def get_user_display_name(self, user_id, update: Update = None):
        if user_id in self.user_names:
            return self.user_names[user_id]
        
        if update and update.effective_user:
            user = update.effective_user
            full_name = self.update_user_name(user_id, user.first_name, user.last_name)
            self.save_user_data()
            return full_name
        
        return f"Игрок_{user_id}"
    
    def get_user_vsrakost_rank(self, user_id):
        if user_id not in self.user_vsrakost:
            return None
        
        sorted_users = sorted(self.user_vsrakost.items(), key=lambda x: x[1], reverse=True)
        for rank, (uid, points) in enumerate(sorted_users, 1):
            if uid == user_id:
                return rank
        return None
    
    def get_top_users(self, limit=10):
        sorted_users = sorted(self.user_vsrakost.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    def get_user_cards_count(self, user_id):
        return len(self.user_cards.get(user_id, []))
    
    def get_total_cards_count(self):
        return len(self.cards_list)

# Глобальный экземпляр бота
card_bot = CardBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    
    can_open, time_left = card_bot.can_open_card(user_id)
    
    welcome_text = (
        f"🎴 Привет, {user_name}!\n"
        f"📊 Карт в коллекции: {card_bot.get_user_cards_count(user_id)}\n"
        f"⭐ Очков VSRAKOSTI: {card_bot.user_vsrakost.get(user_id, 0)}\n"
        f"🎯 Всего карт в игре: {card_bot.get_total_cards_count()}\n\n"
    )
    
    if not can_open:
        mins, secs = time_left
        welcome_text += f"⏳ Следующую карту можно открыть через: {mins} мин {secs} сек\n"
        welcome_text += f"🔔 Я пришлю уведомление, когда таймер истечёт!\n\n"
    else:
        welcome_text += "✅ Можешь открыть карту прямо сейчас!\n\n"
    
    welcome_text += "📋 Команды:\n"
    welcome_text += "/drop - Получить карту 🎴\n"
    welcome_text += "/list - Моя коллекция 📚\n"
    welcome_text += "/top - Топ игроков 🏆\n"
    welcome_text += "/help - Помощь ❓\n\n"
    welcome_text += f"⏰ Таймер: {COOLDOWN_MINUTES} минут"
    
    await update.message.reply_text(welcome_text)

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    
    # Проверяем кулдаун
    can_open, time_left = card_bot.can_open_card(user_id)
    if not can_open:
        mins, secs = time_left
        await update.message.reply_text(
            f"⏳ {user_name}, подожди еще:\n"
            f"🕐 {mins} минут {secs} секунд\n\n"
            f"Я пришлю уведомление, когда можно будет открыть следующую карту! 🔔"
        )
        return
    
    # Получаем случайную карту
    card = card_bot.get_random_card()
    if not card:
        await update.message.reply_text(
            "❌ Карты не найдены!\n"
            "Добавьте картинки в папку 'cards' и перезапустите бота"
        )
        return
    
    # Получаем путь к картинке
    current_dir = os.path.dirname(os.path.abspath(__file__))
    card_path = os.path.join(current_dir, CARDS_FOLDER, card)
    
    try:
        # Проверяем существование файла
        if not os.path.exists(card_path):
            await update.message.reply_text("❌ Файл карты не найден")
            return
        
        # Получаем очки карты
        card_points = card_bot.card_points.get(card, 0)
        
        # Отправляем карту
        with open(card_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎴 Новая SRAKA!\n"
                       f"💎 Очков: {card_points}\n"
                       f"⏰ Следующая через {COOLDOWN_MINUTES} мин\n"
                       f"🔔 Уведомлю, когда можно будет открыть следующую!"
            )
        
        # Устанавливаем кулдаун и добавляем карту
        card_bot.set_cooldown(user_id)
        earned_points = card_bot.add_card_to_user(user_id, card)
        
        print(f"✅ Карта {card} отправлена {user_name} ({earned_points} очков)")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при отправке карты")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    
    user_cards_count = card_bot.get_user_cards_count(user_id)
    user_points = card_bot.user_vsrakost.get(user_id, 0)
    user_rank = card_bot.get_user_vsrakost_rank(user_id)
    
    can_open, time_left = card_bot.can_open_card(user_id)
    
    message = f"📚 Коллекция {user_name}:\n\n"
    message += f"📊 Карт: {user_cards_count}\n"
    message += f"⭐ Очков: {user_points}\n"
    
    if user_rank:
        message += f"🏆 Ранг: {user_rank}\n\n"
    else:
        message += f"🏆 Ранг: -\n\n"
    
    if not can_open:
        mins, secs = time_left
        message += f"⏳ До следующей карты: {mins} мин {secs} сек\n"
        message += "🔔 Уведомление придет автоматически!"
    else:
        message += "✅ Можешь открыть карту! /drop"
    
    await update.message.reply_text(message)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = card_bot.get_top_users(10)
    
    if not top_users:
        await update.message.reply_text("😴 Пока никто не открыл карты...")
        return
    
    message = "🏆 ТОП ИГРОКОВ 🏆\n\n"
    
    for i, (user_id, points) in enumerate(top_users, 1):
        # Получаем имя пользователя
        if user_id in card_bot.user_names:
            name = card_bot.user_names[user_id]
        else:
            name = f"Игрок_{user_id}"
        
        # Эмодзи для первых трех мест
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        message += f"{medal} {name}\n"
        message += f"   ⭐ {points} очков | 🎴 {card_bot.get_user_cards_count(user_id)} карт\n\n"
    
    message += "💡 Используй /drop чтобы получить карты!"
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 ПОМОЩЬ ПО БОТУ\n\n"
        "🎴 SRAKY Collector - бот для коллекционирования карт\n\n"
        "📋 КОМАНДЫ:\n"
        "/start - Начать работу\n"
        "/drop - Получить карту (раз в 30 мин)\n"
        "/list - Посмотреть свою коллекцию\n"
        "/top - Топ игроков по очкам\n"
        "/help - Эта справка\n\n"
        "📊 СИСТЕМА ОЧКОВ:\n"
        "• Каждая карта дает случайное количество очков (1-100)\n"
        "• Очки суммируются в рейтинге VSRAKOSTI\n"
        "• Чем больше карт и чем выше их очки - тем выше в топе!\n\n"
        "⏰ ТАЙМЕР:\n"
        f"• Между открытиями карт: {COOLDOWN_MINUTES} минут\n"
        "• Бот пришлет уведомление, когда можно открыть следующую карту!\n\n"
        "🔔 УВЕДОМЛЕНИЯ:\n"
        "• Работают даже после перезапуска бота\n"
        "• Приходят в личные сообщения"
    )
    
    await update.message.reply_text(help_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(card_bot.user_cards)
    total_cards = sum(len(cards) for cards in card_bot.user_cards.values())
    total_points = sum(card_bot.user_vsrakost.values())
    
    message = (
        "📊 СТАТИСТИКА БОТА\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🎴 Всего карт: {total_cards}\n"
        f"⭐ Всего очков: {total_points}\n"
        f"📁 Карт доступно: {card_bot.get_total_cards_count()}\n"
    )
    
    await update.message.reply_text(message)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"⚠️ Ошибка: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз или свяжитесь с администратором."
            )
    except:
        pass

def main():
    print("=" * 50)
    print("🤖 SRAKY Collector Bot")
    print("=" * 50)
    
    # Проверка токена
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Замените BOT_TOKEN на ваш настоящий токен!")
        print("📝 Как получить токен:")
        print("1. Найдите @BotFather в Telegram")
        print("2. Создайте нового бота командой /newbot")
        print("3. Скопируйте токен и вставьте в код")
        return
    
    # Проверка карт
    if card_bot.get_total_cards_count() == 0:
        print("⚠️ ВНИМАНИЕ: Карты не найдены!")
        print("📁 Создайте папку 'cards' и добавьте картинки:")
        print("   • PNG, JPG, JPEG, GIF, WEBP, BMP")
        print("   • Имена файлов должны быть на английском")
    else:
        print(f"✅ Карт загружено: {card_bot.get_total_cards_count()}")
        print(f"⏰ Таймер: {COOLDOWN_MINUTES} минут")
        print(f"⭐ Система очков: включена")
        print(f"🔔 Уведомления: включены")
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Устанавливаем приложение в бота
        card_bot.set_application(application)
        
        # Восстанавливаем уведомления
        card_bot.restore_notifications()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("drop", drop_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("top", top_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        print("\n🚀 Бот запускается...")
        print("💬 Напишите /start в Telegram")
        print("📡 Ожидание сообщений...")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ ФАТАЛЬНАЯ ОШИБКА: {e}")
        print("\n🔧 Возможные решения:")
        print("1. Проверьте токен бота")
        print("2. Проверьте интернет-соединение")
        print("3. Убедитесь, что python-telegram-bot установлен:")
        print("   pip install python-telegram-bot")
        print("4. Убедитесь, что у бота есть права на отправку сообщений")

if __name__ == '__main__':
    main()
