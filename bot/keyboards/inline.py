# your_bot_project/keyboards/inline.py
import datetime
import calendar
import logging

from aiogram.types import InlineKeyboardButton, Message, CallbackQuery, InlineKeyboardMarkup  # <--- Явный импорт типов
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext  # Может быть нужно для create_time_slots_markup

import db_utils
import config_manager


# send_main_menu теперь принимает admin_username напрямую
async def send_main_menu(target: Message | CallbackQuery, admin_username: str) -> None:  # <--- ИСПРАВЛЕНО
    """
    Отправляет или редактирует сообщение с главным меню.
    Принимает объект Message (для /start) или CallbackQuery (для кнопки "Назад").
    """
    user_first_name = target.from_user.first_name

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [InlineKeyboardButton(text="✨ Наши услуги", callback_data="show_services_main_menu")],
            [InlineKeyboardButton(text="📸 Фотографии салона", callback_data="show_salon_photos")],
            [InlineKeyboardButton(text="🗓️ Мои записи", callback_data="show_my_bookings")],
            [InlineKeyboardButton(text="📍 Как до нас добраться?",
                                  url="https://yandex.ru/maps/54/yekaterinburg/?from=api-maps&ll=60.607417%2C56.855225&mode=routes&origin=jsapi_2_1_79&rtext=~56.855225%2C60.607417&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D176318285490&z=13.89")],
            [InlineKeyboardButton(text="💌 Связаться с администратором",
                                  url=f"tg://resolve?domain={admin_username}")],
        ]
    )

    welcome_message = (
        f"Привет, {user_first_name}! 👋\n\n"
        "Добро пожаловать в салон красоты \"Shade\"!\n"
        "Мы рады предложить вам широкий спектр услуг для вашей красоты и здоровья.\n"
        "Выберите интересующий раздел ниже, чтобы узнать больше:"
    )

    if isinstance(target, Message):
        await target.answer(welcome_message, reply_markup=markup)
    elif isinstance(target, CallbackQuery):
        if target.message.text:
            try:
                await target.message.edit_text(welcome_message, reply_markup=markup)
            except Exception:
                await target.message.answer(welcome_message, reply_markup=markup)
        else:
            await target.message.answer(welcome_message, reply_markup=markup)


def get_admin_main_markup() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для главного меню админ-панели."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Управление категориями", callback_data="admin_manage_categories")],
            [InlineKeyboardButton(text="Управление услугами", callback_data="admin_manage_services")],
            [InlineKeyboardButton(text="Посмотреть услуги (как пользователь)",
                                  callback_data="admin_view_public_services")],
            [InlineKeyboardButton(text="Изменить пароль админа", callback_data="admin_change_password")],
            [InlineKeyboardButton(text="Выйти из админ-панели", callback_data="admin_exit")],
        ]
    )


def get_manage_categories_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")],
            [InlineKeyboardButton(text="✏️ Изменить категорию", callback_data="admin_edit_category")],
            [InlineKeyboardButton(text="➖ Удалить категорию", callback_data="admin_delete_category")],
            [InlineKeyboardButton(text="⬅️ В главное меню админа", callback_data="admin_main_menu")],
        ]
    )


def get_manage_services_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin_add_service")],
            [InlineKeyboardButton(text="✏️ Изменить услугу", callback_data="admin_edit_service")],
            [InlineKeyboardButton(text="➖ Удалить услугу", callback_data="admin_delete_service")],
            [InlineKeyboardButton(text="⬅️ В главное меню админа", callback_data="admin_main_menu")],
        ]
    )


async def get_category_selection_markup(callback_prefix: str, include_none_option: bool = False,
                                        for_edit_delete: bool = False, return_to_admin_categories: bool = False,
                                        return_to_admin_services: bool = False) -> InlineKeyboardMarkup:
    """
    Вспомогательная функция для генерации клавиатуры выбора категорий в админ-панели.
    Возвращает InlineKeyboardMarkup.
    :param callback_prefix: Префикс для callback_data кнопок категорий.
    :param include_none_option: Включить ли опцию "Без родительской категории".
    :param for_edit_delete: Если True, кнопки будут с ID категории, иначе - со slug.
    :param return_to_admin_categories: Флаг для кнопки "Отмена" для возврата к управлению категориями.
    :param return_to_admin_services: Флаг для кнопки "Отмена" для возврата к управлению услугами.
    """
    categories = db_utils.get_all_categories_flat()

    markup = InlineKeyboardBuilder()

    if include_none_option:
        markup.row(InlineKeyboardButton(text="Без родительской категории", callback_data=f"{callback_prefix}::None"))

    for cat in categories:
        if for_edit_delete:
            markup.row(InlineKeyboardButton(text=f"{cat['title']} (ID: {cat['id']})",
                                            callback_data=f"{callback_prefix}::{cat['id']}"))
        else:
            markup.row(InlineKeyboardButton(text=cat['title'], callback_data=f"{callback_prefix}::{cat['slug']}"))

    if return_to_admin_categories:
        markup.row(InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories"))
    elif return_to_admin_services:
        markup.row(InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services"))
    else:  # Fallback, если ни один флаг не установлен (например, для пользовательской части)
        markup.row(InlineKeyboardButton(text="Отмена", callback_data="back_to_main_menu"))

    return markup.as_markup()


async def create_calendar_markup(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    cal = calendar.Calendar()
    month_days = cal.monthdayscalendar(year, month)

    markup = InlineKeyboardBuilder()

    markup.row(InlineKeyboardButton(text=f"{calendar.month_name[month]} {year}", callback_data="ignore_calendar"))

    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[InlineKeyboardButton(text=day, callback_data="ignore_calendar") for day in week_days])

    for week in month_days:
        row_buttons = []
        for day in week:
            if day == 0:
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore_calendar"))
            else:
                current_date = datetime.date(year, month, day)
                if current_date < now.date():
                    row_buttons.append(InlineKeyboardButton(text=str(day), callback_data="ignore_calendar"))
                else:
                    row_buttons.append(InlineKeyboardButton(text=str(day),
                                                            callback_data=f"cal_day::{current_date.strftime('%Y-%m-%d')}"))
        markup.row(*row_buttons)

    prev_month_date = (datetime.date(year, month, 1) - datetime.timedelta(days=1))
    next_month_date = (datetime.date(year, month, 1) + datetime.timedelta(days=32))

    markup.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"cal_nav::{prev_month_date.year}::{prev_month_date.month}"),
        InlineKeyboardButton(text="➡️", callback_data=f"cal_nav::{next_month_date.year}::{next_month_date.month}")
    )
    markup.row(InlineKeyboardButton(text="⬅️ Назад к выбору услуги", callback_data="book_back_to_service_selection"))
    return markup.as_markup()


async def create_time_slots_markup(state: FSMContext) -> InlineKeyboardMarkup:
    data = await state.get_data()
    chosen_date_str = data.get('chosen_date')
    chosen_service_id = data.get('chosen_service_id')

    if not chosen_date_str or not chosen_service_id:
        logging.error("Chosen date or service ID not found in FSM context for time slot generation.")
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ошибка: Вернуться к выбору даты", callback_data="book_back_to_date_selection")]
        ])

    booked_times = db_utils.get_booked_slots_for_date_service(chosen_date_str, chosen_service_id)
    all_slots = []

    start_hour = 9
    end_hour = 20
    interval_minutes = 30

    current_time_dt = datetime.datetime.now()
    today_str = current_time_dt.strftime('%Y-%m-%d')

    for hour in range(start_hour, end_hour):
        for minute_step in range(0, 60, interval_minutes):
            slot_time = datetime.time(hour, minute_step)
            slot_str = slot_time.strftime('%H:%M')

            is_past = False
            if chosen_date_str == today_str:
                combined_dt = datetime.datetime.combine(current_time_dt.date(), slot_time)
                if combined_dt < current_time_dt:
                    is_past = True

            if not is_past and slot_str not in booked_times:
                all_slots.append(slot_str)

    markup = InlineKeyboardBuilder()
    row_buttons = []
    if not all_slots:
        markup.row(InlineKeyboardButton(text="На эту дату нет свободных временных слотов. Выберите другую дату.",
                                        callback_data="ignore_time_slot"))
    else:
        for slot in all_slots:
            button = InlineKeyboardButton(text=slot, callback_data=f"book_time::{slot}")
            row_buttons.append(button)
            if len(row_buttons) == 4:
                markup.row(*row_buttons)
                row_buttons = []
        if row_buttons:
            markup.row(*row_buttons)

    markup.row(InlineKeyboardButton(text="⬅️ Назад к выбору даты", callback_data="book_back_to_date_selection"))
    return markup.as_markup()
