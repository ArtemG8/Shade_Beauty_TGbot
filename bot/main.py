# your_bot_project/bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery # <--- Явный импорт типов

# Импортируем модули из нашего проекта
import config_manager
import db_utils
from handlers import admin, users
from states.admin_states import AdminState
from states.user_states import BookingState
from keyboards.inline import send_main_menu # Вспомогательная функция из keyboards

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Инициализация объекта Bot и Dispatcher
bot = Bot(token=config_manager.get_setting('BOT_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Регистрируем роутеры из наших модулей
dp.include_router(admin.admin_router)
dp.include_router(users.user_router)


# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start. Отправляет приветственное сообщение с инлайн-кнопками.
    """
    await state.clear() # Очищаем все предыдущие состояния
    # Теперь передаем admin_username напрямую, как ожидает send_main_menu
    await send_main_menu(target=message, admin_username=config_manager.get_setting('ADMIN_USERNAME'))

# Обработчик кнопки "Назад в главное меню"
@dp.callback_query(F.data == "back_to_main_menu", ~StateFilter(AdminState, BookingState))
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик нажатия на кнопку "Назад в главное меню" для ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ.
    Не срабатывает, если пользователь находится в любом админском или любом состоянии записи FSM.
    """
    await state.clear()
    await callback.answer()
    # Теперь передаем admin_username напрямую, как ожидает send_main_menu
    await send_main_menu(target=callback, admin_username=config_manager.get_setting('ADMIN_USERNAME'))

async def main() -> None:
    # Инициализация базы данных
    if hasattr(db_utils, 'init_db'):
        db_utils.init_db()

    # Для отправки уведомлений админу, лучше хранить ID, а не username.
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

