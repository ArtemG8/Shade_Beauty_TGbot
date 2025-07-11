import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
# Импортируем InputMediaPhoto для отправки медиагруппы
from aiogram.types import InputMediaPhoto

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота, полученный от BotFather
BOT_TOKEN = "8099050356:AAHTmPGZ72er-_tguInYs8raDWHH9We1qcI"

# Замените 'YOUR_ADMIN_USERNAME' на реальный юзернейм администратора Telegram (без символа '@')
ADMIN_USERNAME = "ArtemArtem11111"  # Например: "my_salon_admin"

# Список URL-адресов фотографий салона
PHOTO_URLS = [
    "https://optim.tildacdn.com/tild3437-6533-4432-b933-343832636236/-/format/webp/DSCF3359.JPG.webp",
    "https://optim.tildacdn.com/tild3237-3563-4166-b939-333738666137/-/format/webp/DSCF3302.JPG.webp",
    "https://optim.tildacdn.com/tild3230-3433-4432-b835-303533326134/-/format/webp/DSCF3267.JPG.webp",
    "https://optim.tildacdn.com/tild6361-6564-4162-a236-336537356635/-/format/webp/DSCF3182.JPG.webp",
    "https://optim.tildacdn.com/tild6366-3739-4831-b863-366664633632/-/format/webp/DSCF3400.JPG.webp",
    "https://optim.tildacdn.com/tild6364-6436-4638-b036-396462623662/-/format/webp/DSCF3293.JPG.webp"
]

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
            [types.InlineKeyboardButton(text="✨ Наши услуги", callback_data="show_services")],
            [types.InlineKeyboardButton(text="📸 Фотографии салона", callback_data="show_salon_photos")],
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
        # Если это сообщение (например, команда /start), отправляем новое сообщение
        await target.answer(welcome_message, reply_markup=markup)
    elif isinstance(target, types.CallbackQuery):
        # Если это CallbackQuery (например, нажатие "Назад"), пытаемся отредактировать
        # сообщение, из которого пришел callback.
        # В случае, если сообщение не может быть отредактировано (например, это медиагруппа),
        # отправляем новое сообщение.
        try:
            await target.message.edit_text(welcome_message, reply_markup=markup)
        except Exception:
            await target.message.answer(welcome_message, reply_markup=markup)


# --- Обработчики команд и кнопок ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    Обработчик команды /start. Отправляет приветственное сообщение с инлайн-кнопками.
    """
    await send_main_menu(message)


@dp.callback_query(F.data == "show_services")
async def process_services_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Наши услуги".
    """
    await callback.answer(text="Загрузка услуг...", show_alert=False)

    # Добавляем кнопку "Назад"
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )

    await callback.message.edit_text(
        "<b>💎 Наши услуги:</b>\n"
        "Здесь будет подробная информация о наших услугах (стрижки, окрашивания, маникюр, педикюр и т.д.).\n"
        "Скоро мы добавим полный прейскурант и описания! 😊",
        reply_markup=markup
    )


@dp.callback_query(F.data == "show_salon_photos")
async def process_photos_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Фотографии салона". Отправляет медиагруппу с фото.
    """
    await callback.answer(text="Загрузка фотографий...", show_alert=False)

    # Создаем список объектов InputMediaPhoto из URL-адресов
    media_group = []
    for url in PHOTO_URLS:
        media_group.append(InputMediaPhoto(media=url))

    # Отправляем медиагруппу (все фото одним сообщением)
    await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)

    # Отправляем отдельное сообщение с кнопкой "Назад" после фотографий
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")],
        ]
    )
    await callback.message.answer(
        "Надеемся, вам понравились фотографии нашего салона! ✨",
        reply_markup=markup
    )
    # Важно: Не используем callback.message.edit_text() здесь, так как мы только что
    # отправили новую группу сообщений.


@dp.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Назад в главное меню".
    """
    await callback.answer()  # Отвечаем на callback, чтобы убрать "часики" с кнопки
    await send_main_menu(callback)  # Возвращаем пользователя в главное меню


# --- Основная функция запуска бота ---

async def main() -> None:
    # Запускаем все зарегистрированные обработчики и начинаем опрос новых обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Бот запускается... Нажмите Ctrl+C для остановки.")
    asyncio.run(main())

