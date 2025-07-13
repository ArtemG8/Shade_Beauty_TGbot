import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InputMediaPhoto

from services_data import SERVICES_DATA, PHOTO_URLS
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота, полученный от BotFather
BOT_TOKEN = "8099050356:AAHTmPGZ72er-_tguInYs8raDWHH9We1qcI"

# Замените 'YOUR_ADMIN_USERNAME' на реальный юзернейм администратора Telegram (без символа '@')
ADMIN_USERNAME = "ArtemArtem11111"  # Например: "my_salon_admin"



# Структура данных для услуг (порядок изменен для "Дополнительных услуг")


# Включаем логирование, чтобы видеть информацию о входящих обновлениях в консоли
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Инициализация объекта Bot и Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


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
            [types.InlineKeyboardButton(text="📍 Как до нас добраться?", url = "https://yandex.ru/maps/54/yekaterinburg/?from=api-maps&ll=60.607417%2C56.855225&mode=routes&origin=jsapi_2_1_79&rtext=~56.855225%2C60.607417&rtt=mt&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D176318285490&z=13.89")],
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


# --- Обработчики команд и кнопок ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    Обработчик команды /start. Отправляет приветственное сообщение с инлайн-кнопками.
    """
    await send_main_menu(message)


@dp.callback_query(F.data == "show_services_main_menu")
async def process_services_main_menu_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Наши услуги".
    Показывает основные категории услуг.
    """
    await callback.answer(text="Загрузка категорий услуг...", show_alert=False)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])

    for category_key, category_data in SERVICES_DATA.items():
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text=f"✨ {category_data['title']}", callback_data=f"cat::{category_key}")
            # ИЗМЕНЕНО
        ])

    markup.inline_keyboard.append([
        types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    ])

    await callback.message.edit_text(
        "<b>💎 Наши услуги:</b>\n"
        "Выберите интересующую категорию:",
        reply_markup=markup
    )


@dp.callback_query(F.data.startswith("cat::"))  # ИЗМЕНЕНО
async def process_service_category_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку категории услуг.
    Либо показывает подкатегории, либо выводит список услуг.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    category_key = callback.data.split("::")[1]  # ИЗМЕНЕНО
    category_data = SERVICES_DATA.get(category_key)

    if not category_data:
        await callback.message.answer("Извините, информация по данной категории не найдена.")
        await send_main_menu(callback)
        return

    if "sub_categories" in category_data:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[])
        for sub_key, sub_data in category_data["sub_categories"].items():
            # ИЗМЕНЕНО: Формат callback_data для подкатегории
            markup.inline_keyboard.append([
                types.InlineKeyboardButton(text=f"▪️ {sub_data['title']}",
                                           callback_data=f"sub::{category_key}::{sub_key}")
            ])
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг", callback_data="show_services_main_menu")
        ])

        await callback.message.edit_text(
            f"<b>{category_data['title']}:</b>\n"
            "Выберите подкатегорию:",
            reply_markup=markup
        )
    else:
        service_text = f"<b>{category_data['title']}:</b>\n\n"
        for item in category_data["items"]:
            service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
            if "description" in item:
                service_text += f"   <i>{item['description']}</i>\n"

        markup = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад к категориям услуг",
                                            callback_data="show_services_main_menu")],
            ]
        )
        await callback.message.edit_text(service_text, reply_markup=markup)


@dp.callback_query(F.data.startswith("sub::"))  # ИЗМЕНЕНО
async def process_service_subcategory_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку подкатегории услуг.
    Выводит список услуг для этой подкатегории.
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    # ИЗМЕНЕНО: Использование split('::') для надежного разбора
    parts = callback.data.split('::')

    # parts будет ['sub', 'parent_category_key', 'subcategory_key']
    if len(parts) < 3:
        await callback.message.answer("Извините, некорректные данные подкатегории.")
        await send_main_menu(callback)
        return

    parent_category_key = parts[1]
    subcategory_key = parts[2]

    parent_category_data = SERVICES_DATA.get(parent_category_key)
    if not parent_category_data or "sub_categories" not in parent_category_data:
        await callback.message.answer("Извините, ошибка в данных родительской категории. Попробуйте еще раз.")
        await send_main_menu(callback)
        return

    subcategory_data = parent_category_data["sub_categories"].get(subcategory_key)

    if not subcategory_data:
        await callback.message.answer("Извините, информация по данной подкатегории не найдена.")
        await send_main_menu(callback)
        return

    service_text = f"<b>{subcategory_data['title']}:</b>\n\n"
    for item in subcategory_data["items"]:
        service_text += f"▪️ <b>{item['name']}</b> - {item['price']}\n"
        if "description" in item:
            service_text += f"   <i>{item['description']}</i>\n"

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            # ИЗМЕНЕНО: Кнопка "Назад" к родительской категории
            [types.InlineKeyboardButton(text="⬅️ Назад к подкатегориям", callback_data=f"cat::{parent_category_key}")],
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
async def process_back_to_main_menu(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Назад в главное меню".
    """
    await callback.answer()
    await send_main_menu(callback)


# --- Основная функция запуска бота ---

async def main() -> None:
    # Запускаем все зарегистрированные обработчики и начинаем опрос новых обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Бот запускается... Нажмите Ctrl+C для остановки.")
    asyncio.run(main())

