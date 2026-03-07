import asyncio
import logging
import time
import os
import json
from datetime import datetime
from threading import Thread
import requests
from supabase import create_client

# ===== SUPABASE =====
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase подключен!")

# Версия: 20260307-205251 🔥

# ===== САМОПИНГЕР =====
def ping_self():
    render_url = "https://hollybux-bot.onrender.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        try:
            response = requests.get(render_url, headers=headers, timeout=10)
print("🔥 Автопинг: 20:52:51 - Статус: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка пинга: {e}")
        time.sleep(600)

ping_thread = Thread(target=ping_self, daemon=True)
ping_thread.start()
print("🔥 Самопингер активен 24/7")

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ===== ВЕБ-СЕРВЕР =====
from aiohttp import web

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = "@HolyBux"
REVIEW_CHANNEL_ID = "@HolyBuxOtziv"
ADMIN_ID = 8009278482
ADMIN_USERNAME = "@emycac"
CHANNEL_NAME = "HolyTime"
REWARD_AMOUNT = 3000000
COOLDOWN_SECONDS = 3600
REFERRAL_BONUS = 1000000

# ===== КЛАССЫ СОСТОЯНИЙ =====
class States(StatesGroup):
    waiting_photo = State()
    waiting_review = State()
    waiting_nickname = State()

# ===== ФУНКЦИИ РАБОТЫ С SUPABASE =====
def get_user_data(user_id):
    """Получить данные пользователя из Supabase"""
    try:
        response = supabase.table('users').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return {
                'balance': response.data[0]['balance'],
                'last_task_time': response.data[0]['last_task_time']
            }
        else:
            # Создаем нового пользователя
            new_user = {
                'user_id': user_id,
                'balance': 0,
                'last_task_time': 0
            }
            supabase.table('users').insert(new_user).execute()
            return {'balance': 0, 'last_task_time': 0}
    except Exception as e:
        print(f"❌ Ошибка Supabase: {e}")
        return {'balance': 0, 'last_task_time': 0}

def add_balance(user_id, amount):
    """Добавить баланс пользователю"""
    try:
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        current_balance = response.data[0]['balance'] if response.data else 0
        new_balance = current_balance + amount
        supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
        return new_balance
    except Exception as e:
        print(f"❌ Ошибка обновления баланса: {e}")
        return 0

def update_last_task(user_id, task_time):
    """Обновить время последнего задания"""
    try:
        supabase.table('users').update({'last_task_time': task_time}).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"❌ Ошибка обновления времени: {e}")

def add_referral(user_id, referral_id):
    """Добавить реферала"""
    try:
        response = supabase.table('users').select('referrals').eq('user_id', user_id).execute()
        referrals = response.data[0].get('referrals', []) if response.data else []
        
        if referral_id not in referrals:
            referrals.append(referral_id)
            supabase.table('users').update({'referrals': referrals}).eq('user_id', user_id).execute()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка добавления реферала: {e}")
        return False

def add_screenshot(user_id, screenshot_id):
    """Сохранить ID скриншота"""
    try:
        response = supabase.table('users').select('screenshots').eq('user_id', user_id).execute()
        screenshots = response.data[0].get('screenshots', []) if response.data else []
        
        if screenshot_id not in screenshots:
            screenshots.append(screenshot_id)
            supabase.table('users').update({'screenshots': screenshots}).eq('user_id', user_id).execute()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка сохранения скриншота: {e}")
        return False

def set_reviewed(user_id):
    """Отметить что пользователь оставил отзыв"""
    try:
        supabase.table('users').update({'reviewed': True}).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"❌ Ошибка обновления отзыва: {e}")

def is_reviewed(user_id):
    """Проверить оставлял ли пользователь отзыв"""
    try:
        response = supabase.table('users').select('reviewed').eq('user_id', user_id).execute()
        return response.data[0].get('reviewed', False) if response.data else False
    except Exception as e:
        print(f"❌ Ошибка проверки отзыва: {e}")
        return False

# ===== ВЕБ-СЕРВЕР =====
app = web.Application()

async def handle_health(request):
    return web.Response(text="Bot is running!")

app.router.add_get('/', handle_health)
app.router.add_get('/health', handle_health)

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
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ===== КЛАВИАТУРЫ =====
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
        [InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="help")],
        [InlineKeyboardButton(text="🎉 Друзья", callback_data="ref_link")]
    ])

def withdraw_menu_keyboard(user_id):
    user_data = get_user_data(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💸 Вывести весь баланс ({user_data['balance']:,})", callback_data="withdraw_all")],
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
@dp.message_handler(commands=['start'])
async def start(message: Message):
    username = message.from_user.first_name
    user_id = message.from_user.id
    
    args = message.get_args()
    if args and args.isdigit():
        referrer_id = int(args)
        if referrer_id != user_id:
            if add_referral(referrer_id, user_id):
                add_balance(referrer_id, REFERRAL_BONUS)
                try:
                    await bot.send_message(
                        referrer_id,
                        f"🎉 **По вашей ссылке зарегистрировался новый пользователь!**\n\n"
                        f"👤 {username}\n"
                        f"💰 **+{REFERRAL_BONUS:,} монет** зачислено на баланс!"
                    )
                except:
                    pass
                log_success(f"💰 Реферал: {username} (ID: {user_id}) от {referrer_id} +{REFERRAL_BONUS:,}")
    
    get_user_data(user_id)
    
    log_divider()
    log_big_title(f"НОВЫЙ ПОЛЬЗОВАТЕЛЬ: {username}")
    log_user_action(username, f"🚀 ЗАПУСТИЛ БОТА [ID: {user_id}]")
    log_divider()
    await message.answer("🌟 **Привет! Хочешь получить валюту?**", reply_markup=start_keyboard(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'ref_link')
async def ref_link(callback: CallbackQuery):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "🎉 НАЖАЛ ДРУЗЬЯ")
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    response = supabase.table('users').select('referrals').eq('user_id', user_id).execute()
    referral_count = len(response.data[0].get('referrals', [])) if response.data else 0
    
    await callback.message.answer(
        f"🎉 **Реферальная система**\n\n"
        f"👥 **Приглашено друзей:** {referral_count}\n"
        f"💰 **Получено бонусов:** {referral_count * REFERRAL_BONUS:,} монет\n\n"
        f"🔗 **Твоя ссылка:**\n`{ref_link}`\n\n"
        f"📱 **Отправь эту ссылку друзьям**\n"
        f"💎 **За каждого друга +{REFERRAL_BONUS:,} монет**\n\n"
        f"✨ Чем больше друзей, тем больше бонусов!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'no')
async def no(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "❌ НАЖАЛ НЕТ")
    await callback.message.edit_text("😕 Окей, если не хочешь, то как хочешь)\nЕсли передумаешь, пиши /start")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'yes')
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

@dp.callback_query_handler(lambda c: c.data == 'subscribe_first')
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

@dp.callback_query_handler(lambda c: c.data == 'check_sub')
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
            "❓ **ПОМОЩЬ** - помощь\n"
            "🎉 **ДРУЗЬЯ** - пригласить друзей и получить бонус",
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

@dp.callback_query_handler(lambda c: c.data == 'reviews')
async def reviews_button(callback: CallbackQuery, state: FSMContext):
    username = callback.from_user.first_name
    user_id = callback.from_user.id
    log_user_action(username, "📝 НАЖАЛ ОТЗЫВЫ")
    if is_reviewed(user_id):
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

@dp.callback_query_handler(lambda c: c.data == 'help')
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

@dp.callback_query_handler(lambda c: c.data == 'task')
async def task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    chat_id = callback.message.chat.id
    
    user_data = get_user_data(user_id)
    if not can_do_task(user_id):
        time_left = get_time_left(user_id)
        await remind_user_about_cooldown(user_id, chat_id)
        await callback.answer(
            f"⏳ Подожди {time_left} до следующего задания!", 
            show_alert=True
        )
        return
    
    log_user_action(username, "📋 ВЗЯЛ ЗАДАНИЕ")
    log_success(f"✅ {username} ВЗЯЛ ЗАДАНИЕ")
    
    await callback.message.edit_text(
        "📋 **Твоё задание:**\n\n"
        "1️⃣ Зайди на сервер\n"
        "2️⃣ Напиши в чат: !Кому нужна валюта заходим в тг бота @HolyBuxBot_Bot\n"
        "3️⃣ Сделай скриншот\n"
        "4️⃣ Отправь скриншот сюда\n\n"
        f"💰 Награда: {REWARD_AMOUNT:,} монет\n\n"
        "⚠️ **ВНИМАНИЕ!**\n"
        "❌ НЕ ВЗДУМАЙ ХИТРИТЬ!\n"
        "❌ ЕСЛИ ТЫ УЖЕ ДЕЛАЛ ЗАДАНИЕ - ДЕЛАЙ ЗАНОВО!\n"
        "❌ КИДАЙ НОВЫЙ СКРИНШОТ!\n\n"
        "🚫 **ЕСЛИ АДМИН ЗАМЕТИТ ПОВТОРНЫЙ СКРИНШОТ/ФОТО - ТЫ ПОЛУЧИШЬ БАН НАВСЕГДА!**"
    )
    await callback.message.answer("📸 **Отправь скриншот:**", parse_mode="Markdown")
    await state.set_state(States.waiting_photo)
    await callback.answer()

@dp.message_handler(content_types=['photo'], state=States.waiting_photo)
async def get_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    name = message.from_user.full_name
    photo_id = message.photo[-1].file_id
    
    log_user_action(username, "📸 ОТПРАВИЛ СКРИНШОТ")
    log_info(f"🆔 ID фото: {photo_id}")
    
    # Проверяем на повторный скриншот
    response = supabase.table('users').select('screenshots').eq('user_id', user_id).execute()
    screenshots = response.data[0].get('screenshots', []) if response.data else []
    
    if photo_id in screenshots:
        log_warning(f"⚠️ {username} ОТПРАВИЛ ПОВТОРНЫЙ СКРИНШОТ!")
        await message.answer(
            "❌ **ОБНАРУЖЕН ПОВТОРНЫЙ СКРИНШОТ!**\n\n"
            "🚫 Ты пытаешься отправить тот же самый скриншот!\n"
            "⚠️ Администратор уже получил уведомление о нарушении.\n\n"
            "📋 **Сделай новое задание и отправь СВЕЖИЙ скриншот!**"
        )
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 **ПОПЫТКА ОБМАНА!**\n\n"
                f"👤 Пользователь: {name}\n"
                f"🆔 ID: {user_id}\n"
                f"📱 Username: @{message.from_user.username or 'Нет'}\n\n"
                f"❌ Отправил ПОВТОРНЫЙ скриншот!"
            )
        except:
            pass
        await state.finish()
        return
    
    # Сохраняем скриншот
    add_screenshot(user_id, photo_id)
    
    await message.answer("✅ **Скриншот отправлен на проверку!**", parse_mode="Markdown")
    log_success(f"✅ Скриншот от {username} отправлен админу")
    
    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=f"Новый скриншот от {name} (ID: {user_id})",
            reply_markup=admin_screenshot_keyboard(user_id)
        )
        log_success(f"✅ Фото доставлено админу")
    except Exception as e:
        log_error(f"❌ Ошибка отправки админу: {e}")
        await message.answer("⚠️ Ошибка при отправке админу")
    
    await state.finish()

@dp.message_handler(state=States.waiting_photo)
async def not_photo(message: Message):
    username = message.from_user.first_name
    log_warning(f"⚠️ {username} ОТПРАВИЛ НЕ ФОТО")
    await message.answer("❌ **Отправь фото, а не текст!**\n\n📸 Сделай скриншот задания и отправь его как фото.", parse_mode="Markdown")

@dp.message_handler(state=States.waiting_review)
async def handle_review(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.first_name
    user_tag = message.from_user.username or "Нет username"
    review_text = message.text
    
    if is_reviewed(user_id):
        await message.answer(
            "❌ **Вы уже оставляли отзыв!**\n\nСпасибо за ваше мнение, но можно оставить только один отзыв.",
            parse_mode="Markdown"
        )
        await state.finish()
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
        set_reviewed(user_id)
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
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'balance')
async def balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    
    log_user_action(username, f"💰 ПРОВЕРИЛ БАЛАНС")
    
    if can_do_task(user_id):
        task_status = "✅ Доступно"
    else:
        task_status = f"⏳ Через {get_time_left(user_id)}"
    
    response = supabase.table('users').select('referrals').eq('user_id', user_id).execute()
    referral_count = len(response.data[0].get('referrals', [])) if response.data else 0
    
    await callback.message.answer(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"💎 **Монет:** {user_data['balance']:,}\n"
        f"📊 **Задание:** {task_status}\n"
        f"👥 **Рефералов:** {referral_count}\n"
        f"🎁 **Бонус за рефералов:** {referral_count * REFERRAL_BONUS:,}\n\n"
        f"📢 **Канал:** {CHANNEL_ID}\n"
        f"📝 **Отзывы:** {REVIEW_CHANNEL_ID}",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'withdraw_menu')
async def withdraw_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    log_user_action(username, "💸 ОТКРЫЛ МЕНЮ ВЫВОДА")
    if user_data['balance'] <= 0:
        await callback.answer("❌ У тебя нет монет для вывода! Выполни задание.", show_alert=True)
        return
    await callback.message.edit_text(
        f"💸 **Меню вывода средств**\n\n"
        f"💰 **Твой баланс:** {user_data['balance']:,} монет\n\n"
        f"Выбери действие:",
        reply_markup=withdraw_menu_keyboard(user_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def back_to_menu(callback: CallbackQuery):
    username = callback.from_user.first_name
    log_user_action(username, "🔙 ВЕРНУЛСЯ В ГЛАВНОЕ МЕНЮ")
    await callback.message.edit_text(
        "✅ **Выбирай что нужно:**",
        reply_markup=menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'withdraw_all')
async def withdraw_all(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    user_data = get_user_data(user_id)
    amount = user_data['balance']
    
    log_user_action(username, f"💸 ХОЧЕТ ВЫВЕСТИ {amount:,} монет")
    if amount <= 0:
        await callback.answer("❌ Нет монет для вывода!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"💸 **Вывод средств**\n\n"
        f"💰 **Сумма к выводу:** {amount:,} монет\n\n"
        f"📝 **Инструкция:**\n"
        f"1️⃣ Зайди на сервер **HolyTime**\n"
        f"2️⃣ Выставь на аукцион предмет за **{amount:,} монет**\n"
        f"3️⃣ Напиши сюда свой **никнейм**\n\n"
        f"✍️ **Введи свой никнейм:**",
        parse_mode="Markdown"
    )
    await state.set_state(States.waiting_nickname)

@dp.message_handler(state=States.waiting_nickname)
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
    
    update_last_task(user_id, time.time())
    
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
    await state.finish()

# ===== АДМИН ФУНКЦИИ =====
@dp.callback_query_handler(lambda c: c.data.startswith('ok_'))
async def approve_screenshot(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        log_warning(f"⚠️ Попытка подтверждения не админом: {callback.from_user.first_name}")
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    add_balance(user_id, REWARD_AMOUNT)
    update_last_task(user_id, time.time())
    log_big_title(f"АДМИН ПОДТВЕРДИЛ СКРИНШОТ")
    log_action(f"👑 Админ подтвердил скриншот пользователя ID:{user_id}")
    log_success(f"💰 Начислено {REWARD_AMOUNT:,} монет")
    try:
        withdraw_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 ВЫВЕСТИ СРЕДСТВА", callback_data="withdraw_menu")]
        ])
        
        user_data = get_user_data(user_id)
        await bot.send_message(
            user_id,
            f"✅ **Админ {ADMIN_USERNAME}** подтвердил ваш скриншот!\n\n"
            f"🎉 **+{REWARD_AMOUNT:,} монет** зачислено на баланс!\n"
            f"💰 **Текущий баланс:** {user_data['balance']:,} монет\n\n"
            f"💸 **Теперь вы можете вывести свои средства, нажав на кнопку ниже**",
            parse_mode="Markdown",
            reply_markup=withdraw_keyboard
        )
        log_success(f"✅ Уведомление с кнопкой вывода отправлено пользователю")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление пользователю: {e}")
    await callback.message.delete()
    await callback.answer("Готово!")

@dp.callback_query_handler(lambda c: c.data.startswith('no_'))
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

# ===== ИСПРАВЛЕННЫЕ КНОПКИ КУПИЛ/НЕ КУПИЛ =====
@dp.callback_query_handler(lambda c: c.data.startswith('bought_'))
async def bought(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    
    user_data = get_user_data(user_id)
    old_balance = user_data['balance']
    
    # Обнуляем баланс
    supabase.table('users').update({'balance': 0}).eq('user_id', user_id).execute()
    
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
        log_success(f"✅ Уведомление о покупке отправлено пользователю {user_id}")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление: {e}")
    
    await callback.message.delete()
    await callback.answer("✅ Готово! Сообщение удалено")

@dp.callback_query_handler(lambda c: c.data.startswith('not_bought_'))
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
            "💰 **Ваш баланс сохранен.** Попробуйте еще раз.\n\n"
            "💸 **Для повторной попытки нажмите кнопку ВЫВОД в меню**",
            parse_mode="Markdown"
        )
        log_success(f"✅ Уведомление об отказе отправлено пользователю {user_id}")
    except Exception as e:
        log_error(f"❌ Не удалось отправить уведомление: {e}")
    
    await callback.message.delete()
    await callback.answer("✅ Готово! Сообщение удалено")

@dp.message_handler()
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

def can_do_task(user_id):
    user_data = get_user_data(user_id)
    return (time.time() - user_data['last_task_time']) >= COOLDOWN_SECONDS

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start_bot():
    print(f"{Colors.BOLD}{Colors.PURPLE}╔══════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║                      🚀 БОТ ЗАПУЩЕН 🚀                       ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}╠══════════════════════════════════════════════════════════════╣{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 📢 Канал: {Colors.CYAN}{CHANNEL_ID}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 📝 Канал отзывов: {Colors.PINK}{REVIEW_CHANNEL_ID}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 👤 Админ: {Colors.GREEN}{ADMIN_USERNAME}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 💰 Награда: {Colors.YELLOW}{REWARD_AMOUNT:,}{Colors.END} монет ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} ⏱ Кулдаун: {Colors.YELLOW}{COOLDOWN_SECONDS//3600} час{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 💰 Бонус за друга: {Colors.YELLOW}{REFERRAL_BONUS:,}{Colors.END} монет ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} ⏰ Время запуска: {Colors.YELLOW}{current_datetime()}{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}║{Colors.END} 🔄 Автообновление: {Colors.GREEN}КАЖДЫЕ 3 МИНУТЫ{Colors.END} ")
    print(f"{Colors.BOLD}{Colors.PURPLE}╚══════════════════════════════════════════════════════════════╝{Colors.END}")
    print("")
    log_system("🟢 Бот готов к работе! Ожидаю пользователей...")
    print("")
    await dp.start_polling()

# ===== ТОЧКА ВХОДА =====
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    
    from multiprocessing import Process
    
    def run_web():
        web.run_app(app, host='0.0.0.0', port=port)
    
    web_process = Process(target=run_web, daemon=True)
    web_process.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log_warning("⏹ Бот остановлен пользователем")
        web_process.terminate()
        print(f"{Colors.BOLD}{Colors.PURPLE}До свидания! Бот завершил работу.{Colors.END}")
    except Exception as e:
        log_error(f"❌ Критическая ошибка: {e}")
        web_process.terminate()
