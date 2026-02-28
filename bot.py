import asyncio
import logging
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

    def log_message(self, format, *args):
        pass

def run_webserver():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Веб-сервер для Render запущен на порту {port}")
    server.serve_forever()

webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()
# =================================

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = "@HolyBux"
REVIEW_CHANNEL_ID = "@HolyBuxOtziv"
ADMIN_ID = 8009278482
ADMIN_USERNAME = "@emycac"
CHANNEL_NAME = "HolyBux"
REWARD_AMOUNT = 3000000
COOLDOWN_SECONDS = 3600
# =====================

# 🌈 КРАСИВЫЕ ЦВЕТА ДЛЯ КОНСОЛИ
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'
    ORANGE = '\033[38;5;214m'
    PINK = '\033[38;5;206m'

def current_time():
    return datetime.now().strftime("%H:%M:%S")

def current_datetime():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")

def log_success(text):
    print(f"{Colors.GREEN}[✅ {current_time()}] {text}{Colors.END}")

def log_info(text):
    print(f"{Colors.BLUE}[ℹ️ {current_time()}] {text}{Colors.END}")

def log_warning(text):
    print(f"{Colors.YELLOW}[⚠️ {current_time()}] {text}{Colors.END}")

def log_error(text):
    print(f"{Colors.RED}[❌ {current_time()}] {text}{Colors.END}")

def log_action(text):
    print(f"{Colors.PURPLE}[⚡ {current_time()}] {text}{Colors.END}")

def log_user_action(username, action):
    print(f"{Colors.CYAN}[👤 {current_time()}] {Colors.BOLD}{username}{Colors.END} {Colors.WHITE}{action}{Colors.END}")

def log_review(text):
    print(f"{Colors.PINK}[📝 {current_time()}] {text}{Colors.END}")

def log_system(text):
    print(f"{Colors.ORANGE}[🔧 {current_time()}] {text}{Colors.END}")

def log_divider():
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

def log_big_title(text):
    print(f"{Colors.BOLD}{Colors.PURPLE}▶▶▶ {current_time()} {text} ◀◀◀{Colors.END}")

logging.basicConfig(level=logging.CRITICAL)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_photo = State()
    waiting_nickname = State()
    waiting_review = State()

users = {}
withdraw_requests = {}
users_who_reviewed = set()

def get_user_data(user_id: int):
    if user_id not in users:
        users[user_id] = {'balance': 0, 'last_task_time': 0}
    return users[user_id]

def add_balance(user_id: int, amount: int):
    users[user_id]['balance'] += amount

def can_do_task(user_id: int) -> bool:
    user_data = get_user_data(user_id)
    current_time_sec = time.time()
    time_passed = current_time_sec - user_data['last_task_time']
    return time_passed >= COOLDOWN_SECONDS

def get_time_left(user_id: int) -> str:
    user_data = get_user_data(user_id)
    time_left = COOLDOWN_SECONDS - (time.time() - user_data['last_task_time'])
    if time_left <= 0:
        return "0"
    hours = int(time_left // 3600)
    minutes = int((time_left % 3600) // 60)
    seconds = int(time_left % 60)
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    elif minutes > 0:
        return f"{minutes}мин {seconds}сек"
    else:
        return f"{seconds}сек"

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ============= КЛАВИАТУРЫ =============
def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ДА", callback_data="yes")],
        [InlineKeyboardButton(text="❌ НЕТ", callback_data="no")]
    ])

def after_yes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", callback_data="subscribe_first")]
    ])

def sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="🔍 Я ПОДПИСАЛСЯ", callback_data="check_sub")]
    ])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 ЗАДАНИЕ", callback_data="task")],
        [InlineKeyboardButton(text="💰 БАЛАНС", callback_data="balance")],
        [InlineKeyboardButton(text="💸 ВЫВОД", callback_data="withdraw_menu")],
        [InlineKeyboardButton(text="📝 ОТЗЫВЫ", callback_data="reviews")],
        [InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="help")]
    ])

def withdraw_menu_keyboard(user_id: int):
    balance = get_user_data(user_id)['balance']
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💸 Вывести весь баланс ({balance:,})", callback_data="withdraw_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def admin_screenshot_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{user_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{user_id}")]
    ])

def admin_withdraw_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Купил", callback_data=f"bought_{user_id}"),
            InlineKeyboardButton(text="❌ Не купил", callback_data=f"not_bought_{user_id}")
        ]
    ])

# ============= ОБРАБОТЧИКИ =============
@dp.message(Command("start"))
async def start(message: Message):
    username = message.from_user.first_name
    log_divider()
    log_big_title(f"НОВЫЙ ПОЛЬЗОВАТЕЛЬ: {username}")
    log_user_action(username, f"🚀 ЗАПУСТИЛ БОТА [ID: {message.from_user.id}]")
    log_info(f"📅 Дата и время: {current_datetime()}")
    log_info(f"📱 Username: @{message.from_user.username or 'Нет'}")
    log_divider()
    await message.answer("🌟 **Привет! Хочешь получить валюту?**", reply_markup=start_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "help")
async def help_button(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "❓ ОТКРЫЛ ПОМОЩЬ")
    
    await callback.message.answer(
        f"❓ **У ТЕБЯ ЕСТЬ ПРОБЛЕМА?**\n\n"
        f"📝 **Пиши сюда:** {ADMIN_USERNAME}\n"
        f"📢 **Наш ТГК:** {CHANNEL_ID}\n"
        f"📝 **Канал с отзывами:** {REVIEW_CHANNEL_ID}\n\n"
        f"⚡ **Админ ответит в ближайшее время!**",
        parse_mode="Markdown"
    )
    await callback.answer()

# === Остальной код без изменений ===

# Для полной работоспособности оставьте все обработчики и функции из твоего предыдущего кода,
# включая баланс, задания, вывод и админские кнопки.

# ============= ЗАПУСК =============
async def main():
    print(f"{Colors.BOLD}{Colors.PURPLE}╔══════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║                 🚀 ТЕЛЕГРАМ БОТ ЗАПУЩЕН 🚀                  ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}╠══════════════════════════════════════════════════════════════╣{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  📢 Канал: {Colors.CYAN}{CHANNEL_ID}{Colors.END}                                            ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  📝 Канал отзывов: {Colors.PINK}{REVIEW_CHANNEL_ID}{Colors.END}                                  ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  👤 Админ: {Colors.GREEN}{ADMIN_USERNAME}{Colors.END}                                          ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  💰 Награда: {Colors.YELLOW}{REWARD_AMOUNT:,}{Colors.END} монет                                 ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  ⏱ Кулдаун: {Colors.YELLOW}{COOLDOWN_SECONDS//3600} час{Colors.END}                                          ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END}  ⏰ Время запуска: {Colors.YELLOW}{current_datetime()}{Colors.END}              ")
    print(f"{Colors.BOLD}{Colors.PURPLE}╚══════════════════════════════════════════════════════════════╝{Colors.END}")
    print("")
    log_system("🟢 Бот готов к работе! Ожидаю пользователей...")
    print("")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_warning("⏹ Бот остановлен пользователем")
    except Exception as e:
        log_error(f"❌ Критическая ошибка: {e}")
