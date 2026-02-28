import asyncio
import logging
import time
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ===== ВЕБ-СЕРВЕР =====
from aiohttp import web
import aiohttp

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = "@HolyBux"
REVIEW_CHANNEL_ID = "@HolyBuxOtziv"
ADMIN_ID = 8009278482
ADMIN_USERNAME = "@emycac"
CHANNEL_NAME = "HolyTime"
REWARD_AMOUNT = 3000000
COOLDOWN_SECONDS = 3600

# ===== КЛАССЫ СОСТОЯНИЙ =====
class States(StatesGroup):
    waiting_photo = State()
    waiting_review = State()
    waiting_nickname = State()

# ===== Глобальные переменные =====
users = {}
withdraw_requests = {}
users_who_reviewed = set()

# ===== ВЕБ-СЕРВЕР =====
app = web.Application()

async def handle_health(request):
    return web.Response(text="Bot is running!")

app.router.add_get('/', handle_health)
app.router.add_get('/health', handle_health)

# ===== ФУНКЦИИ РАБОТЫ С ДАННЫМИ =====
def load_users():
    global users
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                users = json.load(f)
        except:
            users = {}
    else:
        users = {}

def save_users():
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f)

def get_user_data(user_id):
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {'balance': 0, 'last_task_time': 0}
        save_users()
    return users[user_id_str]

def add_balance(user_id, amount):
    user_str_id = str(user_id)
    if user_str_id not in users:
        users[user_str_id] = {'balance': 0, 'last_task_time': 0}
    users[user_str_id]['balance'] += amount
    save_users()

def can_do_task(user_id):
    user_data = get_user_data(user_id)
    return (time.time() - user_data['last_task_time']) >= COOLDOWN_SECONDS

def get_time_left(user_id):
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

# ===== ЛОГИ =====
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

# ===== ИНИЦИАЛИЗАЦИЯ =====
logging.basicConfig(level=logging.CRITICAL)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== КЛАВИАТУРЫ =====
def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎉 Друзья", callback_data="ref_link")],
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
        [InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="help")],
        [InlineKeyboardButton(text="🎉 Друзья", callback_data="ref_link")]
    ])

def withdraw_menu_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💸 Вывести весь баланс ({get_user_data(user_id)['balance']:,})", callback_data="withdraw_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def admin_screenshot_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{user_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{user_id}")]
    ])

def admin_withdraw_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купил", callback_data=f"bought_{user_id}"),
         InlineKeyboardButton(text="❌ Не купил", callback_data=f"not_bought_{user_id}")]
    ])

# ===== ОБРАБОТЧИКИ =====
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

@dp.callback_query(types.F.data == "no")
async def no(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "❌ НАЖАЛ НЕТ")
    await callback.message.edit_text("😕 Окей, если не хочешь, то как хочешь)\nЕсли передумаешь, пиши /start")
    await callback.answer()

@dp.callback_query(types.F.data == "yes")
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
        await callback.message.edit_text(
            f"🔒 **Чтобы получать валюту, подпишись на канал {CHANNEL_ID}**\n\n"
            f"Нажми кнопку ниже чтобы подписаться 👇",
            reply_markup=after_yes_keyboard(),
            parse_mode="Markdown"
        )
    await callback.answer()

@dp.callback_query(types.F.data == "subscribe_first")
async def subscribe_first(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "📢 НАЖАЛ ПОДПИСАТЬСЯ")
    await callback.message.edit_text(
        f"🔒 **Подпишись на канал {CHANNEL_ID}**\n\n"
        "1️⃣ Нажми кнопку **'Подписаться'**\n"
        "2️⃣ Вернись сюда и нажми **'Я ПОДПИСАЛСЯ'**\n\n"
        "👇 **Кнопки ниже:**",
        reply_markup=sub_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(types.F.data == "check_sub")
async def check_subscribe(callback: CallbackQuery):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "🔍 ПРОВЕРЯЕТ ПОДПИСКУ")
    if await check_sub(user_id):
        log_success(f"✅ {username} ПОДТВЕРДИЛ ПОДПИСКУ - ПЕРЕХОД В МЕНЮ")
        await callback.message.delete()
        await callback.message.answer(
            "✅ **Подписка подтверждена! Добро пожаловать!**\n\n"
            "📋 **ЗАДАНИЕ** - получить задание\n"
            "💰 **БАЛАНС** - проверить монеты\n"
            "💸 **ВЫВОД** - вывести средства\n"
            "📝 **ОТЗЫВЫ** - оставить отзыв\n"
            "❓ **ПОМОЩЬ** - помощь",
            reply_markup=menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        log_warning(f"⚠️ {username} ВСЕ ЕЩЕ НЕ ПОДПИСАН")
        await callback.answer(
            "❌ Ты еще не подписался!\n\n"
            "1. Нажми кнопку 'Подписаться'\n"
            "2. Подпишись на канал\n"
            "3. Вернись и нажми 'Я ПОДПИСАЛСЯ'",
            show_alert=True
        )

@dp.callback_query(types.F.data == "reviews")
async def reviews_button(callback: CallbackQuery, state: FSMContext):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "📝 НАЖАЛ ОТЗЫВЫ")
    if user_id in users_who_reviewed:
        log_warning(f"⚠️ {username} УЖЕ ПИСАЛ ОТЗЫВ")
        await callback.answer(
            "❌ **Вы уже оставляли отзыв!**\n\nСпасибо за ваше мнение, но можно оставить только один отзыв.",
            show_alert=True
        )
        return
    await callback.message.answer(
        "📝 **Напишите ваш отзыв о нашем проекте**\n\n"
        "✍️ Просто отправьте текст сообщением\n\n"
        "📢 Отзыв будет опубликован в канале @HolyBuxOtziv",
        parse_mode="Markdown"
    )
    await state.set_state(States.waiting_review)
    await callback.answer()

@dp.callback_query(types.F.data == "help")
async def help_button(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "❓ ОТКРЫЛ ПОМОЩЬ")
    await callback.message.answer(
        f"❓ **У ТЕБЯ ЕСТЬ ПРОБЛЕМА?**\n\n"
        f"📝 **Пиши сюда:** {ADMIN_USERNAME}\n"
        f"📢 **Наш ТГК:** {CHANNEL_NAME}\n"
        f"📝 **Канал с отзывами:** {REVIEW_CHANNEL_ID}\n\n"
        f"⚡ **Админ ответит в ближайшее время!**",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(types.F.data == "task")
async def task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    if not can_do_task(user_id):
        await remind_user_about_cooldown(user_id, chat_id)
        time_left = get_time_left(user_id)
        await callback.answer(
            f"⏳ Подожди {time_left} до следующего задания!", show_alert=True
        )
        return
    log_user_action(callback.from_user.first_name, "📋 ПЫТАЕТСЯ ВЗЯТЬ ЗАДАНИЕ")
    log_success(f"✅ {callback.from_user.first_name} ВЗЯЛ ЗАДАНИЕ")
    await callback.message.edit_text(
        "📋 **Твоё задание:**\n\n"
        "1️⃣ Зайди на сервер\n"
        "2️⃣ Напиши в чат: !Кому нужна валюта заходим в тг бота @HolyBuxBot_Bot\n"
        "3️⃣ Сделай скриншот\n"
        "4️⃣ Отправь скриншот сюда\n\n"
        f"💰 Награда: {REWARD_AMOUNT:,} монет"
    )
    await callback.message.answer("📸 **Отправь скриншот:**", parse_mode="Markdown")
    await state.set_state(States.waiting_photo)
    await callback.answer()

@dp.message(States.waiting_photo, types.F.photo)
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
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=f"Новый скриншот от {name} (ID: {user_id})",
            reply_markup=admin_screenshot_keyboard(user_id)
        )
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

@dp.message(States.waiting_review)
async def handle_review(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    user_tag = message.from_user.username or "Нет username"
    review_text = message.text
    if user_id in users_who_reviewed:
        await message.answer(
            "❌ **Вы уже оставляли отзыв!**\n\nСпасибо за ваше мнение, но можно оставить только один отзыв.",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    log_review(f"📝 НОВЫЙ ОТЗЫВ от {username}: {review_text[:50]}...")
    try:
        review_message = (
            f"📝 **Новый отзыв!**\n\n"
            f"👤 **Отзыв от** @{user_tag}\n"
            f"💬 **Текст отзыва:**\n"
            f"«{review_text}»"
        )
        await bot.send_message(
            chat_id=REVIEW_CHANNEL_ID,
            text=review_message,
            parse_mode="Markdown"
        )
        users_who_reviewed.add(user_id)
        log_success(f"✅ Отзыв от {username} опубликован в канале {REVIEW_CHANNEL_ID}")
        await message.answer(
            "✅ **Спасибо за ваш отзыв!**\n\n"
            f"📢 Он уже опубликован в канале {REVIEW_CHANNEL_ID}\n\n"
            "🔝 Чтобы вернуться в меню, нажми /start",
            parse_mode="Markdown"
        )
    except Exception as e:
        log_error(f"❌ Ошибка при отправке отзыва в канал: {e}")
        await message.answer(
            "❌ **Ошибка при отправке отзыва**\n\n"
            "Попробуйте позже или напишите админу @emycac",
            parse_mode="Markdown"
        )
    await state.clear()

@dp.callback_query(types.F.data == "balance")
async def balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, f"💰 ПРОВЕРИЛ БАЛАНС: {user_data['balance']:,} монет")
    if not can_do_task(user_id):
        await remind_user_about_cooldown(user_id, callback.message.chat.id)
        time_left = get_time_left(user_id)
        await callback.answer(
            f"⏳ Подожди {time_left} до следующего задания!", show_alert=True
        )
        return
    if can_do_task(user_id):
        task_status = "✅ Доступно"
    else:
        task_status = f"⏳ Через {get_time_left(user_id)}"
    await callback.message.answer(
        f"💰 **Твой баланс:** {user_data['balance']:,} монет\n\n"
        f"📊 **Статус задания:** {task_status}",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(types.F.data == "withdraw_menu")
async def withdraw_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, "💸 ОТКРЫЛ МЕНЮ ВЫВОДА")
    if user_data['balance'] <= 0:
        await callback.answer("❌ У тебя нет монет для вывода! Выполни задание.", show_alert=True)
        return
    if not can_do_task(user_id):
        await remind_user_about_cooldown(user_id, callback.message.chat.id)
    await callback.message.edit_text(
        f"💸 **Меню вывода средств**\n\n"
        f"💰 **Твой баланс:** {user_data['balance']:,} монет\n\n"
        f"Выбери действие:",
        reply_markup=withdraw_menu_keyboard(user_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(types.F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "🔙 ВЕРНУЛСЯ В ГЛАВНОЕ МЕНЮ")
    await callback.message.edit_text(
        "✅ **Выбирай что нужно:**",
        reply_markup=menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(types.F.data == "withdraw_all")
async def withdraw_all(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, f"💸 ХОЧЕТ ВЫВЕСТИ {user_data['balance']:,} монет")
    if user_data['balance'] <= 0:
        await callback.answer("❌ Нет монет для вывода!", show_alert=True)
        return
    if not can_do_task(user_id):
        await remind_user_about_cooldown(user_id, callback.message.chat.id)
    await callback.message.edit_text(
        f"💸 **Вывод средств**\n\n"
        f"💰 **Сумма к выводу:** {user_data['balance']:,} монет\n\n"
        f"📝 **Инструкция:**\n"
        f"1️⃣ Зайди на сервер **HolyTime**\n"
        f"2️⃣ Выставь на аукцион предмет за **{user_data['balance']:,} монет**\n"
        f"3️⃣ Напиши сюда свой **никнейм**\n\n"
        f"✍️ **Введи свой никнейм:**",
        parse_mode="Markdown"
    )
    await state.set_state(States.waiting_nickname)

@dp.message(States.waiting_nickname)
async def handle_nickname(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    nickname = message.text.strip()
    user_data = get_user_data(user_id)
    amount = user_data['balance']
    log_user_action(username, f"✍️ ВВЕЛ НИКНЕЙМ: {nickname}")
    if len(nickname) < 2 or len(nickname) > 32:
        await message.answer(
            "❌ **Некорректный никнейм!**\n"
            "Введи никнейм длиной от 2 до 32 символов:"
        )
        return
    users[str(user_id)]['last_task_time'] = time.time()
    save_users()
    withdraw_requests[user_id] = {
        'amount': amount,
        'nickname': nickname,
        'time': time.time()
    }
    await message.answer(
        f"✅ **Запрос на вывод отправлен!**\n\n"
        f"💰 **Сумма:** {amount:,} монет\n"
        f"👤 **Никнейм:** {nickname}\n"
        f"🌐 **Сервер:** HolyTime\n\n"
        f"⏳ Ожидай проверки администратором...",
        parse_mode="Markdown"
    )
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 НОВЫЙ ЗАПРОС НА ВЫВОД\n\n"
            f"👤 Пользователь: {message.from_user.full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📱 Username: @{message.from_user.username or 'Нет'}\n"
            f"💰 Сумма: {amount:,} монет\n"
            f"👤 Никнейм: {nickname}\n"
            f"🌐 Сервер: HolyTime\n\n"
            f"Проверь аукцион!",
            reply_markup=admin_withdraw_keyboard(user_id)
        )
        log_success(f"✅ Запрос на вывод отправлен админу")
    except Exception as e:
        log_error(f"❌ Ошибка отправки админу: {e}")
        await message.answer("⚠️ Ошибка при отправке запроса админу")
    await state.clear()

@dp.callback_query(types.F.data.startswith("ok_"))
async def approve_screenshot(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        log_warning(f"⚠️ Попытка подтверждения не админом: {callback.from_user.first_name}")
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    add_balance(user_id, REWARD_AMOUNT)
    users[str(user_id)]['last_task_time'] = time.time()
    save_users()
    log_big_title(f"АДМИН ПОДТВЕРДИЛ СКРИНШОТ")
    log_action(f"👑 Админ подтвердил скриншот пользователя ID:{user_id}")
    log_success(f"💰 Начислено {REWARD_AMOUNT:,} монет")
    try:
        await bot.send_message(
            user_id,
            f"✅ **Админ {ADMIN_USERNAME}** подтвердил ваш скриншот!\n\n"
            f"🎉 **+{REWARD_AMOUNT:,} монет** зачислено на баланс!\n"
            f"💰 **Текущий баланс:** {users[str(user_id)]['balance']:,} монет",
            parse_mode="Markdown"
        )
        log_success(f"✅ Уведомление отправлено пользователю")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление пользователю: {e}")
    await callback.message.delete()
    await callback.answer("Готово!")

@dp.callback_query(types.F.data.startswith("no_"))
async def reject_screenshot(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        log_warning(f"⚠️ Попытка отклонения не админом: {callback.from_user.first_name}")
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    log_big_title(f"АДМИН ОТКЛОНИЛ СКРИНШОТ")
    log_action(f"👑 Админ отклонил скриншот пользователя ID:{user_id}")
    try:
        await bot.send_message(
            user_id,
            "❌ **Ваш скриншот был отклонен!**\n\n"
            "Причина: ты не выполнил задание по инструкции.\n"
            "Попробуй еще раз!",
            parse_mode="Markdown"
        )
        log_success(f"✅ Уведомление об отказе отправлено")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление об отказе: {e}")
    await callback.message.delete()
    await callback.answer("Готово!")

@dp.callback_query(types.F.data.startswith("bought_"))
async def bought(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    if str(user_id) in users:
        old_balance = users[str(user_id)]['balance']
        users[str(user_id)]['balance'] = 0
        save_users()
        log_big_title(f"АДМИН: КУПЛЕНО")
        log_action(f"👑 Админ подтвердил покупку для пользователя {user_id}")
        log_success(f"💰 Списано {old_balance:,} монет")
        try:
            await bot.send_message(
                user_id,
                "✅ **Администрация купила ваш предмет!**\n\n"
                "📝 **Если хотите, напишите отзыв о нашем проекте!**\n\n"
                "👉 Нажмите кнопку **📝 ОТЗЫВЫ** в главном меню и напишите отзыв\n\n"
                "📢 Ваш отзыв будет опубликован в канале @HolyBuxOtziv от вашего имени",
                parse_mode="Markdown"
            )
            log_success(f"✅ Уведомление о покупке с предложением отзыва отправлено пользователю {user_id}")
        except Exception as e:
            log_error(f"❌ Не удалось отправить уведомление: {e}")
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ **КУПЛЕНО**\n💰 Баланс обнулен"
        )
        await callback.answer("Готово!")

@dp.callback_query(types.F.data.startswith("not_bought_"))
async def not_bought(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    log_big_title(f"АДМИН: НЕ КУПЛЕНО")
    log_action(f"👑 Админ отклонил покупку для пользователя {user_id}")
    try:
        await bot.send_message(
            user_id,
            "❌ **Вы не выставили предмет либо ваш ник неправильный!**\n\n"
            "💰 Ваш баланс сохранен. Попробуйте еще раз.",
            parse_mode="Markdown"
        )
        log_success(f"✅ Уведомление об отказе отправлено")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление: {e}")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ **НЕ КУПЛЕНО**\n💰 Баланс сохранен"
    )
    await callback.answer("Готово!")

@dp.message()
async def handle_other_messages(message: Message):
    if message.text and message.text.startswith('/'):
        return
    await message.answer("❓ **Используй кнопки меню или команду /start**", parse_mode="Markdown")

async def remind_user_about_cooldown(user_id, chat_id):
    time_left = get_time_left(user_id)
    if time_left != "0":
        try:
            await bot.send_message(
                chat_id,
                f"⏳ Осталось подождать: {time_left} до следующего задания!"
            )
        except Exception as e:
            log_error(f"Ошибка при отправке напоминания: {e}")

async def start_bot():
    load_users()
    print(f"{Colors.BOLD}{Colors.PURPLE}╔══════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║                      🚀 БОТ ЗАПУЩЕН 🚀                       ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}╠══════════════════════════════════════════════════════════════╣{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 📢 Канал: {Colors.CYAN}{CHANNEL_ID}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 📝 Канал отзывов: {Colors.PINK}{REVIEW_CHANNEL_ID}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 👤 Админ: {Colors.GREEN}{ADMIN_USERNAME}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 💰 Награда: {Colors.YELLOW}{REWARD_AMOUNT:,}{Colors.END} монет ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} ⏱ Кулдаун: {Colors.YELLOW}{COOLDOWN_SECONDS//3600} час{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} ⏰ Время запуска: {Colors.YELLOW}{current_datetime()}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 🔄 Пинг: {Colors.GREEN}GITHUB ACTIONS КАЖДУЮ МИНУТУ{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}╚══════════════════════════════════════════════════════════════╝{Colors.END}")
    print("")
    log_system("🟢 Бот готов к работе! Ожидаю пользователей...")
    print("")
    await dp.start_polling(bot)

# ===== ТОЧКА ВХОДА =====
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_bot())
    
    port = int(os.environ.get('PORT', 10000))
    web.run_app(app, host='0.0.0.0', port=port)
