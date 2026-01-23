import os
import random
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "TOKEN"
CARDS_FOLDER = "cards"
DATA_FILE = "users_data.json"
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
COOLDOWN_MINUTES = 30

class CardBot:
    def __init__(self):
        self.cards_list = []
        self.user_cards = {}
        self.user_cooldowns = {}
        self.user_notifications = {}
        self.user_vsrakost = {}
        self.user_names = {}
        self.card_points = {}
        self.application = None
        self.load_cards()
        self.load_user_data()
    
    def set_application(self, application: Application):
        """Устанавливает приложение для планирования задач"""
        self.application = application
        print("✅ Application установлен в CardBot")
    
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
            logger.error(f"Ошибка при загрузке карт: {e}")
    
    def load_user_data(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"📊 Загружаем данные пользователей...")
                
                user_cards_data = data.get('user_cards', {})
                self.user_cards = {}
                for user_id_str, cards_list in user_cards_data.items():
                    user_id = int(user_id_str)
                    self.user_cards[user_id] = cards_list
                
                cooldowns_data = data.get('user_cooldowns', {})
                self.user_cooldowns = {}
                for user_id_str, cooldown_str in cooldowns_data.items():
                    user_id = int(user_id_str)
                    if cooldown_str:
                        self.user_cooldowns[user_id] = datetime.fromisoformat(cooldown_str)
                
                vsrakost_data = data.get('user_vsrakost', {})
                self.user_vsrakost = {}
                for user_id_str, vsrakost_points in vsrakost_data.items():
                    user_id = int(user_id_str)
                    self.user_vsrakost[user_id] = vsrakost_points
                    print(f"   ⭐ Пользователь {user_id}: {vsrakost_points} очков VSRAKOSTI")
                
                names_data = data.get('user_names', {})
                self.user_names = {}
                for user_id_str, name in names_data.items():
                    user_id = int(user_id_str)
                    self.user_names[user_id] = name
                
                card_points_data = data.get('card_points', {})
                if card_points_data:
                    self.card_points = card_points_data
                    print(f"   🎴 Загружены очки для {len(self.card_points)} карт")
                else:
                    print("   🎴 Инициализируем очки для карт...")
                    for card in self.cards_list:
                        if card not in self.card_points:
                            self.card_points[card] = random.randint(1, 100)
                    print(f"   ✅ Инициализированы очки для {len(self.card_points)} карт")
                    self.save_user_data()
                
                cards_without_points = [card for card in self.cards_list if card not in self.card_points]
                if cards_without_points:
                    print(f"   🎴 Назначаем очки для {len(cards_without_points)} новых карт...")
                    for card in cards_without_points:
                        self.card_points[card] = random.randint(1, 100)
                    self.save_user_data()
                
                print(f"✅ Загружены данные {len(self.user_cards)} пользователей")
                print(f"📊 Всего карт у пользователей: {sum(len(cards) for cards in self.user_cards.values())}")
                print(f"🎴 Всего карт с очками: {len(self.card_points)}")
                
            else:
                print("✅ Файл данных не найден, создадим новый при сохранении")
                self.user_cards = {}
                self.user_cooldowns = {}
                self.user_vsrakost = {}
                self.user_names = {}
                print("🎴 Инициализируем очки для всех карт...")
                for card in self.cards_list:
                    self.card_points[card] = random.randint(1, 100)
                print(f"✅ Инициализированы очки для {len(self.card_points)} карт")
                self.save_user_data()
                
        except Exception as e:
            print(f"❌ Ошибка при загрузке данных пользователей: {e}")
            self.user_cards = {}
            self.user_cooldowns = {}
            self.user_vsrakost = {}
            self.user_names = {}
            for card in self.cards_list:
                self.card_points[card] = random.randint(1, 100)
            self.save_user_data()
    
    def save_user_data(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            user_cards_data = {}
            for user_id, cards_list in self.user_cards.items():
                user_cards_data[str(user_id)] = cards_list
            
            cooldowns_data = {}
            for user_id, cooldown_time in self.user_cooldowns.items():
                cooldowns_data[str(user_id)] = cooldown_time.isoformat() if cooldown_time else None
            
            vsrakost_data = {}
            for user_id, vsrakost_points in self.user_vsrakost.items():
                vsrakost_data[str(user_id)] = vsrakost_points
            
            names_data = {}
            for user_id, name in self.user_names.items():
                names_data[str(user_id)] = name
            
            card_points_data = self.card_points.copy()
            
            data = {
                'user_cards': user_cards_data,
                'user_cooldowns': cooldowns_data,
                'user_vsrakost': vsrakost_data,
                'user_names': names_data,
                'card_points': card_points_data
            }
            
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            total_cards = sum(len(cards) for cards in self.user_cards.values())
            total_points = sum(self.user_vsrakost.values())
            print(f"💾 Данные сохранены: {len(self.user_cards)} пользователей, {total_cards} карт, {total_points} очков")
            print(f"🎴 Сохранены очки для {len(self.card_points)} карт")
            
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
    
    def set_cooldown(self, user_id, application: Application = None):
        """Устанавливает кулдаун и планирует уведомление"""
        self.user_cooldowns[user_id] = datetime.now()
        self.save_user_data()
        
        app_to_use = application or self.application
        if app_to_use:
            self.schedule_notification(user_id, app_to_use)
        else:
            print(f"⚠️ Нет application для планирования уведомления пользователю {user_id}")
    
    def schedule_notification(self, user_id: int, application: Application):
        """Планирует уведомление о завершении кулдауна"""
        if user_id in self.user_notifications:
            try:
                self.user_notifications[user_id].schedule_removal()
                del self.user_notifications[user_id]
            except Exception as e:
                print(f"⚠️ Ошибка при отмене предыдущего уведомления: {e}")
        
        job_queue = application.job_queue
        if job_queue:
            cooldown_end = self.user_cooldowns[user_id] + timedelta(minutes=COOLDOWN_MINUTES)
            now = datetime.now()
            delay = (cooldown_end - now).total_seconds()
            
            if delay > 0:
                print(f"⏰ Планирую уведомление для {user_id} через {delay:.0f} секунд")
                job = job_queue.run_once(
                    callback=lambda context: self.send_notification(context, user_id),
                    when=delay,
                    name=f"cooldown_notification_{user_id}",
                    chat_id=user_id,
                    user_id=user_id
                )
                self.user_notifications[user_id] = job
                print(f"✅ Уведомление запланировано для пользователя {user_id}")
    
    async def send_notification(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Отправляет уведомление о возможности открыть карту"""
        try:
            if user_id in self.user_notifications:
                del self.user_notifications[user_id]
            
            user_name = self.get_user_display_name(user_id)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 {user_name}, таймер окончен!\n\n"
                     "Теперь ты можешь открыть следующую SRAKY!\n"
                     "Используй команду /drop чтобы получить новую карту! 🎴"
            )
            print(f"✅ Уведомление отправлено пользователю {user_id} ({user_name})")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке уведомления пользователю {user_id}: {e}")
    
    def restore_notifications(self, application: Application):
        """Восстанавливает уведомления при перезапуске бота"""
        print("🔄 Восстанавливаю уведомления о таймерах...")
        now = datetime.now()
        restored_count = 0
        
        for user_id, last_open_time in self.user_cooldowns.items():
            cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
            
            if now < cooldown_end:
                delay = (cooldown_end - now).total_seconds()
                if delay > 0:
                    self.schedule_notification(user_id, application)
                    restored_count += 1
                    print(f"   ✅ Восстановлено уведомление для {user_id} через {delay:.0f} сек")
            else:
                print(f"   ⏰ Таймер пользователя {user_id} уже истек")
        
        print(f"🔄 Восстановлено {restored_count} уведомлений")
    
    def add_card_to_user(self, user_id, card_name):
        if user_id not in self.user_cards:
            self.user_cards[user_id] = []
        
        self.user_cards[user_id].append(card_name)
        
        card_points = self.card_points.get(card_name, 0)
        if user_id not in self.user_vsrakost:
            self.user_vsrakost[user_id] = 0
        
        old_points = self.user_vsrakost[user_id]
        self.user_vsrakost[user_id] += card_points
        new_points = self.user_vsrakost[user_id]
        
        print(f"🎴 Добавлена карта {card_name} пользователю {user_id}")
        print(f"⭐ Начислено {card_points} очков VSRAKOSTI за карту {card_name}")
        print(f"📊 У пользователя {user_id}: было {old_points} очков, стало {new_points} очков")
        print(f"📦 Всего карт у пользователя {user_id}: {len(self.user_cards[user_id])}")
        
        self.save_user_data()
        return card_points
    
    def update_user_name(self, user_id, first_name, last_name=None):
        full_name = first_name
        if last_name:
            full_name = f"{first_name} {last_name}"
        
        if user_id not in self.user_names or self.user_names[user_id] != full_name:
            self.user_names[user_id] = full_name
            print(f"📝 Обновлено имя пользователя {user_id}: '{full_name}'")
            self.save_user_data()
        
        return full_name
    
    def get_user_display_name(self, user_id, update: Update = None):
        if user_id in self.user_names:
            return self.user_names[user_id]
        
        if update and update.effective_user:
            user = update.effective_user
            full_name = self.update_user_name(user_id, user.first_name, user.last_name)
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
        if user_id not in self.user_cards:
            return 0
        return len(self.user_cards[user_id])
    
    def get_user_cards_list(self, user_id):
        if user_id not in self.user_cards:
            return []
        return self.user_cards[user_id]
    
    def get_total_cards_count(self):
        return len(self.cards_list)
    
    def get_cooldown_time(self, user_id):
        if user_id not in self.user_cooldowns:
            return None
        
        last_open_time = self.user_cooldowns[user_id]
        cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
        now = datetime.now()
        
        if now >= cooldown_end:
            return None
        
        time_left = cooldown_end - now
        return time_left

card_bot = CardBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    total_cards = card_bot.get_total_cards_count()
    user_cards_count = card_bot.get_user_cards_count(user_id)
    user_points = card_bot.user_vsrakost.get(user_id, 0)
    
    can_open, time_left = card_bot.can_open_card(user_id)
    
    welcome_text = (
        f"🎴 Добро пожаловать, {user_name}!\n"
        f"📊 Карт в коллекции: {user_cards_count}\n"
        f"⭐ Очков VSRAKOSTI: {user_points}\n"
        f"🎯 Всего карт в игре: {total_cards}\n\n"
    )
    
    if not can_open:
        mins, secs = time_left
        welcome_text += f"⏳ Следующую карту можно открыть через: {mins} мин {secs} сек\n"
        welcome_text += f"🔔 Я отправлю тебе уведомление, когда таймер истечёт!\n\n"
    else:
        welcome_text += "✅ Можешь открыть карту прямо сейчас!\n\n"
    
    welcome_text += "📋 Доступные команды:\n"
    welcome_text += "/drop - Получить карту 🎴\n"
    welcome_text += "/list - Моя коллекция 📚\n"
    welcome_text += "/top - Топ игроков 🏆\n\n"
    welcome_text += f"⏰ Таймер между открытиями: {COOLDOWN_MINUTES} минут"
    
    await update.message.reply_text(welcome_text)

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    
    can_open, time_left = card_bot.can_open_card(user_id)
    if not can_open:
        mins, secs = time_left
        await update.message.reply_text(
            f"⏳ {user_name}, следующую карту можно открыть через:\n"
            f"🕐 {mins} минут {secs} секунд\n\n"
            f"💡 Таймер: {COOLDOWN_MINUTES} минут между открытиями\n"
            f"🔔 Я отправлю тебе уведомление, когда таймер истечёт!"
        )
        return
    
    card = card_bot.get_random_card()
    
    if not card:
        await update.message.reply_text(
            "❌ Карты не найдены!\n"
            "Добавьте картинки в папку cards и перезапустите бота"
        )
        return
    
    card_points = card_bot.card_points.get(card, 0)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    card_path = os.path.join(current_dir, CARDS_FOLDER, card)
    
    print(f"🔄 Пытаюсь отправить карту: {card} пользователю {user_id} ({user_name})")
    print(f"🎯 Карта дает {card_points} очков")
    
    try:
        if not os.path.exists(card_path):
            await update.message.reply_text(f"❌ Файл карты не найден: {card}")
            print(f"❌ Файл не существует: {card_path}")
            return
        
        with open(card_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎴 Новая SRAKA!\n💎 Даёт очков: {card_points}\n⏰ Следующая карта через {COOLDOWN_MINUTES} минут\n\n"
                       f"🔔 Я отправлю тебе уведомление, когда можно будет открыть следующую карту!"
            )
        
        card_bot.set_cooldown(user_id, context.application)
        earned_points = card_bot.add_card_to_user(user_id, card)
        
        user_total_points = card_bot.user_vsrakost.get(user_id, 0)
        user_rank = card_bot.get_user_vsrakost_rank(user_id)
        
        print(f"✅ Успешно отправлена карта: {card} пользователю {user_id}, начислено {earned_points} очков")
        
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке карты {card}: {e}"
        print(error_msg)
        await update.message.reply_text("❌ Ошибка при отправке карты")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    user_cards_count = card_bot.get_user_cards_count(user_id)
    total_cards_count = card_bot.get_total_cards_count()
    user_points = card_bot.user_vsrakost.get(user_id, 0)
    user_rank = card_bot.get_user_vsrakost_rank(user_id)
    
    cooldown_time = card_bot.get_cooldown_time(user_id)
    
    message = f"🎴 Коллекция {user_name}:\n\n"
    message += f"📊 Карт в коллекции: {user_cards_count}\n"
    message += f"⭐ Очков VSRAKOSTI: {user_points}\n"
    
    if user_rank:
        message += f"🏆 Позиция в рейтинге: {user_rank}\n\n"
    else:
        message += f"🏆 Ты еще не в рейтинге\n\n"
    
    if cooldown_time:
        mins = int(cooldown_time.total_seconds() // 60)
        secs = int(cooldown_time.total_seconds() % 60)
        message += f"⏳ До следующей карты: {mins} мин {secs} сек\n"
        message += f"🔔 Уведомление придёт автоматически!\n"
    else:
        message += "✅ Можешь открыть следующую карту! Используй /drop"
    
    await update.message.reply_text(message)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = card_bot.get_top_users(limit=10)
    
    message = "🏆 ТОП-10 ИГРОКОВ ПО VSRAKOSTI 🏆\n\n"
    
    if top_users:
        for i, (user_id, points) in enumerate(top_users, 1):
            if user_id in card_bot.user_names:
                display_name = card_bot.user_names[user_id]
            else:
                display_name = f"Игрок_{user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            cards_count = card_bot.get_user_cards_count(user_id)
            message += f"{medal} {display_name}\n"
            message += f"   ⭐ Очки: {points} | 🎴 Карты: {cards_count}\n\n"
    else:
        message += "😴 Пока никто не заработал очков...\n"
        message += "Используй /drop чтобы получить первую карту! 🎴"
    
    message += "\n💡 Используй /drop чтобы получить карты и подняться в рейтинге!"
    
    await update.message.reply_text(message)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику бота"""
    total_users = len(card_bot.user_cards)
    total_cards_in_collections = sum(len(cards) for cards in card_bot.user_cards.values())
    total_points = sum(card_bot.user_vsrakost.values())
    total_available_cards = card_bot.get_total_cards_count()
    
    message = "📊 СТАТИСТИКА БОТА 📊\n\n"
    message += f"👥 Всего пользователей: {total_users}\n"
    message += f"🎴 Всего карт у пользователей: {total_cards_in_collections}\n"
    message += f"⭐ Всего очков VSRAKOSTI: {total_points}\n"
    message += f"📁 Доступных карт: {total_available_cards}\n"
    
    if total_available_cards > 0:
        avg_points_per_card = sum(card_bot.card_points.values()) / total_available_cards
        max_points = max(card_bot.card_points.values())
        min_points = min(card_bot.card_points.values())
        
        message += f"\n🎯 Статистика очков карт:\n"
        message += f"   Среднее: {avg_points_per_card:.1f}\n"
        message += f"   Максимальное: {max_points}\n"
        message += f"   Минимальное: {min_points}\n"
    
    await update.message.reply_text(message)

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Замените BOT_TOKEN на ваш настоящий токен бота!")
        print("💡 Как получить токен:")
        print("   1. Напишите @BotFather в Telegram")
        print("   2. Создайте нового бота или выберите существующего")
        print("   3. Скопируйте токен и вставьте вместо 'YOUR_BOT_TOKEN_HERE'")
        return
    
    total_cards = card_bot.get_total_cards_count()
    if total_cards == 0:
        print("❌ ВНИМАНИЕ: Карты не найдены!")
        print("💡 Решение:")
        print("   1. Создайте папку 'cards' рядом с файлом бота")
        print("   2. Добавьте в нее картинки (PNG, JPG, JPEG, GIF, WEBP, BMP)")
        print("   3. Перезапустите бота")
    else:
        print(f"✅ Готов к работе! Загружено карт: {total_cards}")
        print(f"⏰ Таймер между открытиями: {COOLDOWN_MINUTES} минут")
        print(f"⭐ Система очков VSRAKOSTI: ВКЛЮЧЕНА")
        print(f"👤 Автоматические имена из Telegram: ВКЛЮЧЕНО")
        print(f"💾 Сохранение очков карт: ВКЛЮЧЕНО")
        print(f"🔔 Система уведомлений: ВКЛЮЧЕНА")
        
        print(f"\n🎴 Примеры карт с очками:")
        sample_cards = list(card_bot.card_points.items())[:5]
        for i, (card, points) in enumerate(sample_cards, 1):
            print(f"   {i}. {card} - {points} очков")
        
        total_card_points = sum(card_bot.card_points.values())
        avg_points = total_card_points / len(card_bot.card_points) if card_bot.card_points else 0
        print(f"\n📊 Статистика очков:")
        print(f"   Всего очков у всех карт: {total_card_points}")
        print(f"   Среднее очков на карту: {avg_points:.1f}")
        print(f"   Максимальное очков: {max(card_bot.card_points.values()) if card_bot.card_points else 0}")
        print(f"   Минимальное очков: {min(card_bot.card_points.values()) if card_bot.card_points else 0}")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        card_bot.set_application(application)
        
        card_bot.restore_notifications(application)
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("drop", drop_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("top", top_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        print("\n🤖 Бот запускается...")
        print("💬 Используйте /start в Telegram для начала работы")
        print("🔔 Система уведомлений активирована и восстановлена")
        print("🔄 Бот работает в режиме polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
