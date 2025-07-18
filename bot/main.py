import asyncio
import logging
import datetime
import calendar

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InputMediaPhoto, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config_manager
import db_utils

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# ЗАГРУЗКА НАСТРОЕК ИЗ config_manager
BOT_TOKEN = config_manager.get_setting('BOT_TOKEN')
ADMIN_USERNAME = config_manager.get_setting('ADMIN_USERNAME')
PHOTO_URLS = config_manager.get_setting('PHOTO_URLS', [])

# Инициализация объекта Bot и Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
admin_router = Router()
booking_router = Router()

# Регистрируем роутеры в основном диспетчере
dp.include_router(admin_router)
dp.include_router(booking_router)

# --- FSM States for Admin Panel ---
class AdminState(StatesGroup):
    waiting_for_password = State()
    in_admin_panel = State()

    # Category management states
    manage_categories = State()
    add_category_slug = State()
    add_category_title = State()
    add_category_parent = State()
    edit_category_select = State()
    edit_category_new_title = State()
    delete_category_select = State()

    # Service management states
    manage_services = State()
    select_category_for_service = State()

    add_service_name = State()
    add_service_price = State()
    add_service_description = State()

    edit_service_select = State()
    edit_service_choose_field = State()
    edit_service_new_value = State()
    editing_service_data = State()

    delete_service_select = State()

    # State for admin viewing public services
    viewing_public_services_mode = State()

    # State for changing admin password
    change_password_waiting_for_new_password = State()


# --- FSM States для системы записи клиентов ---
class BookingState(StatesGroup):
    choosing_category = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_comment = State()
    entering_phone = State()
    confirming_booking = State()


# --- Вспомогательная функция для отправки главного меню ---
async def send_main_menu(target: types.Message | types.CallbackQuery):
    """
    Отправляет или редактирует сообщение с главным меню.
    Принимает объект Message (для /start) или CallbackQuery (для кнопки "Назад").
    """
    user_first_name = target.from_user.first_name

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✨ Наши услуги", callback_data="show_services_main_menu")],
            [types.InlineKeyboardButton(text="📸 Фотографии салона", callback_data="show_salon_photos")],
            [types.InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [types.InlineKeyboardButton(text="🗓️ Мои записи", callback_data="show_my_bookings")],
            [types.InlineKeyboardButton(text="📍 Как до нас добраться?", url="https://yandex.ru/maps/54/yekaterinburg/?from=api-maps&ll=60.607417%2C56.855225&mode=routes&origin=jsapi_2_1_79&rtext=~56.855225%2C60.607417&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D176318285490&z=13.89")],
            [types.InlineKeyboardButton(text="💌 Связаться с администратором",
                                        url=f"tg://resolve?domain={ADMIN_USERNAME}")],

        ]
    )

    welcome_message = (
        f"Привет, {user_first_name}! 👋\n\n"
        "Добро пожаловать в салон красоты \"Shade\"!\n"
        "Мы рады предложить вам широкий спектр услуг для вашей красоты и здоровья.\n"
        "Выберите интересующий раздел ниже, чтобы узнать больше:"
    )

    if isinstance(target, types.Message):
        await target.answer(welcome_message, reply_markup=markup)
    elif isinstance(target, types.CallbackQuery):
        if target.message.text:
            try:
                await target.message.edit_text(welcome_message, reply_markup=markup)
            except Exception: # Если сообщение уже изменено или удалено
                await target.message.answer(welcome_message, reply_markup=markup)
        else: # Если callback.message был от медиа группы, у него нет текста
            await target.message.answer(welcome_message, reply_markup=markup)


# --- ОБРАБОТЧИКИ КОМАНД И КНОПОК ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик команды /start. Отправляет приветственное сообщение с инлайн-кнопками.
    """
    await state.clear()
    await send_main_menu(message)


@dp.callback_query(F.data == "show_services_main_menu")
async def process_services_main_menu_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Наши услуги".
    Показывает основные категории услуг, получая их из БД.
    """
    await callback.answer(text="Загрузка категорий услуг...", show_alert=False)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])

    main_categories = db_utils.get_main_categories()

    for category in main_categories:
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text=f"✨ {category['title']}", callback_data=f"cat::{category['slug']}")
        ])

    markup.inline_keyboard.append([
        types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    ])

    await callback.message.edit_text(
        "<b>💎 Наши услуги:</b>\n"
        "Выберите интересующую категорию:",
        reply_markup=markup
    )


@dp.callback_query(F.data.startswith("cat::"))
async def process_service_category_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку категории услуг.
    Либо показывает подкатегории, либо выводит список услуг, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    category_slug = callback.data.split("::")[1]

    current_category = db_utils.get_category_by_slug(category_slug)
    if not current_category:
        await callback.message.answer("Извините, информация по данной категории не найдена.")
        await send_main_menu(callback)
        return

    subcategories = db_utils.get_subcategories(category_slug)

    if subcategories:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[])
        for sub_data in subcategories:
            markup.inline_keyboard.append([
                types.InlineKeyboardButton(text=f"▪️ {sub_data['title']}",
                                           callback_data=f"sub::{category_slug}::{sub_data['slug']}")
            ])
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг", callback_data="show_services_main_menu")
        ])

        await callback.message.edit_text(
            f"<b>{current_category['title']}:</b>\n"
            "Выберите подкатегорию:",
            reply_markup=markup
        )
    else:
        services = db_utils.get_services_by_category_slug(category_slug)

        service_text = f"<b>{current_category['title']}:</b>\n\n"
        if services:
            for item in services:
                service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
                if "description" in item:
                    service_text += f"   <i>{item['description']}</i>\n"
        else:
            service_text += "Услуги в данной категории пока отсутствуют."

        markup = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг",
                                            callback_data="show_services_main_menu")],
            ]
        )
        await callback.message.edit_text(service_text, reply_markup=markup)


@dp.callback_query(F.data.startswith("sub::"))
async def process_service_subcategory_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку подкатегории услуг.
    Выводит список услуг для этой подкатегории, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    parts = callback.data.split('::')

    if len(parts) < 3:
        await callback.message.answer("Извините, некорректные данные подкатегории.")
        await send_main_menu(callback)
        return

    parent_category_slug = parts[1]
    subcategory_slug = parts[2]

    subcategory_data = db_utils.get_category_by_slug(subcategory_slug)

    if not subcategory_data:
        await callback.message.answer("Извините, информация по данной подкатегории не найдена.")
        await send_main_menu(callback)
        return

    services = db_utils.get_services_by_category_slug(subcategory_slug)

    service_text = f"<b>{subcategory_data['title']}:</b>\n\n"
    if services:
        for item in services:
            service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
            if "description" in item:
                service_text += f"   <i>{item['description']}</i>\n"
    else:
        service_text += "Услуги в данной подкатегории пока отсутствуют."

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад к подкатегориям", callback_data=f"cat::{parent_category_slug}")],
        ]
    )
    await callback.message.edit_text(service_text, reply_markup=markup)


@dp.callback_query(F.data == "show_salon_photos")
async def process_photos_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Фотографии салона". Отправляет фото.
    """
    await callback.answer(text="Загрузка фотографий...")
    media_group = []

    for url in PHOTO_URLS:
        media_group.append(InputMediaPhoto(media=url))

    try:
        await callback.message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение перед отправкой фото: {e}")

    await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )
    await callback.message.answer(
        "Надеемся, вам понравились фотографии нашего салона! ✨",
        reply_markup=markup
    )


@dp.callback_query(F.data == "back_to_main_menu", ~StateFilter(AdminState, BookingState))
async def process_back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на кнопку "Назад в главное меню" для ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ.
    Не срабатывает, если пользователь находится в любом админском или любом состоянии записи FSM.
    """
    await state.clear()
    await callback.answer()
    await send_main_menu(callback)


# --- БЛОК: Мои записи ---
@dp.callback_query(F.data == "show_my_bookings")
async def show_my_bookings(callback: types.CallbackQuery):
    await callback.answer("Загружаю ваши записи...", show_alert=False)
    user_id = callback.from_user.id
    bookings = db_utils.get_user_bookings(user_id)

    if not bookings:
        message_text = "У вас пока нет активных записей. Хотите записаться?"
    else:
        message_text = "<b>Ваши предстоящие записи:</b>\n\n"
        for i, booking in enumerate(bookings):
            # Форматируем дату для более читаемого вида
            formatted_date = datetime.datetime.strptime(booking['booking_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            message_text += (
                f"Запись №{i+1}:\n"
                f"  📅 Дата: <b>{formatted_date}</b>\n"
                f"  ⏰ Время: <b>{booking['booking_time']}</b>\n"
                f"  💅 Услуга: <b>{booking['service_name']}</b> (Категория: {booking['category_name']})\n"
                f"  💬 Комментарий: <i>{booking['comment'] if booking['comment'] else 'нет'}</i>\n"
                f"  📞 Ваш номер: <code>{booking['user_phone']}</code>\n\n"
            )

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )
    await callback.message.edit_text(message_text, reply_markup=markup)


# --- БЛОК: Функционал записи клиентов ---

@booking_router.callback_query(F.data == "start_booking")
async def booking_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Начинаем запись...", show_alert=False)
    await state.clear() # Очищаем предыдущие данные записи

    markup = InlineKeyboardBuilder()
    main_categories = db_utils.get_main_categories()

    if not main_categories:
        await callback.message.edit_text("Извините, пока нет доступных категорий услуг для записи. Пожалуйста, попробуйте позже.",
                                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                             [types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")]
                                         ]))
        await state.clear()
        return

    for category in main_categories:
        markup.button(text=f"✨ {category['title']}", callback_data=f"book_cat::{category['slug']}")

    markup.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu"))
    await callback.message.edit_text("<b>📝 Запись на услугу:</b>\nВыберите категорию услуги:", reply_markup=markup.as_markup())
    await state.set_state(BookingState.choosing_category)


@booking_router.callback_query(F.data.startswith("book_cat::"), BookingState.choosing_category)
async def booking_choose_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Загружаю услуги...", show_alert=False)
    category_slug = callback.data.split("::")[1]
    current_category = db_utils.get_category_by_slug(category_slug)

    if not current_category:
        await callback.message.edit_text("Категория не найдена. Пожалуйста, выберите другую.",
                                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                             [types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="start_booking")]
                                         ]))
        return

    # Сохраняем текущий slug категории для удобства возврата
    await state.update_data(current_booking_category_slug=category_slug)

    subcategories = db_utils.get_subcategories(category_slug)
    if subcategories:
        markup = InlineKeyboardBuilder()
        for sub_data in subcategories:
            markup.button(text=f"▪️ {sub_data['title']}", callback_data=f"book_sub::{category_slug}::{sub_data['slug']}")
        markup.row(types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="start_booking"))
        await callback.message.edit_text(f"<b>{current_category['title']}:</b>\nВыберите подкатегорию:", reply_markup=markup.as_markup())
        # Состояние остается choosing_category, пока не выберем конкретную услугу
        # await state.set_state(BookingState.choosing_category)
    else:
        # Если подкатегорий нет, сразу показываем услуги из этой категории
        await _send_services_for_booking(callback, state, category_slug, "start_booking") # Возврат к началу выбора категории


@booking_router.callback_query(F.data.startswith("book_sub::"), BookingState.choosing_category)
async def booking_choose_subcategory(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Загружаю услуги...", show_alert=False)
    parts = callback.data.split("::")
    parent_category_slug = parts[1] # Для кнопки "Назад"
    subcategory_slug = parts[2]
    # Сохраняем текущий slug подкатегории для удобства возврата
    await state.update_data(current_booking_category_slug=subcategory_slug, parent_category_slug_for_booking=parent_category_slug)
    await _send_services_for_booking(callback, state, subcategory_slug, f"book_cat::{parent_category_slug}")


async def _send_services_for_booking(callback: types.CallbackQuery, state: FSMContext, category_slug: str, back_callback_data: str):
    """Вспомогательная функция для отправки списка услуг для выбора записи."""
    services = db_utils.get_services_by_category_slug(category_slug)
    category_title = db_utils.get_category_by_slug(category_slug)['title']

    if not services:
        await callback.message.edit_text(f"В категории <b>'{category_title}'</b> пока нет услуг для записи.",
                                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                             [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data)]
                                         ]))
        return

    markup = InlineKeyboardBuilder()
    text = f"<b>{category_title}:</b>\nВыберите услугу для записи:\n\n"
    for svc in services:
        markup.button(text=f"✨ {svc['name']} - {svc['price']}", callback_data=f"book_svc::{svc['id']}")
        text += f"▪️ <b>{svc['name']}</b> - {svc['price']}\n"
        if svc.get('description'):
            text += f"   <i>{svc['description']}</i>\n"

    markup.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data))
    await callback.message.edit_text(text, reply_markup=markup.as_markup())
    await state.set_state(BookingState.choosing_service)


@booking_router.callback_query(F.data.startswith("book_svc::"), BookingState.choosing_service)
async def booking_select_service(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Выбрана услуга...", show_alert=False)
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)

    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.",
                                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                             [types.InlineKeyboardButton(text="⬅️ Назад к выбору услуг", callback_data="start_booking")]
                                         ]))
        return

    await state.update_data(chosen_service_id=service_id, chosen_service_name=service['name'],
                            chosen_service_category_slug=service['category_slug']) # Сохраняем для возврата

    await callback.message.edit_text(f"Вы выбрали услугу: <b>{service['name']}</b>. \n\nТеперь выберите желаемую дату:",
                                     reply_markup=await create_calendar_markup())
    await state.set_state(BookingState.choosing_date)


# --- Функции для календаря ---
async def create_calendar_markup(year: int = None, month: int = None):
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    cal = calendar.Calendar()
    month_days = cal.monthdayscalendar(year, month)

    markup = InlineKeyboardBuilder()

    # Заголовок: месяц и год
    markup.row(types.InlineKeyboardButton(text=f"{calendar.month_name[month]} {year}", callback_data="ignore_calendar"))

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[types.InlineKeyboardButton(text=day, callback_data="ignore_calendar") for day in week_days])

    # Дни месяца
    for week in month_days:
        row_buttons = []
        for day in week:
            if day == 0: # Пустые ячейки (дни из предыдущего/следующего месяца)
                row_buttons.append(types.InlineKeyboardButton(text=" ", callback_data="ignore_calendar"))
            else:
                current_date = datetime.date(year, month, day)
                # Проверяем, не прошла ли дата
                if current_date < now.date():
                    row_buttons.append(types.InlineKeyboardButton(text=str(day), callback_data="ignore_calendar")) # Неактивная кнопка
                else:
                    row_buttons.append(types.InlineKeyboardButton(text=str(day), callback_data=f"cal_day::{current_date.strftime('%Y-%m-%d')}"))
        markup.row(*row_buttons)

    # Кнопки навигации по месяцам
    prev_month_date = (datetime.date(year, month, 1) - datetime.timedelta(days=1))
    next_month_date = (datetime.date(year, month, 1) + datetime.timedelta(days=32))

    markup.row(
        types.InlineKeyboardButton(text="⬅️", callback_data=f"cal_nav::{prev_month_date.year}::{prev_month_date.month}"),
        types.InlineKeyboardButton(text="➡️", callback_data=f"cal_nav::{next_month_date.year}::{next_month_date.month}")
    )
    markup.row(types.InlineKeyboardButton(text="⬅️ Назад к выбору услуги", callback_data="book_back_to_service_selection"))
    return markup.as_markup()

@booking_router.callback_query(F.data.startswith("cal_nav::"), BookingState.choosing_date)
async def process_calendar_navigation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(show_alert=False)
    parts = callback.data.split("::")
    year = int(parts[1])
    month = int(parts[2])
    await callback.message.edit_reply_markup(reply_markup=await create_calendar_markup(year, month))

@booking_router.callback_query(F.data == "ignore_calendar", BookingState.choosing_date)
async def ignore_calendar_callback(callback: types.CallbackQuery):
    await callback.answer(show_alert=False) # Просто игнорируем нажатие на дни недели или пустые ячейки

@booking_router.callback_query(F.data == "book_back_to_service_selection", BookingState.choosing_date)
async def book_back_to_service_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору услуги...", show_alert=False)
    data = await state.get_data()
    chosen_service_category_slug = data.get('chosen_service_category_slug')

    if chosen_service_category_slug:
        # Пытаемся вернуться к списку услуг в той же категории
        await _send_services_for_booking(callback, state, chosen_service_category_slug, "start_booking")
    else:
        # Если почему-то нет slug, возвращаемся к началу выбора категорий для записи
        await booking_start(callback, state)


@booking_router.callback_query(F.data.startswith("cal_day::"), BookingState.choosing_date)
async def booking_select_date(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Выбрана дата...", show_alert=False)
    chosen_date_str = callback.data.split("::")[1]
    chosen_date = datetime.datetime.strptime(chosen_date_str, '%Y-%m-%d').date()

    await state.update_data(chosen_date=chosen_date_str)

    await callback.message.edit_text(f"Выбрана дата: <b>{chosen_date.strftime('%d.%m.%Y')}</b>. \nТеперь выберите желаемое время:",
                                     reply_markup=await create_time_slots_markup(state))
    await state.set_state(BookingState.choosing_time)


# --- Функции для выбора времени ---
async def create_time_slots_markup(state: FSMContext):
    data = await state.get_data()
    chosen_date_str = data.get('chosen_date')
    chosen_service_id = data.get('chosen_service_id')

    if not chosen_date_str or not chosen_service_id:
        logging.error("Chosen date or service ID not found in FSM context for time slot generation.")
        # Предлагаем вернуться к выбору даты, чтобы восстановить контекст
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Ошибка: Вернуться к выбору даты", callback_data="book_back_to_date_selection")]
        ])

    booked_times = db_utils.get_booked_slots_for_date_service(chosen_date_str, chosen_service_id)
    all_slots = []
    # Салон работает с 9:00 до 20:00, интервал 30 минут
    start_hour = 9
    end_hour = 20 # Заканчиваем в 20:00, последний слот будет 19:30
    interval_minutes = 30

    current_time_dt = datetime.datetime.now()
    today_str = current_time_dt.strftime('%Y-%m-%d')


    for hour in range(start_hour, end_hour):
        for minute_step in range(0, 60, interval_minutes):
            slot_time = datetime.time(hour, minute_step)
            slot_str = slot_time.strftime('%H:%M')

            # Учитываем, что последний слот может быть 19:30, а салон работает до 20:00.
            # Если хотим, чтобы 20:00 было последним доступным временем для начала, то end_hour = 21 и 0 минут.
            # Для простоты, оставим так, как будто последний сеанс начинается в 19:30.
            # Если 20:00 - это время ЗАКРЫТИЯ, а не начала последнего сеанса, то end_hour = 20, а последний сеанс,
            # который может начаться, например, 19:30, если сеанс 30 минут.

            # Проверяем, если текущая дата и текущий час/минута
            is_past = False
            if chosen_date_str == today_str:
                combined_dt = datetime.datetime.combine(current_time_dt.date(), slot_time)
                if combined_dt < current_time_dt:
                    is_past = True

            # Убеждаемся, что не добавляем слоты, если они уже прошли, или забронированы.
            if not is_past and slot_str not in booked_times:
                all_slots.append(slot_str)


    markup = InlineKeyboardBuilder()
    row_buttons = []
    if not all_slots:
        # Если нет доступных слотов, добавляем сообщение
        markup.row(types.InlineKeyboardButton(text="На эту дату нет свободных временных слотов. Выберите другую дату.", callback_data="ignore_time_slot"))
    else:
        for slot in all_slots:
            button = types.InlineKeyboardButton(text=slot, callback_data=f"book_time::{slot}")
            row_buttons.append(button)
            if len(row_buttons) == 4: # По 4 кнопки в ряд
                markup.row(*row_buttons)
                row_buttons = []
        if row_buttons: # Добавляем оставшиеся кнопки
            markup.row(*row_buttons)

    markup.row(types.InlineKeyboardButton(text="⬅️ Назад к выбору даты", callback_data="book_back_to_date_selection"))
    return markup.as_markup()

@booking_router.callback_query(F.data == "ignore_time_slot", BookingState.choosing_time)
async def ignore_time_slot_callback(callback: types.CallbackQuery):
    await callback.answer("Это время занято или недоступно. Выберите другое.", show_alert=True)

@booking_router.callback_query(F.data == "book_back_to_date_selection", BookingState.choosing_time)
async def book_back_to_date_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору даты...", show_alert=False)
    await callback.message.edit_text("Теперь выберите желаемую дату:",
                                     reply_markup=await create_calendar_markup())
    await state.set_state(BookingState.choosing_date)


@booking_router.callback_query(F.data.startswith("book_time::"), BookingState.choosing_time)
async def booking_select_time(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Выбрано время...", show_alert=False)
    chosen_time_str = callback.data.split("::")[1]
    await state.update_data(chosen_time=chosen_time_str)

    await callback.message.edit_text(f"Вы выбрали время: <b>{chosen_time_str}</b>. \n\n"
                                     "Оставьте комментарий к записи (например, особенности, пожелания). "
                                     "Если комментарий не нужен, просто напишите `-` или `нет`:",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="⬅️ Назад к выбору времени", callback_data="book_back_to_time_selection")]
                                     ]))
    await state.set_state(BookingState.entering_comment)

@booking_router.callback_query(F.data == "book_back_to_time_selection", BookingState.entering_comment)
async def book_back_to_time_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору времени...", show_alert=False)
    await callback.message.edit_text("Теперь выберите желаемое время:",
                                     reply_markup=await create_time_slots_markup(state))
    await state.set_state(BookingState.choosing_time)

@booking_router.message(BookingState.entering_comment)
async def booking_enter_comment(message: types.Message, state: FSMContext):
    comment = message.text.strip()
    if comment.lower() in ["-", "нет", "none", "n/a", "no"]:
        comment = None
    await state.update_data(comment=comment)

    # Клавиатура для запроса номера телефона
    request_phone_markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Поделиться номером телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Теперь, пожалуйста, укажите ваш номер телефона. "
                         "Вы можете нажать кнопку 'Поделиться номером телефона' ниже или ввести его вручную:",
                         reply_markup=request_phone_markup)
    await state.set_state(BookingState.entering_phone)


@booking_router.message(BookingState.entering_phone, F.contact)
async def booking_get_phone_from_contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone=phone_number)
    await _confirm_booking(message, state) # Переходим к подтверждению


@booking_router.message(BookingState.entering_phone)
async def booking_enter_phone_manually(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    # Простая валидация номера телефона (можно улучшить регулярными выражениями)
    # Например: import re; if not re.match(r"^\+?\d{10,15}$", phone_number):
    if not (phone_number.startswith('+') and phone_number[1:].isdigit() and len(phone_number) > 8) and not (phone_number.isdigit() and len(phone_number) >= 10):
        await message.answer("Пожалуйста, введите корректный номер телефона (например, +79XXXXXXXXX или 89XXXXXXXXX):",
                             reply_markup=types.ReplyKeyboardRemove()) # Убираем reply-клавиатуру
        return
    await state.update_data(phone=phone_number)
    await _confirm_booking(message, state) # Переходим к подтверждению

async def _confirm_booking(message: types.Message, state: FSMContext):
    data = await state.get_data()
    service_name = data.get('chosen_service_name', 'Неизвестная услуга')
    chosen_date_str = data.get('chosen_date', 'Не выбрана')
    chosen_time_str = data.get('chosen_time', 'Не выбрано')
    comment = data.get('comment', 'Нет')
    phone = data.get('phone', 'Не указан')

    # Убираем клавиатуру "Поделиться номером"
    # Это может быть проблематично, если сообщение с клавиатурой не то, которое нужно редактировать.
    # Лучше отправить новое сообщение и убрать клавиатуру.
    if message.reply_markup and isinstance(message.reply_markup, types.ReplyKeyboardMarkup):
        await message.answer("...", reply_markup=types.ReplyKeyboardRemove())
        await message.delete() # Удаляем старое сообщение с reply-клавиатурой, если хотим

    summary_text = (
        "<b>Ваша запись:</b>\n\n"
        f"💅 Услуга: <b>{service_name}</b>\n"
        f"📅 Дата: <b>{datetime.datetime.strptime(chosen_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Время: <b>{chosen_time_str}</b>\n"
        f"💬 Комментарий: <i>{comment if comment else 'нет'}</i>\n"
        f"📞 Ваш номер: <code>{phone}</code>\n\n"
        "Все верно?"
    )

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="booking_confirm")],
        [types.InlineKeyboardButton(text="❌ Отменить и начать заново", callback_data="booking_cancel")]
    ])
    await message.answer(summary_text, reply_markup=markup)
    await state.set_state(BookingState.confirming_booking)


@booking_router.callback_query(F.data == "booking_confirm", BookingState.confirming_booking)
async def booking_final_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Подтверждаю запись...", show_alert=False)
    data = await state.get_data()

    user_id = callback.from_user.id
    phone = data.get('phone')
    service_id = data.get('chosen_service_id')
    booking_date = data.get('chosen_date')
    booking_time = data.get('chosen_time')
    comment = data.get('comment')

    if not all([user_id, phone, service_id, booking_date, booking_time]):
        await callback.message.edit_text("Ошибка при подтверждении записи. Пожалуйста, попробуйте начать заново.",
                                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                             [types.InlineKeyboardButton(text="📝 Начать запись заново", callback_data="start_booking")]
                                         ]))
        await state.clear()
        return

    success = db_utils.add_booking(user_id, phone, service_id, booking_date, booking_time, comment)

    if success:
        formatted_date = datetime.datetime.strptime(booking_date, '%Y-%m-%d').strftime('%d.%m.%Y')
        await callback.message.edit_text(
            f"🎉 Ваша запись на услугу <b>{data['chosen_service_name']}</b> на <b>{formatted_date}</b> в <b>{booking_time}</b> успешно создана!\n\n"
            "Скоро с вами свяжется администратор для уточнения деталей. Спасибо, что выбрали нас! ✨",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu")],
                [types.InlineKeyboardButton(text="🗓️ Мои записи", callback_data="show_my_bookings")]
            ])
        )
        # Отправка уведомления администратору
        admin_id = config_manager.get_setting('ADMIN_USERNAME_ID')
        if admin_id:
            admin_message = (
                "🔔 <b>НОВАЯ ЗАПИСЬ!</b>\n\n"
                f"Клиент: <a href='tg://user?id={user_id}'>{callback.from_user.full_name}</a>\n"
                f"Услуга: <b>{data['chosen_service_name']}</b>\n"
                f"Дата: <b>{formatted_date}</b>\n"
                f"Время: <b>{booking_time}</b>\n"
                f"Номер телефона: <code>{phone}</code>\n"
                f"Комментарий: <i>{comment if comment else 'нет'}</i>"
            )
            try:
                await bot.send_message(chat_id=admin_id, text=admin_message, parse_mode=ParseMode.HTML)
                logging.info(f"Уведомление о новой записи отправлено админу {admin_id}")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        else:
            logging.warning("ADMIN_USERNAME_ID не настроен. Уведомление о новой записи не отправлено админу.")


    else:
        await callback.message.edit_text(
            "Произошла ошибка при сохранении вашей записи. Пожалуйста, попробуйте еще раз или свяжитесь с администратором.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📝 Начать запись заново", callback_data="start_booking")],
                [types.InlineKeyboardButton(text="💌 Связаться с администратором", url=f"tg://resolve?domain={ADMIN_USERNAME}")]
            ])
        )

    await state.clear() # Очищаем состояние после завершения записи

@booking_router.callback_query(F.data == "booking_cancel", BookingState.confirming_booking)
async def booking_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Запись отменена.", show_alert=True)
    await state.clear()
    await callback.message.edit_text(
        "Запись отменена. Вы можете начать процесс записи заново в любое время.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [types.InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu")]
        ])
    )


# --- АДМИН-ПАНЕЛЬ ---
@admin_router.message(CommandStart(magic=F.args == "admin"))
@admin_router.message(F.text == "/admin")
async def cmd_admin(message: types.Message, state: FSMContext):
    """Начинает процесс входа в админ-панель."""
    await message.answer("Введите пароль для доступа к админ-панели:")
    await state.set_state(AdminState.waiting_for_password)

@admin_router.message(AdminState.waiting_for_password)
async def process_admin_password(message: types.Message, state: FSMContext):
    """Проверяет пароль и предоставляет доступ к админ-панели."""
    current_admin_password = config_manager.get_setting('ADMIN_PASSWORD')

    if message.text == current_admin_password:
        await message.answer("Добро пожаловать в админ-панель! Что хотите сделать?",
                             reply_markup=get_admin_main_markup())
        await state.set_state(AdminState.in_admin_panel)
    else:
        await message.answer("Неверный пароль. Попробуйте еще раз или нажмите /start для возврата в главное меню.")


def get_admin_main_markup():
    """Возвращает клавиатуру для главного меню админ-панели."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Управление категориями", callback_data="admin_manage_categories")],
            [types.InlineKeyboardButton(text="Управление услугами", callback_data="admin_manage_services")],
            [types.InlineKeyboardButton(text="Посмотреть услуги (как пользователь)", callback_data="admin_view_public_services")],
            [types.InlineKeyboardButton(text="Изменить пароль админа", callback_data="admin_change_password")],
            [types.InlineKeyboardButton(text="Выйти из админ-панели", callback_data="admin_exit")],
        ]
    )

@admin_router.callback_query(F.data == "admin_main_menu", StateFilter(
    AdminState.in_admin_panel,
    AdminState.manage_categories,
    AdminState.manage_services,
    AdminState.viewing_public_services_mode,
    AdminState.change_password_waiting_for_new_password,
    AdminState.add_category_slug, # Добавлены состояния для корректного возврата
    AdminState.add_category_title,
    AdminState.add_category_parent,
    AdminState.edit_category_select,
    AdminState.edit_category_new_title,
    AdminState.delete_category_select,
    AdminState.select_category_for_service,
    AdminState.add_service_name,
    AdminState.add_service_price,
    AdminState.add_service_description,
    AdminState.edit_service_select,
    AdminState.edit_service_choose_field,
    AdminState.edit_service_new_value,
    AdminState.delete_service_select
))
async def admin_main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата в главное меню админ-панели."""
    await callback.answer()
    await state.set_state(AdminState.in_admin_panel)
    await callback.message.edit_text("Добро пожаловать в админ-панель! Что хотите сделать?",
                                     reply_markup=get_admin_main_markup())

@admin_router.callback_query(F.data == "admin_exit", AdminState.in_admin_panel)
async def admin_exit_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выход из админ-панели."""
    await callback.answer("Вы вышли из админ-панели.", show_alert=True)
    await state.clear()
    await send_main_menu(callback)


# --- ОБРАБОТЧИКИ ДЛЯ ПРОСМОТРА УСЛУГ АДМИНОМ (как пользователь) ---
@admin_router.callback_query(F.data == "admin_view_public_services", StateFilter(AdminState.in_admin_panel, AdminState.viewing_public_services_mode))
async def admin_show_public_services_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на кнопку "Посмотреть услуги (как пользователь)" в админ-панели.
    Показывает основные категории услуг с возможностью вернуться в админку.
    """
    await callback.answer(text="Загрузка категорий услуг...", show_alert=False)
    await state.set_state(AdminState.viewing_public_services_mode)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    main_categories = db_utils.get_main_categories()

    for category in main_categories:
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text=f"✨ {category['title']}", callback_data=f"admin_view_cat::{category['slug']}")
        ])

    markup.inline_keyboard.append([
        types.InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_main_menu")
    ])

    await callback.message.edit_text(
        "<b>💎 Наши услуги (режим просмотра для админа):</b>\n"
        "Выберите интересующую категорию:",
        reply_markup=markup
    )


@admin_router.callback_query(F.data.startswith("admin_view_cat::"), AdminState.viewing_public_services_mode)
async def admin_view_service_category_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку категории услуг в режиме просмотра админом.
    Либо показывает подкатегории, либо выводит список услуг, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    category_slug = callback.data.split("::")[1]
    current_category = db_utils.get_category_by_slug(category_slug)
    if not current_category:
        await callback.message.answer("Извините, информация по данной категории не найдена.")
        await admin_show_public_services_main_menu(callback, None) # state=None потому что не используется
        return

    subcategories = db_utils.get_subcategories(category_slug)

    if subcategories:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[])
        for sub_data in subcategories:
            markup.inline_keyboard.append([
                types.InlineKeyboardButton(text=f"▪️ {sub_data['title']}",
                                           callback_data=f"admin_view_sub::{category_slug}::{sub_data['slug']}")
            ])
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг", callback_data="admin_view_public_services")
        ])

        await callback.message.edit_text(
            f"<b>{current_category['title']}:</b>\n"
            "Выберите подкатегорию:",
            reply_markup=markup
        )
    else:
        services = db_utils.get_services_by_category_slug(category_slug)

        service_text = f"<b>{current_category['title']}:</b>\n\n"
        if services:
            for item in services:
                service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
                if "description" in item:
                    service_text += f"   <i>{item['description']}</i>\n"
        else:
            service_text += "Услуги в данной категории пока отсутствуют."

        markup = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг",
                                            callback_data="admin_view_public_services")],
            ]
        )
        await callback.message.edit_text(service_text, reply_markup=markup)


@admin_router.callback_query(F.data.startswith("admin_view_sub::"), AdminState.viewing_public_services_mode)
async def admin_view_service_subcategory_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку подкатегории услуг в режиме просмотра админом.
    Выводит список услуг для этой подкатегории.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    parts = callback.data.split('::')
    if len(parts) < 3:
        await callback.message.answer("Извините, некорректные данные подкатегории.")
        await admin_show_public_services_main_menu(callback, None) # state=None
        return

    parent_category_slug = parts[1]
    subcategory_slug = parts[2]

    subcategory_data = db_utils.get_category_by_slug(subcategory_slug)

    if not subcategory_data:
        await callback.message.answer("Извините, информация по данной подкатегории не найдена.")
        await admin_show_public_services_main_menu(callback, None) # state=None
        return

    services = db_utils.get_services_by_category_slug(subcategory_slug)

    service_text = f"<b>{subcategory_data['title']}:</b>\n\n"
    if services:
        for item in services:
            service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
            if "description" in item:
                service_text += f"   <i>{item['description']}</i>\n"
    else:
        service_text += "Услуги в данной подкатегории пока отсутствуют."

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад к подкатегориям", callback_data=f"admin_view_cat::{parent_category_slug}")],
        ]
    )
    await callback.message.edit_text(service_text, reply_markup=markup)

# --- Управление категориями ---
def get_manage_categories_markup():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")],
            [types.InlineKeyboardButton(text="✏️ Изменить категорию", callback_data="admin_edit_category")],
            [types.InlineKeyboardButton(text="➖ Удалить категорию", callback_data="admin_delete_category")],
            [types.InlineKeyboardButton(text="⬅️ В главное меню админа", callback_data="admin_main_menu")],
        ]
    )

@admin_router.callback_query(F.data == "admin_manage_categories", StateFilter(
    AdminState.in_admin_panel,
    AdminState.add_category_slug,
    AdminState.add_category_title,
    AdminState.add_category_parent,
    AdminState.edit_category_select,
    AdminState.edit_category_new_title,
    AdminState.delete_category_select
))
async def admin_manage_categories(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_categories)
    await callback.message.edit_text("Управление категориями:", reply_markup=get_manage_categories_markup())


# Добавление категории
@admin_router.callback_query(F.data == "admin_add_category", AdminState.manage_categories)
async def admin_add_category_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Введите уникальный идентификатор для новой категории (например, `nails_new`):",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                                     ]))
    await state.set_state(AdminState.add_category_slug)

@admin_router.message(AdminState.add_category_slug)
async def admin_add_category_get_slug(message: types.Message, state: FSMContext):
    slug = message.text.strip().lower()
    if not slug.replace('_', '').isalnum():
        await message.answer("Идентификатор должен содержать только латинские буквы, цифры и символ подчеркивания. Попробуйте еще раз.")
        return

    if db_utils.get_category_by_slug(slug):
        await message.answer("Такой идентификатор уже существует. Пожалуйста, придумайте уникальный идентификатор:",
                             reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                 [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                             ]))
        return

    await state.update_data(new_category_slug=slug)
    await message.answer("Теперь введите отображаемое НАЗВАНИЕ категории (например, `Новая Категория`):")
    await state.set_state(AdminState.add_category_title)

@admin_router.message(AdminState.add_category_title)
async def admin_add_category_get_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(new_category_title=title)

    categories = db_utils.get_all_categories_flat()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Без родительской категории", callback_data="add_cat_parent::None")]
    ])
    for cat in categories:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=cat['title'], callback_data=f"add_cat_parent::{cat['slug']}")])
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")])

    await message.answer("Выберите РОДИТЕЛЬСКУЮ категорию (если это подкатегория) или 'Без родительской категории':",
                         reply_markup=markup)
    await state.set_state(AdminState.add_category_parent)

@admin_router.callback_query(F.data.startswith("add_cat_parent::"), AdminState.add_category_parent)
async def admin_add_category_get_parent(callback: types.CallbackQuery, state: FSMContext):
    parent_slug = callback.data.split("::")[1]
    if parent_slug == "None":
        parent_slug = None

    data = await state.get_data()
    slug = data["new_category_slug"]
    title = data["new_category_title"]

    success = db_utils.add_category(slug, title, parent_slug)
    if success:
        await callback.message.edit_text(f"Категория <b>'{title}'</b> (SLUG: <code>{slug}</code>) успешно добавлена!",
                                         reply_markup=get_manage_categories_markup())
    else:
        await callback.message.edit_text(f"Ошибка при добавлении категории <b>'{title}'</b>. Возможно, SLUG <code>{slug}</code> уже занят. Попробуйте еще раз.",
                                         reply_markup=get_manage_categories_markup())
    await state.set_state(AdminState.manage_categories)


# Изменение категории
@admin_router.callback_query(F.data == "admin_edit_category", AdminState.manage_categories)
async def admin_edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await callback.message.edit_text("Нет категорий для редактирования.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=f"{cat['title']} (ID: {cat['id']})", callback_data=f"edit_cat_select::{cat['id']}")])
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")])

    await callback.message.edit_text("Выберите категорию для редактирования (по ID):", reply_markup=markup)
    await state.set_state(AdminState.edit_category_select)

@admin_router.callback_query(F.data.startswith("edit_cat_select::"), AdminState.edit_category_select)
async def admin_edit_category_selected(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("::")[1])
    category = db_utils.get_category_by_id(category_id)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    await state.update_data(editing_category_id=category_id, old_category_title=category['title'])
    await callback.message.edit_text(f"Вы выбрали категорию <b>'{category['title']}'</b>.\n"
                                     "Введите новое название для этой категории:",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                                     ]))
    await state.set_state(AdminState.edit_category_new_title)

@admin_router.message(AdminState.edit_category_new_title)
async def admin_edit_category_set_new_title(message: types.Message, state: FSMContext):
    new_title = message.text.strip()
    data = await state.get_data()
    category_id = data.get("editing_category_id")

    if category_id == None:
        await message.answer("Произошла ошибка, ID категории не найден. Начните заново.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    db_utils.update_category(category_id, new_title)
    await message.answer(f"Название категории изменено с <b>'{data['old_category_title']}'</b> на <b>'{new_title}'</b>!",
                         reply_markup=get_manage_categories_markup())
    await state.set_state(AdminState.manage_categories)


# Удаление категории
@admin_router.callback_query(F.data == "admin_delete_category", AdminState.manage_categories)
async def admin_delete_category_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await callback.message.edit_text("Нет категорий для удаления.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=f"{cat['title']} (ID: {cat['id']})", callback_data=f"del_cat_select::{cat['id']}")])
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")])

    await callback.message.edit_text("Выберите категорию для удаления (по ID). "
                                     "<b>ВНИМАНИЕ:</b> Категорию нельзя удалить, если у нее есть подкатегории или услуги!",
                                     reply_markup=markup)
    await state.set_state(AdminState.delete_category_select)

@admin_router.callback_query(F.data.startswith("del_cat_select::"), AdminState.delete_category_select)
async def admin_delete_category_selected(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("::")[1])
    category = db_utils.get_category_by_id(category_id)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    success = db_utils.delete_category(category_id)
    if success:
        await callback.message.edit_text(f"Категория <b>'{category['title']}'</b> успешно удалена.",
                                         reply_markup=get_manage_categories_markup())
    else:
        await callback.message.edit_text(f"Не удалось удалить категорию <b>'{category['title']}'</b>. "
                                         "Убедитесь, что у нее нет связанных подкатегорий или услуг, и попробуйте снова.",
                                         reply_markup=get_manage_categories_markup())
    await state.set_state(AdminState.manage_categories)


# --- Управление услугами ---
def get_manage_services_markup():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin_add_service")],
            [types.InlineKeyboardButton(text="✏️ Изменить услугу", callback_data="admin_edit_service")],
            [types.InlineKeyboardButton(text="➖ Удалить услугу", callback_data="admin_delete_service")],
            [types.InlineKeyboardButton(text="⬅️ В главное меню админа", callback_data="admin_main_menu")],
        ]
    )

@admin_router.callback_query(F.data == "admin_manage_services", StateFilter(
    AdminState.in_admin_panel,
    AdminState.select_category_for_service,
    AdminState.add_service_name,
    AdminState.add_service_price,
    AdminState.add_service_description,
    AdminState.edit_service_select,
    AdminState.edit_service_choose_field,
    AdminState.edit_service_new_value,
    AdminState.delete_service_select
))
async def admin_manage_services_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_services)
    await callback.message.edit_text("Управление услугами:", reply_markup=get_manage_services_markup())


# Вспомогательная функция для выбора категории услуги
async def send_category_selection(target: types.Message | types.CallbackQuery, state: FSMContext, next_state: State, callback_prefix: str, message_text: str):
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await target.message.answer("Нет доступных категорий для выбора.")
        # Проверяем тип 'target', чтобы избежать ошибок при редактировании
        if isinstance(target, types.CallbackQuery):
            await target.message.edit_reply_markup(reply_markup=get_manage_services_markup()) # Изменяем сообщение с ошибкой
        else:
            await target.answer("Управление услугами:", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=cat['title'], callback_data=f"{callback_prefix}::{cat['slug']}")])
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")])

    if isinstance(target, types.Message):
        await target.answer(message_text, reply_markup=markup)
    else: # CallbackQuery
        await target.message.edit_text(message_text, reply_markup=markup)
    await state.set_state(next_state)


# Добавление услуги
@admin_router.callback_query(F.data == "admin_add_service", AdminState.manage_services)
async def admin_add_service_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_category_selection(callback, state, AdminState.select_category_for_service, "add_service_cat", "Выберите категорию, в которую будет добавлена услуга:")

@admin_router.callback_query(F.data.startswith("add_service_cat::"), AdminState.select_category_for_service)
async def admin_add_service_get_category(callback: types.CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    await state.update_data(current_service_category_slug=category_slug)
    await callback.message.edit_text(f"Выбрана категория: <b>{category['title']}</b>.\n"
                                     "Теперь введите НАЗВАНИЕ новой услуги:",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                                     ]))
    await state.set_state(AdminState.add_service_name)

@admin_router.message(AdminState.add_service_name)
async def admin_add_service_get_name(message: types.Message, state: FSMContext):
    service_name = message.text.strip()
    await state.update_data(new_service_name=service_name)
    await message.answer("Введите ЦЕНУ услуги (например, `1500 ₽` или `от 2000 ₽ до 3000 ₽`):",
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                             [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                         ]))
    await state.set_state(AdminState.add_service_price)

@admin_router.message(AdminState.add_service_price)
async def admin_add_service_get_price(message: types.Message, state: FSMContext):
    service_price = message.text.strip()
    await state.update_data(new_service_price=service_price)
    await message.answer("Введите ОПИСАНИЕ услуги (необязательно, можно написать `-` или `нет`):",
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                             [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                         ]))
    await state.set_state(AdminState.add_service_description)

@admin_router.message(AdminState.add_service_description)
async def admin_add_service_get_description(message: types.Message, state: FSMContext):
    service_description = message.text.strip()
    if service_description.lower() in ["-", "нет", "none"]:
        service_description = None

    data = await state.get_data()
    category_slug = data["current_service_category_slug"]
    name = data["new_service_name"]
    price = data["new_service_price"]

    db_utils.add_service(name, price, category_slug, service_description)
    category_title = db_utils.get_category_by_slug(category_slug)['title']
    await message.answer(f"Услуга <b>'{name}'</b> добавлена в категорию <b>'{category_title}'</b>!",
                         reply_markup=get_manage_services_markup())
    await state.set_state(AdminState.manage_services)


# Изменение услуги
@admin_router.callback_query(F.data == "admin_edit_service", AdminState.manage_services)
async def admin_edit_service_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_category_selection(callback, state, AdminState.select_category_for_service, "edit_service_cat", "Выберите категорию, услугу из которой вы хотите изменить:")

@admin_router.callback_query(F.data.startswith("edit_service_cat::"), AdminState.select_category_for_service)
async def admin_edit_service_select_category(callback: types.CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    services = db_utils.get_services_by_category_slug(category_slug)
    if not services:
        await callback.message.edit_text(f"В категории <b>'{category['title']}'</b> нет услуг для изменения.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    service_list_text = f"Услуги в категории <b>{category['title']}</b>:\n\n"
    for svc in services:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=f"{svc['name']} (ID: {svc['id']})", callback_data=f"edit_svc_id::{svc['id']}")])
        service_list_text += f"ID: {svc['id']} - <b>{svc['name']}</b> - {svc['price']}\n"
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")])

    await state.update_data(current_service_category_slug_for_edit=category_slug)
    await callback.message.edit_text(service_list_text + "\nВыберите услугу по ID для изменения:", reply_markup=markup)
    await state.set_state(AdminState.edit_service_select)

@admin_router.callback_query(F.data.startswith("edit_svc_id::"), AdminState.edit_service_select)
async def admin_edit_service_select_service(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    await state.update_data(editing_service_id=service_id, editing_service_data=service)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Изменить название", callback_data="edit_svc_field::name")],
        [types.InlineKeyboardButton(text="Изменить цену", callback_data="edit_svc_field::price")],
        [types.InlineKeyboardButton(text="Изменить описание", callback_data="edit_svc_field::description")],
        [types.InlineKeyboardButton(text="Готово (вернуться к управлению услугами)", callback_data="admin_manage_services")]
    ])
    await callback.message.edit_text(f"Вы выбрали услугу <b>'{service['name']}'</b> (ID: {service['id']}).\n"
                                     f"Что хотите изменить?\n"
                                     f"Текущее название: <b>{service['name']}</b>\n"
                                     f"Текущая цена: <b>{service['price']}</b>\n"
                                     f"Текущее описание: <i>{service['description'] if service['description'] else 'нет'}</i>",
                                     reply_markup=markup)
    await state.set_state(AdminState.edit_service_choose_field)

@admin_router.callback_query(F.data.startswith("edit_svc_field::"), AdminState.edit_service_choose_field)
async def admin_edit_service_choose_field(callback: types.CallbackQuery, state: FSMContext):
    field_to_edit = callback.data.split("::")[1]
    await state.update_data(field_to_edit=field_to_edit)
    await callback.answer()

    prompt_text = ""
    if field_to_edit == "name":
        prompt_text = "Введите новое название услуги:"
    elif field_to_edit == "price":
        prompt_text = "Введите новую цену услуги:"
    elif field_to_edit == "description":
        prompt_text = "Введите новое описание услуги (или `-` / `нет`, чтобы удалить):"

    await callback.message.edit_text(prompt_text,
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                                     ]))
    await state.set_state(AdminState.edit_service_new_value)

@admin_router.message(AdminState.edit_service_new_value)
async def admin_edit_service_set_new_value(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    service_id = data.get("editing_service_id")
    field_to_edit = data.get("field_to_edit")
    current_service_data = data.get("editing_service_data")

    if not all([service_id, field_to_edit, current_service_data]):
        await message.answer("Произошла ошибка, данные услуги не найдены. Начните заново.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    if field_to_edit == "description" and new_value.lower() in ["-", "нет", "none"]:
        current_service_data[field_to_edit] = None
    else:
        current_service_data[field_to_edit] = new_value

    db_utils.update_service(service_id,
                            current_service_data['name'],
                            current_service_data['price'],
                            current_service_data['description'])

    await state.update_data(editing_service_data=current_service_data)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Изменить название", callback_data="edit_svc_field::name")],
        [types.InlineKeyboardButton(text="Изменить цену", callback_data="edit_svc_field::price")],
        [types.InlineKeyboardButton(text="Изменить описание", callback_data="edit_svc_field::description")],
        [types.InlineKeyboardButton(text="Готово (вернуться к управлению услугами)", callback_data="admin_manage_services")]
    ])

    await message.answer(f"Поле <b>'{field_to_edit}'</b> для услуги <b>'{current_service_data['name']}'</b> обновлено.\n"
                         f"Текущее название: <b>{current_service_data['name']}</b>\n"
                         f"Текущая цена: <b>{current_service_data['price']}</b>\n"
                         f"Текущее описание: <i>{current_service_data['description'] if current_service_data['description'] else 'нет'}</i>\n\n"
                         "Что еще хотите изменить или нажмите 'Готово'?", reply_markup=markup)
    await state.set_state(AdminState.edit_service_choose_field)


# Удаление услуги
@admin_router.callback_query(F.data == "admin_delete_service", AdminState.manage_services)
async def admin_delete_service_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_category_selection(callback, state, AdminState.select_category_for_service, "del_service_cat", "Выберите категорию, услугу из которой вы хотите удалить:")

@admin_router.callback_query(F.data.startswith("del_service_cat::"), AdminState.select_category_for_service)
async def admin_delete_service_select_category(callback: types.CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    services = db_utils.get_services_by_category_slug(category_slug)
    if not services:
        await callback.message.edit_text(f"В категории <b>'{category['title']}'</b> нет услуг для удаления.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    service_list_text = f"Услуги в категории <b>{category['title']}</b>:\n\n"
    for svc in services:
        markup.inline_keyboard.append([types.InlineKeyboardButton(text=f"{svc['name']} (ID: {svc['id']})", callback_data=f"del_svc_id::{svc['id']}")])
        service_list_text += f"ID: {svc['id']} - <b>{svc['name']}</b> - {svc['price']}\n"
    markup.inline_keyboard.append([types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")])

    await state.update_data(current_service_category_slug_for_edit=category_slug)
    await callback.message.edit_text(service_list_text + "\nВыберите услугу по ID для удаления:", reply_markup=markup)
    await state.set_state(AdminState.delete_service_select)

@admin_router.callback_query(F.data.startswith("del_svc_id::"), AdminState.delete_service_select)
async def admin_delete_service_confirm(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    db_utils.delete_service(service_id)
    await callback.message.edit_text(f"Услуга <b>'{service['name']}'</b> успешно удалена.",
                                     reply_markup=get_manage_services_markup())
    await state.set_state(AdminState.manage_services)

# --- ОБРАБОТЧИКИ ДЛЯ ИЗМЕНЕНИЯ ПАРОЛЯ ---
@admin_router.callback_query(F.data == "admin_change_password", AdminState.in_admin_panel)
async def admin_change_password_start(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс изменения пароля админа."""
    await callback.answer()
    await callback.message.edit_text("Пожалуйста, введите НОВЫЙ пароль для админ-панели:",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_main_menu")]
                                     ]))
    await state.set_state(AdminState.change_password_waiting_for_new_password)

@admin_router.message(AdminState.change_password_waiting_for_new_password)
async def admin_change_password_get_new(message: types.Message, state: FSMContext):
    """Получает новый пароль и обновляет его в config.json."""
    new_password = message.text.strip()

    if not new_password:
        await message.answer("Пароль не может быть пустым. Пожалуйста, введите новый пароль:")
        return

    # СОХРАНЯЕМ НОВЫЙ ПАРОЛЬ ЧЕРЕЗ config_manager
    config_manager.set_setting('ADMIN_PASSWORD', new_password)

    await message.answer(f"Пароль администратора успешно изменен на: <code>{new_password}</code>",
                         reply_markup=get_admin_main_markup())
    await state.set_state(AdminState.in_admin_panel)


# --- Основная функция запуска бота ---
async def main() -> None:
    # Инициализация базы данных
    if hasattr(db_utils, 'init_db'):
        db_utils.init_db()

    # Для отправки уведомлений админу, лучше хранить ID, а не username.
    # Если ADMIN_USERNAME_ID нет в config_manager, то надо его получить.
    # Для получения ID админа, админ должен написать боту что-нибудь, и ты можешь логировать его message.from_user.id
    admin_id = config_manager.get_setting('ADMIN_USERNAME_ID')
    if not admin_id:
        logging.warning("ADMIN_USERNAME_ID не найден в config.json. Уведомления админу могут не отправляться.")
        logging.warning("Для получения ID админа, попросите админа написать боту, а затем найдите его user.id в логах.")


    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Бот запускается... Нажмите Ctrl+C для остановки.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()

