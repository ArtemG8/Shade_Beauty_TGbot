import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InputMediaPhoto, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services_data import PHOTO_URLS
import db_utils # Импортируем наш модуль для работы с БД

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота, полученный от BotFather
BOT_TOKEN = "8099050356:AAHTmPGZ72er-_tguInYs8raDWHH9We1qcI"

# Замените 'YOUR_ADMIN_USERNAME' на реальный юзернейм администратора Telegram (без символа '@')
ADMIN_USERNAME = "ArtemArtem11111"
ADMIN_PASSWORD = "ADMINSHADE" # Пароль для входа в админ-панель

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Инициализация объекта Bot и Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
admin_router = Router() # Отдельный роутер для админ-панели

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
    # temporary state to hold service data while editing multiple fields
    editing_service_data = State()

    delete_service_select = State()


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
            [types.InlineKeyboardButton(text="📍 Как до нас добраться?", url="https://yandex.ru/maps/54/yekaterinburg/?from=api-maps&ll=60.607417%2C56.855225&mode=routes&origin=jsapi_2_1_79&rtext=~56.855225%2C60.607417&rtt=mt&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D176318285490&z=13.89")],
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
            except Exception:
                await target.message.answer(welcome_message, reply_markup=markup)
        else:
            await target.message.answer(welcome_message, reply_markup=markup)


# --- Обработчики команд и кнопок (Публичная часть) ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик команды /start. Отправляет приветственное сообщение с инлайн-кнопками.
    """
    await state.clear() # Очищаем состояние на всякий случай
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


@dp.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на кнопку "Назад в главное меню".
    """
    await state.clear() # Очищаем состояние при выходе в главное меню
    await callback.answer()
    await send_main_menu(callback)


# --- Админ-панель ---
@admin_router.message(CommandStart(magic=F.args == "admin"))
@admin_router.message(F.text == "/admin")
async def cmd_admin(message: types.Message, state: FSMContext):
    """Начинает процесс входа в админ-панель."""
    await message.answer("Введите пароль для доступа к админ-панели:")
    await state.set_state(AdminState.waiting_for_password)

@admin_router.message(AdminState.waiting_for_password)
async def process_admin_password(message: types.Message, state: FSMContext):
    """Проверяет пароль и предоставляет доступ к админ-панели."""
    if message.text == ADMIN_PASSWORD:
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
            [types.InlineKeyboardButton(text="Выйти из админ-панели", callback_data="admin_exit")],
        ]
    )

@admin_router.callback_query(F.data == "admin_main_menu", AdminState.in_admin_panel)
@admin_router.callback_query(F.data == "admin_main_menu", AdminState.manage_categories) # Для возврата из управления категориями
@admin_router.callback_query(F.data == "admin_main_menu", AdminState.manage_services) # Для возврата из управления услугами
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

@admin_router.callback_query(F.data == "admin_manage_categories", AdminState.in_admin_panel)
async def admin_manage_categories(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_categories)
    await callback.message.edit_text("Управление категориями:", reply_markup=get_manage_categories_markup())


# Добавление категории
@admin_router.callback_query(F.data == "admin_add_category", AdminState.manage_categories)
async def admin_add_category_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Введите уникальный SLUG для новой категории (например, `new_category_slug`):",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                         [types.InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                                     ]))
    await state.set_state(AdminState.add_category_slug)

@admin_router.message(AdminState.add_category_slug)
async def admin_add_category_get_slug(message: types.Message, state: FSMContext):
    slug = message.text.strip().lower()
    if not slug.replace('_', '').isalnum(): # Простая проверка на латинские буквы и цифры
        await message.answer("SLUG должен содержать только латинские буквы, цифры и символ подчеркивания. Попробуйте еще раз.")
        return

    if db_utils.get_category_by_slug(slug):
        await message.answer("Такой SLUG уже существует. Пожалуйста, придумайте уникальный SLUG:",
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

    if category_id is None:
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

@admin_router.callback_query(F.data == "admin_manage_services", AdminState.in_admin_panel)
async def admin_manage_services_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_services)
    await callback.message.edit_text("Управление услугами:", reply_markup=get_manage_services_markup())


# Вспомогательная функция для выбора категории услуги
async def send_category_selection(target: types.Message | types.CallbackQuery, state: FSMContext, next_state: State, callback_prefix: str, message_text: str):
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await target.message.answer("Нет доступных категорий для выбора.")
        await target.message.answer("Управление услугами:", reply_markup=get_manage_services_markup())
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
                                     ])) # Можно сделать более умную отмену, возвращая на шаг выбора услуги
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

    # Обновляем данные в словаре current_service_data
    if field_to_edit == "description" and new_value.lower() in ["-", "нет", "none"]:
        current_service_data[field_to_edit] = None
    else:
        current_service_data[field_to_edit] = new_value

    db_utils.update_service(service_id,
                            current_service_data['name'],
                            current_service_data['price'],
                            current_service_data['description'])

    await state.update_data(editing_service_data=current_service_data) # Обновляем сохраненные данные

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

    await callback.message.edit_text(service_list_text + "\nВыберите услугу по ID для удаления:", reply_markup=markup)
    await state.set_state(AdminState.delete_service_select)

@admin_router.callback_query(F.data.startswith("del_svc_id::"), AdminState.delete_service_select)
async def admin_delete_service_confirm(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.", reply_markup=get_manage_services_markup())
        await state.set_admin_main_menu(AdminState.manage_services)
        return

    db_utils.delete_service(service_id)
    await callback.message.edit_text(f"Услуга <b>'{service['name']}'</b> успешно удалена.",
                                     reply_markup=get_manage_services_markup())
    await state.set_state(AdminState.manage_services)


# Регистрируем роутер админ-панели в основном диспетчере
dp.include_router(admin_router)

# --- Основная функция запуска бота ---
async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Бот запускается... Нажмите Ctrl+C для остановки.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()

