import logging
import datetime
import calendar

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, Message, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup # <--- Явный импорт типов
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db_utils
import config_manager
from states.user_states import BookingState
from states.admin_states import AdminState # Для StateFilter в main_menu
from keyboards.inline import (
    create_calendar_markup,
    create_time_slots_markup,
    send_main_menu
)

user_router = Router()

PHOTO_URLS = config_manager.get_setting('PHOTO_URLS', [])
ADMIN_USERNAME = config_manager.get_setting('ADMIN_USERNAME')

#Обработчики пользователей

@user_router.callback_query(F.data == "show_services_main_menu")
async def process_services_main_menu_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку "Наши услуги".
    Показывает основные категории услуг, получая их из БД.
    """
    await callback.answer(text="Загрузка категорий услуг...", show_alert=False)

    markup = InlineKeyboardMarkup(inline_keyboard=[])

    main_categories = db_utils.get_main_categories()

    for category in main_categories:
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=f"✨ {category['title']}", callback_data=f"cat::{category['slug']}")
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    ])

    await callback.message.edit_text(
        "<b>💎 Наши услуги:</b>\n"
        "Выберите интересующую категорию:",
        reply_markup=markup
    )


@user_router.callback_query(F.data.startswith("cat::"))
async def process_service_category_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку категории услуг.
    Либо показывает подкатегории, либо выводит список услуг, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    category_slug = callback.data.split("::")[1]

    current_category = db_utils.get_category_by_slug(category_slug)
    if not current_category:
        await callback.message.answer("Извините, информация по данной категории не найдена.")
        await send_main_menu(target=callback, admin_username=ADMIN_USERNAME)
        return

    subcategories = db_utils.get_subcategories(category_slug)

    if subcategories:
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        for sub_data in subcategories:
            markup.inline_keyboard.append([
                InlineKeyboardButton(text=f"▪️ {sub_data['title']}",
                                           callback_data=f"sub::{category_slug}::{sub_data['slug']}")
            ])
        markup.inline_keyboard.append([
            InlineKeyboardButton(text="⬅️ Назад к категориям услуг", callback_data="show_services_main_menu")
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

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к категориям услуг",
                                            callback_data="show_services_main_menu")],
            ]
        )
        await callback.message.edit_text(service_text, reply_markup=markup)


@user_router.callback_query(F.data.startswith("sub::"))
async def process_service_subcategory_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку подкатегории услуг.
    Выводит список услуг для этой подкатегории, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    parts = callback.data.split('::')

    if len(parts) < 3:
        await callback.message.answer("Извините, некорректные данные подкатегории.")
        await send_main_menu(target=callback, admin_username=ADMIN_USERNAME)
        return

    parent_category_slug = parts[1]
    subcategory_slug = parts[2]

    subcategory_data = db_utils.get_category_by_slug(subcategory_slug)

    if not subcategory_data:
        await callback.message.answer("Извините, информация по данной подкатегории не найдена.")
        await send_main_menu(target=callback, admin_username=ADMIN_USERNAME)
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

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к подкатегориям", callback_data=f"cat::{parent_category_slug}")],
        ]
    )
    await callback.message.edit_text(service_text, reply_markup=markup)


@user_router.callback_query(F.data == "show_salon_photos")
async def process_photos_callback(callback: CallbackQuery):
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

    await callback.bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )
    await callback.message.answer(
        "Надеемся, вам понравились фотографии нашего салона! ✨",
        reply_markup=markup
    )


#Мои записи
@user_router.callback_query(F.data == "show_my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    await callback.answer("Загружаю ваши записи...", show_alert=False)
    user_id = callback.from_user.id
    bookings = db_utils.get_user_bookings(user_id)

    if not bookings:
        message_text = "У вас пока нет активных записей. Хотите записаться?"
    else:
        message_text = "<b>Ваши предстоящие записи:</b>\n\n"
        for i, booking in enumerate(bookings):
            formatted_date = datetime.datetime.strptime(booking['booking_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            message_text += (
                f"Запись №{i+1}:\n"
                f"  📅 Дата: <b>{formatted_date}</b>\n"
                f"  ⏰ Время: <b>{booking['booking_time']}</b>\n"
                f"  💅 Услуга: <b>{booking['service_name']}</b> (Категория: {booking['category_name']})\n"
                f"  💬 Комментарий: <i>{booking['comment'] if booking['comment'] else 'нет'}</i>\n"
                f"  📞 Ваш номер: <code>{booking['user_phone']}</code>\n\n"
            )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )
    await callback.message.edit_text(message_text, reply_markup=markup)


#Функционал записи клиентов

@user_router.callback_query(F.data == "start_booking")
async def booking_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Начинаем запись...", show_alert=False)
    await state.clear()

    markup = InlineKeyboardBuilder()
    main_categories = db_utils.get_main_categories()

    if not main_categories:
        await callback.message.edit_text("Извините, пока нет доступных категорий услуг для записи. Пожалуйста, попробуйте позже.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")]
                                         ]))
        await state.clear()
        return

    for category in main_categories:
        markup.button(text=f"✨ {category['title']}", callback_data=f"book_cat::{category['slug']}")

    markup.row(InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu"))
    await callback.message.edit_text("<b>📝 Запись на услугу:</b>\nВыберите категорию услуги:", reply_markup=markup.as_markup())
    await state.set_state(BookingState.choosing_category)


@user_router.callback_query(F.data.startswith("book_cat::"), BookingState.choosing_category)
async def booking_choose_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Загружаю услуги...", show_alert=False)
    category_slug = callback.data.split("::")[1]
    current_category = db_utils.get_category_by_slug(category_slug)

    if not current_category:
        await callback.message.edit_text("Категория не найдена. Пожалуйста, выберите другую.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="start_booking")]
                                         ]))
        return

    await state.update_data(current_booking_category_slug=category_slug)

    subcategories = db_utils.get_subcategories(category_slug)
    if subcategories:
        markup = InlineKeyboardBuilder()
        for sub_data in subcategories:
            markup.button(text=f"▪️ {sub_data['title']}", callback_data=f"book_sub::{category_slug}::{sub_data['slug']}")
        markup.row(InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="start_booking"))
        await callback.message.edit_text(f"<b>{current_category['title']}:</b>\nВыберите подкатегорию:", reply_markup=markup.as_markup())
    else:
        await _send_services_for_booking(callback, state, category_slug, "start_booking")


@user_router.callback_query(F.data.startswith("book_sub::"), BookingState.choosing_category)
async def booking_choose_subcategory(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Загружаю услуги...", show_alert=False)
    parts = callback.data.split("::")
    parent_category_slug = parts[1]
    subcategory_slug = parts[2]
    await state.update_data(current_booking_category_slug=subcategory_slug, parent_category_slug_for_booking=parent_category_slug)
    await _send_services_for_booking(callback, state, subcategory_slug, f"book_cat::{parent_category_slug}")


async def _send_services_for_booking(callback: CallbackQuery, state: FSMContext, category_slug: str, back_callback_data: str):
    """Вспомогательная функция для отправки списка услуг для выбора записи."""
    services = db_utils.get_services_by_category_slug(category_slug)
    category_title = db_utils.get_category_by_slug(category_slug)['title']

    if not services:
        await callback.message.edit_text(f"В категории <b>'{category_title}'</b> пока нет услуг для записи.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data)]
                                         ]))
        return

    markup = InlineKeyboardBuilder()
    text = f"<b>{category_title}:</b>\nВыберите услугу для записи:\n\n"
    for svc in services:
        markup.button(text=f"✨ {svc['name']} - {svc['price']}", callback_data=f"book_svc::{svc['id']}")
        text += f"▪️ <b>{svc['name']}</b> - {svc['price']}\n"
        if svc.get('description'):
            text += f"   <i>{svc['description']}</i>\n"

    markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data))
    await callback.message.edit_text(text, reply_markup=markup.as_markup())
    await state.set_state(BookingState.choosing_service)


@user_router.callback_query(F.data.startswith("book_svc::"), BookingState.choosing_service)
async def booking_select_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Выбрана услуга...", show_alert=False)
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)

    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="⬅️ Назад к выбору услуг", callback_data="start_booking")]
                                         ]))
        return

    await state.update_data(chosen_service_id=service_id, chosen_service_name=service['name'],
                            chosen_service_category_slug=service['category_slug'])

    await callback.message.edit_text(f"Вы выбрали услугу: <b>{service['name']}</b>. \n\nТеперь выберите желаемую дату:",
                                     reply_markup=await create_calendar_markup())
    await state.set_state(BookingState.choosing_date)


@user_router.callback_query(F.data.startswith("cal_nav::"), BookingState.choosing_date)
async def process_calendar_navigation(callback: CallbackQuery, state: FSMContext):
    await callback.answer(show_alert=False)
    parts = callback.data.split("::")
    year = int(parts[1])
    month = int(parts[2])
    await callback.message.edit_reply_markup(reply_markup=await create_calendar_markup(year, month))

@user_router.callback_query(F.data == "ignore_calendar", BookingState.choosing_date)
async def ignore_calendar_callback(callback: CallbackQuery):
    await callback.answer(show_alert=False)

@user_router.callback_query(F.data == "book_back_to_service_selection", BookingState.choosing_date)
async def book_back_to_service_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору услуги...", show_alert=False)
    await booking_start(callback, state)


@user_router.callback_query(F.data.startswith("cal_day::"), BookingState.choosing_date)
async def booking_select_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Выбрана дата...", show_alert=False)
    chosen_date_str = callback.data.split("::")[1]
    chosen_date = datetime.datetime.strptime(chosen_date_str, '%Y-%m-%d').date()

    await state.update_data(chosen_date=chosen_date_str)

    await callback.message.edit_text(f"Выбрана дата: <b>{chosen_date.strftime('%d.%m.%Y')}</b>. \nТеперь выберите желаемое время:",
                                     reply_markup=await create_time_slots_markup(state))
    await state.set_state(BookingState.choosing_time)


@user_router.callback_query(F.data == "ignore_time_slot", BookingState.choosing_time)
async def ignore_time_slot_callback(callback: CallbackQuery):
    await callback.answer("Это время занято или недоступно. Выберите другое.", show_alert=True)

@user_router.callback_query(F.data == "book_back_to_date_selection", BookingState.choosing_time)
async def book_back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору даты...", show_alert=False)
    await callback.message.edit_text("Теперь выберите желаемую дату:",
                                     reply_markup=await create_calendar_markup())
    await state.set_state(BookingState.choosing_date)


@user_router.callback_query(F.data.startswith("book_time::"), BookingState.choosing_time)
async def booking_select_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Выбрано время...", show_alert=False)
    chosen_time_str = callback.data.split("::")[1]
    await state.update_data(chosen_time=chosen_time_str)

    await callback.message.edit_text(f"Вы выбрали время: <b>{chosen_time_str}</b>. \n\n"
                                     "Оставьте комментарий к записи (например, особенности, пожелания). "
                                     "Если комментарий не нужен, просто напишите `-` или `нет`:",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="⬅️ Назад к выбору времени", callback_data="book_back_to_time_selection")]
                                     ]))
    await state.set_state(BookingState.entering_comment)

@user_router.callback_query(F.data == "book_back_to_time_selection", BookingState.entering_comment)
async def book_back_to_time_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Возврат к выбору времени...", show_alert=False)
    await callback.message.edit_text("Теперь выберите желаемое время:",
                                     reply_markup=await create_time_slots_markup(state))
    await state.set_state(BookingState.choosing_time)

@user_router.message(BookingState.entering_comment)
async def booking_enter_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment.lower() in ["-", "нет", "none", "n/a", "no"]:
        comment = None
    await state.update_data(comment=comment)

    request_phone_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться номером телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Теперь, пожалуйста, укажите ваш номер телефона. "
                         "Вы можете нажать кнопку 'Поделиться номером телефона' ниже или ввести его вручную:",
                         reply_markup=request_phone_markup)
    await state.set_state(BookingState.entering_phone)


@user_router.message(BookingState.entering_phone, F.contact)
async def booking_get_phone_from_contact(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone=phone_number)
    await _confirm_booking(message, state)


@user_router.message(BookingState.entering_phone)
async def booking_enter_phone_manually(message: Message, state: FSMContext):
    phone_number = message.text.strip()
    if not (phone_number.startswith('+') and phone_number[1:].isdigit() and len(phone_number) > 8) and not (phone_number.isdigit() and len(phone_number) >= 10):
        await message.answer("Пожалуйста, введите корректный номер телефона (например, +79XXXXXXXXX или 89XXXXXXXXX):",
                             reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data(phone=phone_number)
    await _confirm_booking(message, state)

async def _confirm_booking(message: Message, state: FSMContext):
    data = await state.get_data()
    service_name = data.get('chosen_service_name', 'Неизвестная услуга')
    chosen_date_str = data.get('chosen_date', 'Не выбрана')
    chosen_time_str = data.get('chosen_time', 'Не выбрано')
    comment = data.get('comment', 'Нет')
    phone = data.get('phone', 'Не указан')

    if message.reply_markup and isinstance(message.reply_markup, ReplyKeyboardMarkup):
        try:
            await message.answer("Проверяю вашу запись...", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            logging.warning(f"Не удалось удалить или отредактировать сообщение с ReplyKeyboard: {e}")

    summary_text = (
        "<b>Ваша запись:</b>\n\n"
        f"💅 Услуга: <b>{service_name}</b>\n"
        f"📅 Дата: <b>{datetime.datetime.strptime(chosen_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Время: <b>{chosen_time_str}</b>\n"
        f"💬 Комментарий: <i>{comment if comment else 'нет'}</i>\n"
        f"📞 Ваш номер: <code>{phone}</code>\n\n"
        "Все верно?"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="booking_confirm")],
        [InlineKeyboardButton(text="❌ Отменить и начать заново", callback_data="booking_cancel")]
    ])
    await message.answer(summary_text, reply_markup=markup)
    await state.set_state(BookingState.confirming_booking)


@user_router.callback_query(F.data == "booking_confirm", BookingState.confirming_booking)
async def booking_final_confirm(callback: CallbackQuery, state: FSMContext):
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
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="📝 Начать запись заново", callback_data="start_booking")]
                                         ]))
        await state.clear()
        return

    success = db_utils.add_booking(user_id, phone, service_id, booking_date, booking_time, comment)

    if success:
        formatted_date = datetime.datetime.strptime(booking_date, '%Y-%m-%d').strftime('%d.%m.%Y')
        await callback.message.edit_text(
            f"🎉 Ваша запись на услугу <b>{data['chosen_service_name']}</b> на <b>{formatted_date}</b> в <b>{booking_time}</b> успешно создана!\n\n"
            "Скоро с вами свяжется администратор для уточнения деталей. Спасибо, что выбрали нас! ✨",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu")],
                [InlineKeyboardButton(text="🗓️ Мои записи", callback_data="show_my_bookings")]
            ])
        )
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
                await callback.bot.send_message(chat_id=admin_id, text=admin_message, parse_mode=ParseMode.HTML)
                logging.info(f"Уведомление о новой записи отправлено админу {admin_id}")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        else:
            logging.warning("ADMIN_USERNAME_ID не настроен. Уведомление о новой записи не отправлено админу.")


    else:
        await callback.message.edit_text(
            "Произошла ошибка при сохранении вашей записи. Пожалуйста, попробуйте еще раз или свяжитесь с администратором.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Начать запись заново", callback_data="start_booking")],
                [InlineKeyboardButton(text="💌 Связаться с администратором", url=f"tg://resolve?domain={ADMIN_USERNAME}")]
            ])
        )

    await state.clear()

@user_router.callback_query(F.data == "booking_cancel", BookingState.confirming_booking)
async def booking_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Запись отменена.", show_alert=True)
    await state.clear()
    await callback.message.edit_text(
        "Запись отменена. Вы можете начать процесс записи заново в любое время.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записаться на услугу", callback_data="start_booking")],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu")]
        ])
    )
