import os
import random
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8012455423:AAEM4hF8P27QOUrwJUhBarnHeQfmKdZCeXA"
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
        self.user_names = {}  # Храним имена пользователей из Telegram
        self.card_points = {}
        self.load_cards()
        self.load_user_data()
    
    def load_cards(self):
        """Загрузка списка карт из папки"""
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
        """Загрузка данных пользователей из файла"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"📊 Загружаем данные пользователей...")
                
                # Восстанавливаем коллекции карт пользователей
                user_cards_data = data.get('user_cards', {})
                self.user_cards = {}
                for user_id_str, cards_list in user_cards_data.items():
                    user_id = int(user_id_str)
                    self.user_cards[user_id] = cards_list
                
                # Восстанавливаем кулдауны
                cooldowns_data = data.get('user_cooldowns', {})
                self.user_cooldowns = {}
                for user_id_str, cooldown_str in cooldowns_data.items():
                    user_id = int(user_id_str)
                    if cooldown_str:
                        self.user_cooldowns[user_id] = datetime.fromisoformat(cooldown_str)
                
                # Восстанавливаем рейтинг VSRAKOSTI пользователей
                vsrakost_data = data.get('user_vsrakost', {})
                self.user_vsrakost = {}
                for user_id_str, vsrakost_points in vsrakost_data.items():
                    user_id = int(user_id_str)
                    self.user_vsrakost[user_id] = vsrakost_points
                    print(f"   ⭐ Пользователь {user_id}: {vsrakost_points} очков VSRAKOSTI")
                
                # Восстанавливаем имена пользователей (если есть)
                names_data = data.get('user_names', {})
                self.user_names = {}
                for user_id_str, name in names_data.items():
                    user_id = int(user_id_str)
                    self.user_names[user_id] = name
                
                # Восстанавливаем очки карт
                card_points_data = data.get('card_points', {})
                if card_points_data:
                    self.card_points = card_points_data
                    print(f"   🎴 Загружены очки для {len(self.card_points)} карт")
                else:
                    # Если очки карт не загружены, инициализируем их случайными значениями
                    print("   🎴 Инициализируем очки для карт...")
                    for card in self.cards_list:
                        if card not in self.card_points:
                            self.card_points[card] = random.randint(1, 100)
                    print(f"   ✅ Инициализированы очки для {len(self.card_points)} карт")
                    # Сохраняем сразу после инициализации
                    self.save_user_data()
                
                # Проверяем, что у всех карт есть очки
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
                # Инициализируем очки для всех карт
                print("🎴 Инициализируем очки для всех карт...")
                for card in self.cards_list:
                    self.card_points[card] = random.randint(1, 100)
                print(f"✅ Инициализированы очки для {len(self.card_points)} карт")
                # Сохраняем данные сразу
                self.save_user_data()
                
        except Exception as e:
            print(f"❌ Ошибка при загрузке данных пользователей: {e}")
            self.user_cards = {}
            self.user_cooldowns = {}
            self.user_vsrakost = {}
            self.user_names = {}
            # Инициализируем очки для всех карт даже при ошибке
            for card in self.cards_list:
                self.card_points[card] = random.randint(1, 100)
            self.save_user_data()
    
    def save_user_data(self):
        """Сохранение данных пользователей в файл ВКЛЮЧАЯ ОЧКИ КАРТ"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DATA_FILE)
            
            # Конвертируем данные для JSON
            user_cards_data = {}
            for user_id, cards_list in self.user_cards.items():
                user_cards_data[str(user_id)] = cards_list
            
            cooldowns_data = {}
            for user_id, cooldown_time in self.user_cooldowns.items():
                cooldowns_data[str(user_id)] = cooldown_time.isoformat() if cooldown_time else None
            
            vsrakost_data = {}
            for user_id, vsrakost_points in self.user_vsrakost.items():
                vsrakost_data[str(user_id)] = vsrakost_points
            
            # Сохраняем имена пользователей
            names_data = {}
            for user_id, name in self.user_names.items():
                names_data[str(user_id)] = name
            
            # Сохраняем очки карт
            card_points_data = self.card_points.copy()
            
            data = {
                'user_cards': user_cards_data,
                'user_cooldowns': cooldowns_data,
                'user_vsrakost': vsrakost_data,
                'user_names': names_data,  # Сохраняем имена
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
        """Получение случайной карты"""
        if not self.cards_list:
            return None
        return random.choice(self.cards_list)
    
    def can_open_card(self, user_id):
        """Проверяет, может ли пользователь открыть карту"""
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
        """Устанавливает время кулдауна для пользователя"""
        self.user_cooldowns[user_id] = datetime.now()
        self.save_user_data()
        
        # Запускаем задачу для уведомления о завершении таймера
        if application:
            self.schedule_notification(user_id, application)
    
    def schedule_notification(self, user_id: int, application: Application):
        """Планирует уведомление о завершении таймера"""
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
                job = job_queue.run_once(
                    callback=lambda context: self.send_notification(context, user_id),
                    when=delay,
                    name=f"cooldown_notification_{user_id}"
                )
                self.user_notifications[user_id] = job
    
    async def send_notification(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Отправляет уведомление пользователю о том, что можно открыть карту"""
        try:
            if user_id in self.user_notifications:
                del self.user_notifications[user_id]
            
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Таймер окончен! Теперь ты можешь открыть следующую карту!\n\n"
                     "Используй команду /drop чтобы получить новую SRAKY!"
            )
            print(f"✅ Уведомление отправлено пользователю {user_id}")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке уведомления пользователю {user_id}: {e}")
    
    def add_card_to_user(self, user_id, card_name):
        """Добавление карты пользователю с начислением очков"""
        # Инициализируем список карт для пользователя, если его нет
        if user_id not in self.user_cards:
            self.user_cards[user_id] = []
        
        # Добавляем карту
        self.user_cards[user_id].append(card_name)
        
        # Начисляем очки VSRAKOSTI пользователю за получение карты
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
        
        # Сохраняем данные (включая очки карт)
        self.save_user_data()
        return card_points
    
    def update_user_name(self, user_id, first_name, last_name=None):
        """Обновление имени пользователя из Telegram"""
        # Формируем полное имя
        full_name = first_name
        if last_name:
            full_name = f"{first_name} {last_name}"
        
        # Сохраняем имя только если оно изменилось или отсутствует
        if user_id not in self.user_names or self.user_names[user_id] != full_name:
            self.user_names[user_id] = full_name
            print(f"📝 Обновлено имя пользователя {user_id}: '{full_name}'")
            self.save_user_data()
        
        return full_name
    
    def get_user_display_name(self, user_id, update: Update = None):
        """Получение отображаемого имени пользователя"""
        # Если есть сохраненное имя - используем его
        if user_id in self.user_names:
            return self.user_names[user_id]
        
        # Если передан update, пытаемся получить имя из Telegram
        if update and update.effective_user:
            user = update.effective_user
            full_name = self.update_user_name(user_id, user.first_name, user.last_name)
            return full_name
        
        # Если ничего нет - используем ID
        return f"Игрок_{user_id}"
    
    def get_user_vsrakost_rank(self, user_id):
        """Получение позиции пользователя в рейтинге"""
        if user_id not in self.user_vsrakost:
            return None
        
        sorted_users = sorted(self.user_vsrakost.items(), key=lambda x: x[1], reverse=True)
        for rank, (uid, points) in enumerate(sorted_users, 1):
            if uid == user_id:
                return rank
        return None
    
    def get_top_users(self, limit=10):
        """Получение топа пользователей по VSRAKOSTI"""
        sorted_users = sorted(self.user_vsrakost.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    def get_user_cards_count(self, user_id):
        """Получение количества карт у пользователя"""
        if user_id not in self.user_cards:
            return 0
        return len(self.user_cards[user_id])
    
    def get_user_cards_list(self, user_id):
        """Получение списка карт пользователя"""
        if user_id not in self.user_cards:
            return []
        return self.user_cards[user_id]
    
    def get_total_cards_count(self):
        """Получение общего количества карт в колоде"""
        return len(self.cards_list)
    
    def get_cooldown_time(self, user_id):
        """Получение оставшегося времени кулдауна"""
        if user_id not in self.user_cooldowns:
            return None
        
        last_open_time = self.user_cooldowns[user_id]
        cooldown_end = last_open_time + timedelta(minutes=COOLDOWN_MINUTES)
        now = datetime.now()
        
        if now >= cooldown_end:
            return None
        
        time_left = cooldown_end - now
        return time_left

# Создаем экземпляр бота
card_bot = CardBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    total_cards = card_bot.get_total_cards_count()
    user_cards_count = card_bot.get_user_cards_count(user_id)
    user_points = card_bot.user_vsrakost.get(user_id, 0)
    
    can_open, time_left = card_bot.can_open_card(user_id)
    
    welcome_text = (
        f"🎴 Добро пожаловать, {user_name}!\n"
    )
    
    
    if not can_open:
        mins, secs = time_left
        welcome_text += f"⏳ Следующую карту можно открыть через: {mins} мин {secs} сек\n\n"

    else:
        welcome_text += "✅ Можешь открыть карту прямо сейчас!\n\n"
    
    welcome_text += "📋 Доступные команды:\n/drop - Получить карту\n/list - Моя коллекция\n/top - Топ игроков"
    
    await update.message.reply_text(welcome_text)

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /drop - выдача случайной карты"""
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    
    # Проверяем кулдаун
    can_open, time_left = card_bot.can_open_card(user_id)
    if not can_open:
        mins, secs = time_left
        await update.message.reply_text(
            f"⏳ {user_name}, следующую карту можно открыть через:\n"
            f"🕐 {mins} минут {secs} секунд\n\n"
            f"💡 Таймер: {COOLDOWN_MINUTES} минут между открытиями"
        )
        return
    
    card = card_bot.get_random_card()
    
    if not card:
        await update.message.reply_text(
            "❌ Карты не найдены!\n"
            "Добавьте картинки в папку cards и перезапустите бота"
        )
        return
    
    # Получаем очки карты
    card_points = card_bot.card_points.get(card, 0)
    
    # Получаем абсолютный путь к карте
    current_dir = os.path.dirname(os.path.abspath(__file__))
    card_path = os.path.join(current_dir, CARDS_FOLDER, card)
    
    print(f"🔄 Пытаюсь отправить карту: {card} пользователю {user_id} ({user_name})")
    print(f"🎯 Карта дает {card_points} очков")
    
    try:
        # Проверяем существование файла
        if not os.path.exists(card_path):
            await update.message.reply_text(f"❌ Файл карты не найден: {card}")
            print(f"❌ Файл не существует: {card_path}")
            return
        
        # Отправляем картинку
        with open(card_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎴 Новая SRAKA!\n💎 Даёт очков: {card_points}\n⏰ Следующая карта через {COOLDOWN_MINUTES} минут"
            )
        
        # Устанавливаем кулдаун и добавляем карту пользователю
        card_bot.set_cooldown(user_id, context.application)
        earned_points = card_bot.add_card_to_user(user_id, card)
        
        # Получаем обновленные данные пользователя
        user_total_points = card_bot.user_vsrakost.get(user_id, 0)
        user_rank = card_bot.get_user_vsrakost_rank(user_id)
        
        print(f"✅ Успешно отправлена карта: {card} пользователю {user_id}, начислено {earned_points} очков")
        
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке карты {card}: {e}"
        print(error_msg)
        await update.message.reply_text("❌ Ошибка при отправке карты")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list - показывает коллекцию пользователя"""
    user_id = update.effective_user.id
    user_name = card_bot.get_user_display_name(user_id, update)
    user_cards_count = card_bot.get_user_cards_count(user_id)
    total_cards_count = card_bot.get_total_cards_count()
    user_points = card_bot.user_vsrakost.get(user_id, 0)
    user_rank = card_bot.get_user_vsrakost_rank(user_id)
    
    # Проверяем кулдаун
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

    else:
        message += "✅ Можешь открыть следующую карту! Используй /drop"
    
    await update.message.reply_text(message)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /top - показывает топ игроков"""
    top_users = card_bot.get_top_users(limit=10)
    
    message = "🏆 ТОП-10 ИГРОКОВ ПО VSRAKOSTI 🏆\n\n"
    
    if top_users:
        for i, (user_id, points) in enumerate(top_users, 1):
            # Для топа используем сохраненные имена
            if user_id in card_bot.user_names:
                display_name = card_bot.user_names[user_id]
            else:
                display_name = f"Игрок_{user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            message += f"{medal} {display_name} - {points} очков\n"
    else:
        message += "😴 Пока никто не заработал очков...\n"
    
    
    await update.message.reply_text(message)

def main():
    """Основная функция запуска бота"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Замените BOT_TOKEN на ваш настоящий токен бота!")
        return
    
    total_cards = card_bot.get_total_cards_count()
    if total_cards == 0:
        print("❌ ВНИМАНИЕ: Карты не найдены!")
        print("💡 Решение:")
        print("   1. Создайте папку 'cards' рядом с файлом бота")
        print("   2. Добавьте в нее картинки (PNG, JPG, JPEG, GIF, WEBP)")
        print("   3. Перезапустите бота")
    else:
        print(f"✅ Готов к работе! Загружено карт: {total_cards}")
        print(f"⏰ Таймер между открытиями: {COOLDOWN_MINUTES} минут")
        print(f"⭐ Система очков VSRAKOSTI: ВКЛЮЧЕНА")
        print(f"👤 Автоматические имена из Telegram: ВКЛЮЧЕНО")
        print(f"💾 Сохранение очков карт: ВКЛЮЧЕНО")
        
        # Показываем пример карт с очками
        print(f"\n🎴 Примеры карт с очками:")
        sample_cards = list(card_bot.card_points.items())[:5]
        for i, (card, points) in enumerate(sample_cards, 1):
            print(f"   {i}. {card} - {points} очков")
        
        # Показываем общую статистику по очкам
        total_card_points = sum(card_bot.card_points.values())
        avg_points = total_card_points / len(card_bot.card_points) if card_bot.card_points else 0
        print(f"\n📊 Статистика очков:")
        print(f"   Всего очков у всех карт: {total_card_points}")
        print(f"   Среднее очков на карту: {avg_points:.1f}")
        print(f"   Максимальное очков: {max(card_bot.card_points.values()) if card_bot.card_points else 0}")
        print(f"   Минимальное очков: {min(card_bot.card_points.values()) if card_bot.card_points else 0}")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("drop", drop_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("top", top_command))
        
        print("🤖 Бот запускается...")
        print("💬 Используйте /start в Telegram для начала работы")
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()