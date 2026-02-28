import asyncio
import logging
import time
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = "@HolyBux"
REVIEW_CHANNEL_ID = "@HolyBuxOtziv"
ADMIN_ID = 8009278482
ADMIN_USERNAME = "@emycac"
CHANNEL_NAME = "HolyTime"
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

def log_success(text): print(f"{Colors.GREEN}[✅ {current_time()}] {text}{Colors.END}")
def log_info(text): print(f"{Colors.BLUE}[ℹ️ {current_time()}] {text}{Colors.END}")
def log_warning(text): print(f"{Colors.YELLOW}[⚠️ {current_time()}] {text}{Colors.END}")
def log_error(text): print(f"{Colors.RED}[❌ {current_time()}] {text}{Colors.END}")
def log_action(text): print(f"{Colors.PURPLE}[⚡ {current_time()}] {text}{Colors.END}")
def log_user_action(username, action): print(f"{Colors.CYAN}[👤 {current_time()}] {Colors.BOLD}{username}{Colors.END} {Colors.WHITE}{action}{Colors.END}")
def log_review(text): print(f"{Colors.PINK}[📝 {current_time()}] {text}{Colors.END}")
def log_system(text): print(f"{Colors.ORANGE}[🔧 {current_time()}] {text}{Colors.END}")
def log_divider(): print(f"{Colors.BLUE}{'='*70}{Colors.END}")
def log_big_title(text): print(f"{Colors.BOLD}{Colors.PURPLE}▶▶▶ {current_time()} {text} ◀◀◀{Colors.END}")

logging.basicConfig(level=logging.CRITICAL)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_photo = State()
    waiting_nickname = State()
    waiting_review = State()

# ======== ДАННЫЕ С ПЕРСИСТЕНЦИЕЙ ========
users = {}
withdraw_requests = {}
users_who_reviewed = set()
DATA_FILE = "data.json"

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "users": users,
            "withdraw_requests": withdraw_requests,
            "users_who_reviewed": list(users_who_reviewed)
        }, f, indent=4)

def load_data():
    global users, withdraw_requests, users_who_reviewed
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            users = data.get("users", {})
            withdraw_requests = data.get("withdraw_requests", {})
            users_who_reviewed = set(data.get("users_who_reviewed", []))

def get_user_data(user_id: int):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {'balance': 0, 'last_task_time': 0}
        save_data()
    return users[user_id]

def add_balance(user_id: int, amount: int):
    user_id = str(user_id)
    users[user_id]['balance'] += amount
    save_data()

def can_do_task(user_id: int) -> bool:
    user_data = get_user_data(user_id)
    current_time_val = time.time()
    time_passed = current_time_val - user_data['last_task_time']
    return time_passed >= COOLDOWN_SECONDS

def get_time_left(user_id: int) -> str:
    user_data = get_user_data(user_id)
    time_left = COOLDOWN_SECONDS - (time.time() - user_data['last_task_time'])
    if time_left <= 0:
        return "0"
    hours = int(time_left // 3600)
    minutes = int((time_left % 3600) // 60)
    seconds = int(time_left % 60)
    if hours > 0: return f"{hours}ч {minutes}мин"
    elif minutes > 0: return f"{minutes}мин {seconds}сек"
    else: return f"{seconds}сек"

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ================= КЛАВИАТУРЫ =================
def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ ДА", callback_data="yes")],
                                                 [InlineKeyboardButton(text="❌ НЕТ", callback_data="no")]])

def after_yes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", callback_data="subscribe_first")]])

def sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_ID[1:]}")],
                                                 [InlineKeyboardButton(text="🔍 Я ПОДПИСАЛСЯ", callback_data="check_sub")]])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 ЗАДАНИЕ", callback_data="task")],
                                                 [InlineKeyboardButton(text="💰 БАЛАНС", callback_data="balance")],
                                                 [InlineKeyboardButton(text="💸 ВЫВОД", callback_data="withdraw_menu")],
                                                 [InlineKeyboardButton(text="📝 ОТЗЫВЫ", callback_data="reviews")],
                                                 [InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="help")]])

def withdraw_menu_keyboard(user_id: int):
    balance = get_user_data(user_id)['balance']
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"💸 Вывести весь баланс ({balance:,})", callback_data="withdraw_all")],
                                                 [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]])

def admin_screenshot_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{user_id}"),
                                                 InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{user_id}")]])

def admin_withdraw_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Купил", callback_data=f"bought_{user_id}"),
                                                 InlineKeyboardButton(text="❌ Не купил", callback_data=f"not_bought_{user_id}")]])

# ================= ОБРАБОТЧИКИ =================
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

@dp.callback_query(F.data == "no")
async def no(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "❌ НАЖАЛ НЕТ")
    await callback.message.edit_text("😕 Окей, если не хочешь, то как хочешь)\nЕсли передумаешь, пиши /start")
    await callback.answer()

@dp.callback_query(F.data == "yes")
async def yes(callback: CallbackQuery):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "✅ НАЖАЛ ДА")
    if await check_sub(user_id):
        log_success(f"✅ {username} УЖЕ ПОДПИСАН НА КАНАЛ")
        await callback.message.delete()
        await callback.message.answer("✅ **Ты уже подписан! Выбирай что нужно:**", reply_markup=menu_keyboard(), parse_mode="Markdown")
    else:
        log_warning(f"⚠️ {username} НЕ ПОДПИСАН - показываем кнопку подписки")
        await callback.message.edit_text(f"🔒 **Чтобы получать валюту, подпишись на канал {CHANNEL_ID}**\n\nНажми кнопку ниже чтобы подписаться 👇",
                                         reply_markup=after_yes_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "subscribe_first")
async def subscribe_first(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "📢 НАЖАЛ ПОДПИСАТЬСЯ")
    await callback.message.edit_text(f"🔒 **Подпишись на канал {CHANNEL_ID}**\n\n1️⃣ Нажми кнопку **'Подписаться'**\n2️⃣ Вернись сюда и нажми **'Я ПОДПИСАЛСЯ'**\n\n👇 **Кнопки ниже:**",
                                     reply_markup=sub_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "check_sub")
async def check_subscribe(callback: CallbackQuery):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "🔍 ПРОВЕРЯЕТ ПОДПИСКУ")
    if await check_sub(user_id):
        log_success(f"✅ {username} ПОДТВЕРДИЛ ПОДПИСКУ - ПЕРЕХОД В МЕНЮ")
        await callback.message.delete()
        await callback.message.answer("✅ **Подписка подтверждена! Добро пожаловать!**\n\n📋 **ЗАДАНИЕ** - получить задание\n💰 **БАЛАНС** - проверить монеты\n💸 **ВЫВОД** - вывести средства\n📝 **ОТЗЫВЫ** - оставить отзыв\n❓ **ПОМОЩЬ** - помощь",
                                      reply_markup=menu_keyboard(), parse_mode="Markdown")
    else:
        log_warning(f"⚠️ {username} ВСЕ ЕЩЕ НЕ ПОДПИСАН")
        await callback.answer("❌ Ты еще не подписался!\n\n1. Нажми кнопку 'Подписаться'\n2. Подпишись на канал\n3. Вернись и нажми 'Я ПОДПИСАЛСЯ'",
                              show_alert=True)

# ================= ЗАДАНИЕ =================
@dp.callback_query(F.data == "task")
async def task(callback: CallbackQuery, state: FSMContext):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "📋 ПЫТАЕТСЯ ВЗЯТЬ ЗАДАНИЕ")
    if not can_do_task(user_id):
        time_left = get_time_left(user_id)
        log_warning(f"⚠️ {username} НЕ МОЖЕТ ВЗЯТЬ ЗАДАНИЕ. Осталось: {time_left}")
        await callback.answer(f"⏳ Подожди {time_left} до следующего задания!", show_alert=True)
        return
    log_success(f"✅ {username} ВЗЯЛ ЗАДАНИЕ")
    await callback.message.edit_text("📋 **Твоё задание:**\n\n1️⃣ Зайди на сервер\n2️⃣ Напиши в чат: !Кому нужна валюта заходим в тг бота @HolyBuxBot_Bot\n3️⃣ Сделай скриншот\n4️⃣ Отправь скриншот сюда\n\n💰 Награда: {REWARD_AMOUNT:,} монет")
    await callback.message.answer("📸 **Отправь скриншот:**", parse_mode="Markdown")
    await state.set_state(States.waiting_photo)
    await callback.answer()

@dp.message(States.waiting_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    name = message.from_user.full_name
    log_user_action(username, "📸 ОТПРАВИЛ СКРИНШОТ")
    log_info(f"🆔 ID фото: {message.photo[-1].file_id}")
    photo = message.photo[-1]
    await message.answer("✅ **Скриншот отправлен на проверку!**", parse_mode="Markdown")
    log_success(f"✅ Скриншот от {username} отправлен админу")
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=f"Новый скриншот от {name} (ID: {user_id})", reply_markup=admin_screenshot_keyboard(user_id))
        log_success(f"✅ Фото доставлено админу")
    except Exception as e:
        log_error(f"❌ Ошибка отправки админу: {e}")
        await message.answer("⚠️ Ошибка при отправке админу")
    await state.clear()

@dp.message(States.waiting_photo)
async def not_photo(message: Message):
    username = message.from_user.first_name
    log_warning(f"⚠️ {username} ОТПРАВИЛ НЕ ФОТО")
    await message.answer("❌ **Отправь фото, а не текст!**\n\n📸 Сделай скриншот задания и отправь его как фото.", parse_mode="Markdown")

# ================= ОТЗЫВ =================
@dp.callback_query(F.data == "reviews")
async def reviews_button(callback: CallbackQuery, state: FSMContext):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "📝 НАЖАЛ ОТЗЫВЫ")
    if user_id in users_who_reviewed:
        log_warning(f"⚠️ {username} УЖЕ ПИСАЛ ОТЗЫВ")
        await callback.answer("❌ Вы уже оставляли отзыв!\n\nСпасибо за ваше мнение, но можно оставить только один отзыв.", show_alert=True)
        return
    await callback.message.answer("📝 **Напишите ваш отзыв о нашем проекте**\n\n✍️ Просто отправьте текст сообщением\n\n📢 Отзыв будет опубликован в канале @HolyBuxOtziv", parse_mode="Markdown")
    await state.set_state(States.waiting_review)
    await callback.answer()

@dp.message(States.waiting_review)
async def handle_review(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    user_tag = message.from_user.username or "Нет username"
    review_text = message.text
    if user_id in users_who_reviewed:
        await message.answer("❌ **Вы уже оставляли отзыв!**\n\nСпасибо за ваше мнение, но можно оставить только один отзыв.", parse_mode="Markdown")
        await state.clear()
        return
    log_review(f"📝 НОВЫЙ ОТЗЫВ от {username}: {review_text[:50]}...")
    try:
        review_message = f"📝 **Новый отзыв!**\n\n👤 **Отзыв от** @{user_tag}\n💬 **Текст отзыва:**\n«{review_text}»"
        await bot.send_message(chat_id=REVIEW_CHANNEL_ID, text=review_message, parse_mode="Markdown")
        users_who_reviewed.add(user_id)
        save_data()
        log_success(f"✅ Отзыв от {username} опубликован в канале {REVIEW_CHANNEL_ID}")
        await message.answer(f"✅ **Спасибо за ваш отзыв!**\n\n📢 Он уже опубликован в канале {REVIEW_CHANNEL_ID}\n\n🔝 Чтобы вернуться в меню, нажми /start", parse_mode="Markdown")
    except Exception as e:
        log_error(f"❌ Ошибка при отправке отзыва в канал: {e}")
        await message.answer("❌ **Ошибка при отправке отзыва**\n\nПопробуйте позже или напишите админу @emycac", parse_mode="Markdown")
    await state.clear()

# ================= БАЛАНС =================
@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, f"💰 ПРОВЕРИЛ БАЛАНС: {user_data['balance']:,} монет")
    task_status = "✅ Доступно" if can_do_task(user_id) else f"⏳ Через {get_time_left(user_id)}"
    await callback.message.answer(f"💰 **Твой баланс:** {user_data['balance']:,} монет\n\n📊 **Статус задания:** {task_status}", parse_mode="Markdown")
    await callback.answer()

# ================== ВЫВОД ==================
@dp.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, "💸 ОТКРЫЛ МЕНЮ ВЫВОДА")
    if user_data['balance'] <= 0:
        await callback.answer("❌ У тебя нет монет для вывода! Выполни задание.", show_alert=True)
        return
    await callback.message.answer("💸 **Меню вывода:**", reply_markup=withdraw_menu_keyboard(user_id), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "withdraw_all")
async def withdraw_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    if user_data['balance'] <= 0:
        await callback.answer("❌ У тебя нет монет для вывода!", show_alert=True)
        return
    withdraw_requests[user_id] = {
        "amount": user_data['balance'],
        "status": "pending"
    }
    save_data()
    await callback.message.answer(f"💸 **Заявка на вывод {user_data['balance']:,} монет отправлена!**\n\nОжидайте подтверждения от админа.", parse_mode="Markdown")
    log_action(f"💸 {username} отправил заявку на вывод {user_data['balance']:,} монет")
    await callback.answer()

# ===================== ОСНОВНОЙ =====================
async def main():
    load_data()
    log_system("✅ Данные загружены")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
