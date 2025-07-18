# your_bot_project/handlers/admin.py
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, Message, CallbackQuery, InlineKeyboardMarkup  # <--- Явный импорт типов

import db_utils
import config_manager
from states.admin_states import AdminState
from keyboards.inline import (
    get_admin_main_markup,
    get_manage_categories_markup,
    get_manage_services_markup,
    get_category_selection_markup  # Теперь эта функция просто возвращает клавиатуру
)

admin_router = Router()


# --- АДМИН-ПАНЕЛЬ ---
@admin_router.message(CommandStart(magic=F.args == "admin"))
@admin_router.message(F.text == "/admin")
async def cmd_admin(message: Message, state: FSMContext):
    """Начинает процесс входа в админ-панель."""
    await message.answer("Введите пароль для доступа к админ-панели:")
    await state.set_state(AdminState.waiting_for_password)


@admin_router.message(AdminState.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext):
    """Проверяет пароль и предоставляет доступ к админ-панели."""
    current_admin_password = config_manager.get_setting('ADMIN_PASSWORD')

    if message.text == current_admin_password:
        await message.answer("Добро пожаловать в админ-панель! Что хотите сделать?",
                             reply_markup=get_admin_main_markup())
        await state.set_state(AdminState.in_admin_panel)
        admin_id = config_manager.get_setting('ADMIN_USERNAME_ID')
        if not admin_id or admin_id != message.from_user.id:
            config_manager.set_setting('ADMIN_USERNAME_ID', message.from_user.id)
            logging.info(f"Обновлен ADMIN_USERNAME_ID: {message.from_user.id}")
    else:
        await message.answer("Неверный пароль. Попробуйте еще раз или нажмите /start для возврата в главное меню.")


@admin_router.callback_query(F.data == "admin_main_menu", StateFilter(
    AdminState.in_admin_panel,
    AdminState.manage_categories,
    AdminState.add_category_slug,
    AdminState.add_category_title,
    AdminState.add_category_parent,
    AdminState.edit_category_select,
    AdminState.edit_category_new_title,
    AdminState.delete_category_select,
    AdminState.manage_services,
    AdminState.select_category_for_service,
    AdminState.add_service_name,
    AdminState.add_service_price,
    AdminState.add_service_description,
    AdminState.edit_service_select,
    AdminState.edit_service_choose_field,
    AdminState.edit_service_new_value,
    AdminState.delete_service_select,
    AdminState.viewing_public_services_mode,
    AdminState.change_password_waiting_for_new_password
))
async def admin_main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата в главное меню админ-панели."""
    await callback.answer()
    await state.set_state(AdminState.in_admin_panel)
    await callback.message.edit_text("Добро пожаловать в админ-панель! Что хотите сделать?",
                                     reply_markup=get_admin_main_markup())


@admin_router.callback_query(F.data == "admin_exit", AdminState.in_admin_panel)
async def admin_exit_callback(callback: CallbackQuery, state: FSMContext):
    """Выход из админ-панели."""
    await callback.answer("Вы вышли из админ-панели.", show_alert=True)
    await state.clear()
    await callback.message.edit_text("Вы вышли из админ-панели. Для возврата в главное меню используйте /start.")


# --- ОБРАБОТЧИКИ ДЛЯ ПРОСМОТРА УСЛУГ АДМИНОМ (как пользователь) ---
@admin_router.callback_query(F.data == "admin_view_public_services",
                             StateFilter(AdminState.in_admin_panel, AdminState.viewing_public_services_mode))
async def admin_show_public_services_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на кнопку "Посмотреть услуги (как пользователь)" в админ-панели.
    Показывает основные категории услуг с возможностью вернуться в админку.
    """
    await callback.answer(text="Загрузка категорий услуг...", show_alert=False)
    await state.set_state(AdminState.viewing_public_services_mode)

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    main_categories = db_utils.get_main_categories()

    for category in main_categories:
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=f"✨ {category['title']}", callback_data=f"admin_view_cat::{category['slug']}")
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_main_menu")
    ])

    await callback.message.edit_text(
        "<b>💎 Наши услуги (режим просмотра для админа):</b>\n"
        "Выберите интересующую категорию:",
        reply_markup=markup
    )


@admin_router.callback_query(F.data.startswith("admin_view_cat::"), AdminState.viewing_public_services_mode)
async def admin_view_service_category_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку категории услуг в режиме просмотра админом.
    Либо показывает подкатегории, либо выводит список услуг, получая данные из БД.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    category_slug = callback.data.split("::")[1]
    current_category = db_utils.get_category_by_slug(category_slug)
    if not current_category:
        await callback.message.answer("Извините, информация по данной категории не найдена.")
        # При ошибке возвращаемся в главное меню просмотра для админа, но не сбрасываем состояние
        await admin_show_public_services_main_menu(callback,
                                                   None)  # state=None потому что не используется в этой заглушке
        return

    subcategories = db_utils.get_subcategories(category_slug)

    if subcategories:
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        for sub_data in subcategories:
            markup.inline_keyboard.append([
                InlineKeyboardButton(text=f"▪️ {sub_data['title']}",
                                     callback_data=f"admin_view_sub::{category_slug}::{sub_data['slug']}")
            ])
        markup.inline_keyboard.append([
            InlineKeyboardButton(text="⬅️ Назад к категориям услуг", callback_data="admin_view_public_services")
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
                                      callback_data="admin_view_public_services")],
            ]
        )
        await callback.message.edit_text(service_text, reply_markup=markup)


@admin_router.callback_query(F.data.startswith("admin_view_sub::"), AdminState.viewing_public_services_mode)
async def admin_view_service_subcategory_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку подкатегории услуг в режиме просмотра админом.
    Выводит список услуг для этой подкатегории.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    parts = callback.data.split('::')
    if len(parts) < 3:
        await callback.message.answer("Извините, некорректные данные подкатегории.")
        await admin_show_public_services_main_menu(callback, None)
        return

    parent_category_slug = parts[1]
    subcategory_slug = parts[2]

    subcategory_data = db_utils.get_category_by_slug(subcategory_slug)

    if not subcategory_data:
        await callback.message.answer("Извините, информация по данной подкатегории не найдена.")
        await admin_show_public_services_main_menu(callback, None)
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
            [InlineKeyboardButton(text="⬅️ Назад к подкатегориям",
                                  callback_data=f"admin_view_cat::{parent_category_slug}")],
        ]
    )
    await callback.message.edit_text(service_text, reply_markup=markup)


# --- Управление категориями ---
@admin_router.callback_query(F.data == "admin_manage_categories", StateFilter(
    AdminState.in_admin_panel,
    AdminState.add_category_slug,
    AdminState.add_category_title,
    AdminState.add_category_parent,
    AdminState.edit_category_select,
    AdminState.edit_category_new_title,
    AdminState.delete_category_select
))
async def admin_manage_categories(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_categories)
    await callback.message.edit_text("Управление категориями:", reply_markup=get_manage_categories_markup())


# Добавление категории
@admin_router.callback_query(F.data == "admin_add_category", AdminState.manage_categories)
async def admin_add_category_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Введите уникальный идентификатор для новой категории (например, `nails_new`):",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                                     ]))
    await state.set_state(AdminState.add_category_slug)


@admin_router.message(AdminState.add_category_slug)
async def admin_add_category_get_slug(message: Message, state: FSMContext):
    slug = message.text.strip().lower()
    if not slug.replace('_', '').isalnum():
        await message.answer(
            "Идентификатор должен содержать только латинские буквы, цифры и символ подчеркивания. Попробуйте еще раз.")
        return

    if db_utils.get_category_by_slug(slug):
        await message.answer("Такой идентификатор уже существует. Пожалуйста, придумайте уникальный идентификатор:",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                             ]))
        return

    await state.update_data(new_category_slug=slug)
    await message.answer("Теперь введите отображаемое НАЗВАНИЕ категории (например, `Новая Категория`):")
    await state.set_state(AdminState.add_category_title)


@admin_router.message(AdminState.add_category_title)
async def admin_add_category_get_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(new_category_title=title)

    # Генерация клавиатуры для выбора родительской категории
    markup = await get_category_selection_markup(callback_prefix="add_cat_parent", include_none_option=True,
                                                 return_to_admin_categories=True)
    await message.answer("Выберите РОДИТЕЛЬСКУЮ категорию (если это подкатегория) или 'Без родительской категории':",
                         reply_markup=markup)
    await state.set_state(AdminState.add_category_parent)


@admin_router.callback_query(F.data.startswith("add_cat_parent::"), AdminState.add_category_parent)
async def admin_add_category_get_parent(callback: CallbackQuery, state: FSMContext):
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
        await callback.message.edit_text(
            f"Ошибка при добавлении категории <b>'{title}'</b>. Возможно, SLUG <code>{slug}</code> уже занят. Попробуйте еще раз.",
            reply_markup=get_manage_categories_markup())
    await state.set_state(AdminState.manage_categories)


# Изменение категории
@admin_router.callback_query(F.data == "admin_edit_category", AdminState.manage_categories)
async def admin_edit_category_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await callback.message.edit_text("Нет категорий для редактирования.",
                                         reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    # Генерация клавиатуры для выбора категории по ID
    markup = await get_category_selection_markup(callback_prefix="edit_cat_select", for_edit_delete=True,
                                                 return_to_admin_categories=True)  # <--- ИСПРАВЛЕНО
    await callback.message.edit_text("Выберите категорию для редактирования (по ID):", reply_markup=markup)
    await state.set_state(AdminState.edit_category_select)


@admin_router.callback_query(F.data.startswith("edit_cat_select::"), AdminState.edit_category_select)
async def admin_edit_category_selected(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("::")[1])
    category = db_utils.get_category_by_id(category_id)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    await state.update_data(editing_category_id=category_id, old_category_title=category['title'])
    await callback.message.edit_text(f"Вы выбрали категорию <b>'{category['title']}'</b>.\n"
                                     "Введите новое название для этой категории:",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_categories")]
                                     ]))
    await state.set_state(AdminState.edit_category_new_title)


@admin_router.message(AdminState.edit_category_new_title)
async def admin_edit_category_set_new_title(message: Message, state: FSMContext):
    new_title = message.text.strip()
    data = await state.get_data()
    category_id = data.get("editing_category_id")

    if category_id is None:
        await message.answer("Произошла ошибка, ID категории не найден. Начните заново.",
                             reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    db_utils.update_category(category_id, new_title)
    await message.answer(
        f"Название категории изменено с <b>'{data['old_category_title']}'</b> на <b>'{new_title}'</b>!",
        reply_markup=get_manage_categories_markup())
    await state.set_state(AdminState.manage_categories)


# Удаление категории
@admin_router.callback_query(F.data == "admin_delete_category", AdminState.manage_categories)
async def admin_delete_category_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    categories = db_utils.get_all_categories_flat()
    if not categories:
        await callback.message.edit_text("Нет категорий для удаления.", reply_markup=get_manage_categories_markup())
        await state.set_state(AdminState.manage_categories)
        return

    # Генерация клавиатуры для выбора категории по ID
    markup = await get_category_selection_markup(callback_prefix="del_cat_select", for_edit_delete=True,
                                                 return_to_admin_categories=True)  # <--- ИСПРАВЛЕНО
    await callback.message.edit_text("Выберите категорию для удаления (по ID). "
                                     "<b>ВНИМАНИЕ:</b> Категорию нельзя удалить, если у нее есть подкатегории или услуги!",
                                     reply_markup=markup)
    await state.set_state(AdminState.delete_category_select)


@admin_router.callback_query(F.data.startswith("del_cat_select::"), AdminState.delete_category_select)
async def admin_delete_category_selected(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("::")[1])
    category = db_utils.get_category_by_id(category_id)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_categories_markup())
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
async def admin_manage_services_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.manage_services)
    await callback.message.edit_text("Управление услугами:", reply_markup=get_manage_services_markup())


# Добавление услуги
@admin_router.callback_query(F.data == "admin_add_service", AdminState.manage_services)
async def admin_add_service_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    categories_exist = db_utils.get_all_categories_flat()
    if not categories_exist:
        await callback.message.edit_text("Нет доступных категорий для добавления услуг. Сначала добавьте категории.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = await get_category_selection_markup(callback_prefix="add_service_cat",
                                                 return_to_admin_services=True)  # <--- ИСПРАВЛЕНО
    await callback.message.edit_text("Выберите категорию, в которую будет добавлена услуга:", reply_markup=markup)
    await state.set_state(AdminState.select_category_for_service)


@admin_router.callback_query(F.data.startswith("add_service_cat::"), AdminState.select_category_for_service)
async def admin_add_service_get_category(callback: CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    await state.update_data(current_service_category_slug=category_slug)
    await callback.message.edit_text(f"Выбрана категория: <b>{category['title']}</b>.\n"
                                     "Теперь введите НАЗВАНИЕ новой услуги:",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                                     ]))
    await state.set_state(AdminState.add_service_name)


@admin_router.message(AdminState.add_service_name)
async def admin_add_service_get_name(message: Message, state: FSMContext):
    service_name = message.text.strip()
    await state.update_data(new_service_name=service_name)
    await message.answer("Введите ЦЕНУ услуги (например, `1500 ₽` или `от 2000 ₽ до 3000 ₽`):",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                         ]))
    await state.set_state(AdminState.add_service_price)


@admin_router.message(AdminState.add_service_price)
async def admin_add_service_get_price(message: Message, state: FSMContext):
    service_price = message.text.strip()
    await state.update_data(new_service_price=service_price)
    await message.answer("Введите ОПИСАНИЕ услуги (необязательно, можно написать `-` или `нет`):",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                         ]))
    await state.set_state(AdminState.add_service_description)


@admin_router.message(AdminState.add_service_description)
async def admin_add_service_get_description(message: Message, state: FSMContext):
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
async def admin_edit_service_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    categories_exist = db_utils.get_all_categories_flat()
    if not categories_exist:
        await callback.message.edit_text("Нет доступных категорий для изменения услуг. Сначала добавьте категории.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = await get_category_selection_markup(callback_prefix="edit_service_cat",
                                                 return_to_admin_services=True)  # <--- ИСПРАВЛЕНО
    await callback.message.edit_text("Выберите категорию, услугу из которой вы хотите изменить:", reply_markup=markup)
    await state.set_state(AdminState.select_category_for_service)


@admin_router.callback_query(F.data.startswith("edit_service_cat::"), AdminState.select_category_for_service)
async def admin_edit_service_select_category(callback: CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    services = db_utils.get_services_by_category_slug(category_slug)
    if not services:
        await callback.message.edit_text(f"В категории <b>'{category['title']}'</b> нет услуг для изменения.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    service_list_text = f"Услуги в категории <b>{category['title']}</b>:\n\n"
    for svc in services:
        markup.inline_keyboard.append(
            [InlineKeyboardButton(text=f"{svc['name']} (ID: {svc['id']})", callback_data=f"edit_svc_id::{svc['id']}")])
        service_list_text += f"ID: {svc['id']} - <b>{svc['name']}</b> - {svc['price']}\n"
    markup.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")])

    await state.update_data(current_service_category_slug_for_edit=category_slug)
    await callback.message.edit_text(service_list_text + "\nВыберите услугу по ID для изменения:", reply_markup=markup)
    await state.set_state(AdminState.edit_service_select)


@admin_router.callback_query(F.data.startswith("edit_svc_id::"), AdminState.edit_service_select)
async def admin_edit_service_select_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    await state.update_data(editing_service_id=service_id, editing_service_data=service)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data="edit_svc_field::name")],
        [InlineKeyboardButton(text="Изменить цену", callback_data="edit_svc_field::price")],
        [InlineKeyboardButton(text="Изменить описание", callback_data="edit_svc_field::description")],
        [InlineKeyboardButton(text="Готово (вернуться к управлению услугами)", callback_data="admin_manage_services")]
    ])
    await callback.message.edit_text(f"Вы выбрали услугу <b>'{service['name']}'</b> (ID: {service['id']}).\n"
                                     f"Что хотите изменить?\n"
                                     f"Текущее название: <b>{service['name']}</b>\n"
                                     f"Текущая цена: <b>{service['price']}</b>\n"
                                     f"Текущее описание: <i>{service['description'] if service['description'] else 'нет'}</i>",
                                     reply_markup=markup)
    await state.set_state(AdminState.edit_service_choose_field)


@admin_router.callback_query(F.data.startswith("edit_svc_field::"), AdminState.edit_service_choose_field)
async def admin_edit_service_choose_field(callback: CallbackQuery, state: FSMContext):
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
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")]
                                     ]))
    await state.set_state(AdminState.edit_service_new_value)


@admin_router.message(AdminState.edit_service_new_value)
async def admin_edit_service_set_new_value(message: Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    service_id = data.get("editing_service_id")
    field_to_edit = data.get("field_to_edit")
    current_service_data = data.get("editing_service_data")

    if not all([service_id, field_to_edit, current_service_data]):
        await message.answer("Произошла ошибка, данные услуги не найдены. Начните заново.",
                             reply_markup=get_manage_services_markup())
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

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data="edit_svc_field::name")],
        [InlineKeyboardButton(text="Изменить цену", callback_data="edit_svc_field::price")],
        [InlineKeyboardButton(text="Изменить описание", callback_data="edit_svc_field::description")],
        [InlineKeyboardButton(text="Готово (вернуться к управлению услугами)", callback_data="admin_manage_services")]
    ])

    await message.answer(
        f"Поле <b>'{field_to_edit}'</b> для услуги <b>'{current_service_data['name']}'</b> обновлено.\n"
        f"Текущее название: <b>{current_service_data['name']}</b>\n"
        f"Текущая цена: <b>{current_service_data['price']}</b>\n"
        f"Текущее описание: <i>{current_service_data['description'] if current_service_data['description'] else 'нет'}</i>\n\n"
        "Что еще хотите изменить или нажмите 'Готово'?", reply_markup=markup)
    await state.set_state(AdminState.edit_service_choose_field)


# Удаление услуги
@admin_router.callback_query(F.data == "admin_delete_service", AdminState.manage_services)
async def admin_delete_service_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    categories_exist = db_utils.get_all_categories_flat()
    if not categories_exist:
        await callback.message.edit_text("Нет доступных категорий для удаления услуг. Сначала добавьте категории.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = await get_category_selection_markup(callback_prefix="del_service_cat",
                                                 return_to_admin_services=True)  # <--- ИСПРАВЛЕНО
    await callback.message.edit_text("Выберите категорию, услугу из которой вы хотите удалить:", reply_markup=markup)
    await state.set_state(AdminState.select_category_for_service)


@admin_router.callback_query(F.data.startswith("del_service_cat::"), AdminState.select_category_for_service)
async def admin_delete_service_select_category(callback: CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("::")[1]
    category = db_utils.get_category_by_slug(category_slug)
    if not category:
        await callback.message.edit_text("Категория не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    services = db_utils.get_services_by_category_slug(category_slug)
    if not services:
        await callback.message.edit_text(f"В категории <b>'{category['title']}'</b> нет услуг для удаления.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    service_list_text = f"Услуги в категории <b>{category['title']}</b>:\n\n"
    for svc in services:
        markup.inline_keyboard.append(
            [InlineKeyboardButton(text=f"{svc['name']} (ID: {svc['id']})", callback_data=f"del_svc_id::{svc['id']}")])
        service_list_text += f"ID: {svc['id']} - <b>{svc['name']}</b> - {svc['price']}\n"
    markup.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="admin_manage_services")])

    await state.update_data(current_service_category_slug_for_edit=category_slug)
    await callback.message.edit_text(service_list_text + "\nВыберите услугу по ID для удаления:", reply_markup=markup)
    await state.set_state(AdminState.delete_service_select)


@admin_router.callback_query(F.data.startswith("del_svc_id::"), AdminState.delete_service_select)
async def admin_delete_service_confirm(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("::")[1])
    service = db_utils.get_service_by_id(service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена. Попробуйте еще раз.",
                                         reply_markup=get_manage_services_markup())
        await state.set_state(AdminState.manage_services)
        return

    db_utils.delete_service(service_id)
    await callback.message.edit_text(f"Услуга <b>'{service['name']}'</b> успешно удалена.",
                                     reply_markup=get_manage_services_markup())
    await state.set_state(AdminState.manage_services)


# --- ОБРАБОТЧИКИ ДЛЯ ИЗМЕНЕНИЯ ПАРОЛЯ ---
@admin_router.callback_query(F.data == "admin_change_password", AdminState.in_admin_panel)
async def admin_change_password_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения пароля админа."""
    await callback.answer()
    await callback.message.edit_text("Пожалуйста, введите НОВЫЙ пароль для админ-панели:",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Отмена", callback_data="admin_main_menu")]
                                     ]))
    await state.set_state(AdminState.change_password_waiting_for_new_password)


@admin_router.message(AdminState.change_password_waiting_for_new_password)
async def admin_change_password_get_new(message: Message, state: FSMContext):
    """Получает новый пароль и обновляет его в config.json."""
    new_password = message.text.strip()

    if not new_password:
        await message.answer("Пароль не может быть пустым. Пожалуйста, введите новый пароль:")
        return

    config_manager.set_setting('ADMIN_PASSWORD', new_password)

    await message.answer(f"Пароль администратора успешно изменен на: <code>{new_password}</code>",
                         reply_markup=get_admin_main_markup())
    await state.set_state(AdminState.in_admin_panel)
