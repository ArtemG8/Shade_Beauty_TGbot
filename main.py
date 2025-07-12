import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
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

# Структура данных для услуг (порядок изменен для "Дополнительных услуг")
SERVICES_DATA = {
    "стрижки": {
        "title": "Стрижки",
        "sub_categories": {
            "стрижки_женские": {
                "title": "Женские стрижки",
                "items": [
                    {"name": "Стрижка женская ТОП - стилист", "price": "2800 ₽"},
                    {"name": "Стрижка женская Стилист", "price": "2300 ₽"},
                    {"name": "Подравнивание кончиков волос ТОП - стилист/стилист", "price": "1200 ₽"},
                    {"name": "Стрижка челки ТОП - стилист", "price": "1000 ₽"},
                ]
            },
            "стрижки_мужские": {
                "title": "Мужские стрижки",
                "items": [
                    {"name": "Стрижка мужская ТОП - стилист", "price": "2000 ₽"},
                    {"name": "Стрижка мужская Стилист", "price": "1800 ₽"},
                    {"name": "Оформление бороды ТОП - стилист/стилист", "price": "1000 ₽"},
                    {"name": "Камуфляж бороды ТОП - стилист/стилист", "price": "1000 ₽"},
                    {"name": "Мужской камуфляж", "price": "2000 ₽"},
                ]
            },
            "стрижки_детские": {
                "title": "Детские стрижки",
                "items": [
                    {"name": "Стрижка детская девочки от 6 до 12 лет", "price": "1200 ₽"},
                    {"name": "Стрижка детская мальчика от 6 до 12 лет", "price": "1200 ₽"},
                    {"name": "Подравнивание кончиков волос девочки", "price": "1000 ₽"},
                    {"name": "Стрижка чёлки детская", "price": "600 ₽"},
                ]
            },
        }
    },
    "окрашивание": {
        "title": "Окрашивание",
        "items": [
            {"name": "Прикорневое окрашивание", "price": "от 4500 ₽"},
            {"name": "Тонирование короткие", "price": "от 5000 ₽"},
            {"name": "Tонирование средние", "price": "от 5500 ₽"},
            {"name": "Тонирование длинные", "price": "от 6000 ₽"},
            {"name": "Окрашивание короткие в 1 тон", "price": "от 6000 ₽"},
            {"name": "Окрашивание средние в 1 тон", "price": "от 7000 ₽"},
            {"name": "Окрашивание длинные в 1 тон", "price": "от 8000 ₽"},
            {"name": "Сложное окрашивание в 2 этапа", "price": "от 10000 ₽ до 30000 ₽"},
            {"name": "Air touch «воздушное прикосновение»", "price": "от 12000 ₽ до 35000 ₽"},
            {"name": "Детский контуринг", "price": "от 4500 ₽"},
        ]
    },
    "био_завивка": {
        "title": "Био-завивка",
        "sub_categories": {
            "био_завивка_davines": {
                "title": "Био-завивка DAVINES",
                "items": [
                    {"name": "Мужская частичная", "price": "от 5000 ₽"},
                    {"name": "Короткие волосы", "price": "от 6500 ₽"},
                    {"name": "Средние волосы", "price": "от 8000 ₽"},
                    {"name": "Длинные волосы", "price": "от 9000 ₽"},
                ]
            },
            "био_завивка_женская": {
                "title": "Биозавивка волос женская",
                "items": [
                    {"name": "Биозавивка волос женская", "price": "от 5000 ₽"},
                ]
            }
        }
    },
    "эстетика_волос": {
        "title": "Эстетика волос",
        "items": [
            {"name": "LOréal Professionnel Scalp - диагностика + уход для кожи головы", "price": "1500 ₽ - 3000 ₽",
             "description": "Подробнее о услуге: [LOréal Professionnel Scalp]"},
            {"name": "DAVINES NATURALTECH TAILORING", "price": "3000₽ - 6500₽",
             "description": "Рецепт коктейля для волос подбирается в зависимости от базовой потребности в уходе и дополнительного ожидаемого эффекта.\nРезультат: 1. Глубокое увлажнение 2. Восстановление структуры волос (укрепление) 3. Контроль пушистых и пористых волос 4. Блеск 5. Увеличение объёма 6. Сияние блонда\nВ уход входит: 1. Мытьё головы 2. Сушка 3. Укладка по форме стрижки 4. Консультация по домашнему уходу\n*стоимость зависит от расхода материала, густоты и длины волос"},
            {"name": "Davines OI OIL", "price": "3000₽ - 6500₽"},
            {"name": "DAVINES HEART OF GLASS", "price": "3000₽ - 6500₽"},
            {"name": "DAVINES NOURISHING", "price": "3000₽ - 6500₽"},
            {"name": "DAVINES REPLUMPING", "price": "3000₽ - 6500₽",
             "description": "Предназначен для создания плотности, объёма, интенсивного увлажнения и эластичности волос.\nВ уход входит: 1. Мытьё головы 2. Сушка 3. Укладка по форме стрижки 4. Консультация по домашнему уходу\n*стоимость зависит от расхода материала, густоты и длины волос"},
            {"name": "DAVINES скрабирование", "price": "от 2500₽"},
            {"name": "Уходы L'Oréal Professionnel", "price": "2500 ₽ - 5500 ₽"},
        ]
    },
    "укладки": {
        "title": "Укладки",
        "items": [
            {"name": "Укладка повседневная", "price": "2000 ₽"},
            {"name": "Укладка коктейльная", "price": "от 2500 ₽ до 3500 ₽"},
            {"name": "Укладка STEAMPOD", "price": "2500₽ - 4000₽",
             "description": "Щадящее выпрямление волос паровым стайлером SteamPod\n-Создает локоны\n-Восстанавливает волосы\n-Стойкость укладки до 72ч\n*Стоимость зависит от расхода материалов, густоты и длинны волос."},
        ]
    },
    "маникюр": {
        "title": "Маникюр",
        "sub_categories": {
            "маникюр_4_руки": {
                "title": "Маникюр + педикюр в 4 руки",
                "items": [
                    {"name": "Маникюр + педикюр в 4 руки с покрытием гель/лак", "price": "5800₽ - 6600₽",
                     "description": "*стоимость варьируется в зависимости от выбранного педикюра и наличия дополнительных услуг"},
                    {"name": "Маникюр + педикюр в 4 руки без покрытия гель/лак", "price": "3900₽ - 4700₽",
                     "description": "*стоимость варьируется в зависимости от выбранного педикюра и наличия дополнительных услуг"},
                ]
            },
            "маникюр_эксперт_мастер": {
                "title": "Маникюр (Эксперт мастер)",
                "items": [
                    {"name": "Маникюр Европейский/Аппаратный", "price": "1500 ₽"},
                    {"name": "Маникюр + покрытие/гель-лак", "price": "2800 ₽"},
                    {"name": "Маникюр Японский Masura", "price": "2900 ₽"},
                    {"name": "Французский маникюр", "price": "3300 ₽"},
                    {"name": "Маникюр мужской", "price": "1700 ₽"},
                    {"name": "Маникюр детский", "price": "1200 ₽",
                     "description": "*не включает в себя покрытие обычным лаком"},
                    {"name": "Маникюр + наращивание ногтей",
                     "price": "S - 4000 ₽; M - 4500 ₽; L - 5000 ₽; XL - от 5500 ₽"},
                ]
            },
            "маникюр_топ_мастер": {
                "title": "Маникюр (Топ мастер)",
                "items": [
                    {"name": "Маникюр Европейский/Аппаратный", "price": "1300 ₽"},
                    {"name": "Маникюр + покрытие/гель-лак", "price": "2200 ₽"},
                    {"name": "Маникюр Японский Masura", "price": "2600 ₽"},
                    {"name": "Французский маникюр", "price": "3000 ₽"},
                    {"name": "Маникюр мужской", "price": "1500 ₽"},
                    {"name": "Маникюр детский", "price": "1000 ₽",
                     "description": "* не включает в себя покрытие обычным лаком"},
                    {"name": "Маникюр + наращивание ногтей", "price": "S - 4000₽; M - 4500₽; L - 5000₽; XL - от 5500₽"},
                ]
            },
            "маникюр_мастер": {
                "title": "Маникюр (Мастер)",
                "items": [
                    {"name": "Маникюр Европейский/Аппаратный", "price": "1100 ₽"},
                    {"name": "Маникюр + покрытие/гель-лак", "price": "2200 ₽"},
                    {"name": "Маникюр Японский Masura", "price": "2300 ₽"},
                    {"name": "Французский маникюр", "price": "2700 ₽"},
                    {"name": "Маникюр мужской", "price": "1200 ₽"},
                    {"name": "Маникюр детский", "price": "700 ₽"},
                    {"name": "Маникюр + наращивание ногтей", "price": "S - 4000₽; M - 4500₽; L - 5000₽; XL - от 5500₽"},
                ]
            },
        }
    },
    "педикюр": {
        "title": "Педикюр",
        "sub_categories": {
            "педикюр_общий": {
                "title": "Педикюр (Общие услуги)",
                "items": [
                    {"name": "Лёгкая обработка стопы", "price": "2000 ₽",
                     "description": "для всех категорий мастеров одна цена"},
                    {"name": "Обработка сложной стопы", "price": "2300 ₽",
                     "description": "для всех категорий мастеров одна цена"},
                ]
            },
            "педикюр_эксперт_мастер": {
                "title": "Педикюр (Эксперт мастер)",
                "items": [
                    {"name": "Экспресс педикюр без покрытия", "price": "2200 ₽"},
                    {"name": "Экспресс педикюр с покрытием", "price": "2500 ₽"},
                    {"name": "Педикюр Европейский/Комбинированный", "price": "3000 ₽ - 3500 ₽"},
                    {"name": "Педикюр + покрытие / гель-лак", "price": "3300 ₽ - 3800 ₽"},
                    {"name": "Педикюр французский", "price": "3600 ₽ - 4100 ₽"},
                    {"name": "Педикюр японский Masura пальчики", "price": "2600 ₽"},
                    {"name": "Педикюр японский Masura полный", "price": "3300 ₽ - 3800 ₽"},
                    {"name": "педикюр мужской классический", "price": "3000₽ - 3500₽"},
                    {"name": "Golden Trace с однотонным покрытием", "price": "3800 ₽"},
                    {"name": "Golden Trace без покрытия", "price": "3300 ₽"},
                    {"name": "Golden Trace мужской", "price": "3800 ₽"},
                ]
            },
            "педикюр_топ_мастер": {
                "title": "Педикюр (Топ мастер)",
                "items": [
                    {"name": "Экспресс педикюр без покрытия гель/лак", "price": "1800 ₽"},
                    {"name": "Экспресс педикюр с однотонным покрытием гель/лак", "price": "2200 ₽"},
                    {"name": "Педикюр Европейский/Комбинированный", "price": "2600 ₽ - 3100 ₽"},
                    {"name": "Педикюр + покрытие / гель-лак", "price": "3000 ₽ - 3500 ₽"},
                    {"name": "Педикюр французский", "price": "3300 ₽ - 3800 ₽"},
                    {"name": "Педикюр японский Masura пальчики", "price": "2300 ₽"},
                    {"name": "Педикюр японский Masura полный", "price": "3000 ₽ - 3500 ₽"},
                    {"name": "Педикюр мужской классический", "price": "2800 ₽ - 3300 ₽"},
                    {"name": "Golden Trace с однотонным покрытием", "price": "3500 ₽"},
                    {"name": "Golden Trace без покрытия", "price": "3300 ₽"},
                    {"name": "Golden Trace мужской", "price": "3800 ₽"},
                ]
            },
        }
    },
    "брови_ресницы": {
        "title": "Оформление бровей и ламинирование ресниц",
        "items": [
            {"name": "Оформление бровей", "price": "1000 ₽"},
            {"name": "Окрашивание бровей", "price": "1200 ₽"},
            {"name": "Окрашивание и оформление бровей", "price": "2000 ₽"},
            {"name": "Долговременная укладка и оформление бровей", "price": "2700 ₽"},
            {"name": "Долговременная укладка бровей", "price": "2000 ₽"},
            {"name": "Долговременная укладка, оформление и окрашивание бровей", "price": "3200 ₽"},
            {"name": "Ламинирование ресниц", "price": "2500 ₽"},
            {"name": "Комплекс «SPA для бровей»", "price": "2500 ₽"},
            {"name": "Прореживание, оформление и окрашивание бровей", "price": "2500 ₽"},
            {"name": "Прореживание и оформление бровей", "price": "1500 ₽"},
            {"name": "Прореживание", "price": "800 ₽"},
            {"name": "Окрашивание ресниц", "price": "800 ₽"},
            {"name": "Снятие нарощенных ресниц", "price": "700 ₽"},
        ]
    },
    "эстетика_лица": {
        "title": "Эстетика лица",
        "items": [
            {"name": "Лечение акне", "price": "Старший косметолог 3500 ₽; косметолог 3000 ₽",
             "description": "Что входит: консультация, определение причины, диагностика, подбор домашней уходовой косметики, работа со шрамами и постакне, назначение лечения.\nВсе последующие посещения: 500 ₽"},
            {"name": "Атравматическая чистка", "price": "Старший косметолог 3500 ₽ ; косметолог 3000 ₽",
             "description": "Бережное очищение кожи без использования механического воздействия. Включает: пилинг, маски, очищение, увлажнение и восстановление. Подходит для всех типов кожи. Используется космецевтика от pleyana, je demeure и Christina."},
            {"name": "Комбинированная чистка", "price": "Старший косметолог 4000₽; косметолог 3500₽"},
            {"name": "Чистка ультразвуковая", "price": "Старший косметолог 3000₽; косметолог 2500₽"},
            {"name": "Механическая чистка", "price": "Старший косметолог 3300₽; косметолог 2800₽"},
            {"name": "Удаление милиумов", "price": "Старший косметолог 1000₽; косметолог 500₽"},
            {"name": "Пилинг по типу кожи", "price": "Старший косметолог 2000₽ - 6500₽; косметолог 1500₽ - 6000₽"},
            {"name": "Карбокситерапия", "price": "4000 ₽"},
            {"name": "Фототерапия", "price": "Старший косметолог 1200₽; косметолог 700₽",
             "description": "Воздействие на кожу световыми волнами. Эффективен для: сосудистых звездочек, веснушек, морщин, расширенных пор, постакне."},
            {"name": "Маски по типу кожи", "price": "Старший косметолог 1000₽ - 1500₽; косметолог 500₽ - 1000₽"},
            {"name": "Альгинатная маска", "price": "Старший косметолог 1200₽; косметолог 700₽"},
            {"name": "Массаж шея + декольте", "price": "Старший косметолог 2000₽; косметолог 1500₽"},
            {"name": "SPA терапия для лица", "price": "Старший косметолог 5000₽; косметолог 4500₽",
             "description": "Включает: расслабляющий массаж (руки, декольте, лицо, голова), пилинг, водорослевая маска. Направлена на лифтинг, сияние и увлажнение."},
            {"name": "Глубокотканный массаж лица", "price": "4000 ₽",
             "description": "Задача: освободить ткани от фиброзов и токсинов, расслабить мышечные спазмы, улучшить тонус и эластичность кожи, активизировать работу всех мышц лица, шеи, декольте и головы."},
            {"name": "Массаж лица классический", "price": "Старший косметолог 2500₽; косметолог 1900₽"},
            {"name": "Французский лифтинг массаж лица", "price": "Старший косметолог 3200₽; косметолог 2700₽"},
            {"name": "Буккальный массаж лица", "price": "Старший косметолог 2800₽; косметолог 2300₽"},
            {"name": "Японский массаж лица", "price": "Старший косметолог 3300₽; косметолог 2800₽"},
            {"name": "Уход ANESI", "price": "Косметолог 3500₽"},
            {"name": "Лечебная процедура противовоспалительная дарсонваль",
             "price": "Старший косметолог 1200₽; косметолог 700₽"},
            {"name": "SHARM - Механическая дерматония лица",
             "price": "Старший косметолог 2200₽ - 3200₽; косметолог 1700₽ - 2700₽",
             "description": "Аппаратная услуга: лимфодренаж, расслабление мышц, воздействие на нервно-рецепторный аппарат, повышает упругость кожи, устраняет отёчность. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "HARM БМС - биомеханическая стимуляция",
             "price": "Старший косметолог 2700₽ - 3700₽; косметолог 2200₽ - 3200₽",
             "description": "Аппаратная процедура: воздействие на мышцы, нормализация цвета кожи, восстановление овала лица, улучшение состояния сосудов головного мозга. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM - Лимфодренаж, магнитотерапия", "price": "Старший косметолог 2700₽; косметолог 2200₽",
             "description": "Аппаратная процедура: очищает ткани, улучшает микроциркуляцию, регенерация тканей, уменьшение отёков, расслабление мышц. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM – Микродермобразия", "price": "Старший косметолог 1700₽ - 2200₽; косметолог 1200₽ - 1700₽",
             "description": "Безболезненная, атравматичная процедура: отшелушивание ороговевшего слоя, сглаживание неровностей, удаление пигментных пятен. Противопоказания: ОРВИ, воспаления, герпес, опухоли."},
        ]
    },
    "эстетика_тела": {
        "title": "Эстетика тела",
        "items": [
            {"name": "Прессотерапия", "price": "1500₽ - 3500₽; косметолог 1000₽ - 3000₽",
             "description": "*Стоимость зависит от зоны тела и длительности услуги"},
            {"name": "SHARM - шейно-воротниковая зона", "price": "Старший косметолог 2500₽; косметолог 2000₽",
             "description": "Аппаратная услуга: расслабляет, разгоняет лимфоток, кровеносную систему, расслабляет спазмы мышц, сгоняет подкожно-жировую клетчатку и возвращает тело в здоровое состояние. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM – руки", "price": "Старший косметолог 2200₽ - 3000₽; косметолог 1700₽ - 2500₽",
             "description": "Аппаратная услуга: расслабляет, разгоняет лимфоток, кровеносную систему, расслабляет спазмы мышц, сгоняет подкожно-жировую клетчатку. 30 мин - 1700; 1 час - 2500. Рекомендуется выполнять в комплексе со спиной или лопатками. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM – ноги", "price": "Старший косметолог 3200₽; косметолог 2700₽",
             "description": "Аппаратная услуга: расслабляет, разгоняет лимфоток, кровеносную систему, расслабляет спазмы мышц, сгоняет подкожно-жировую клетчатку. При болезненности ног – рекомендуется делать в комплексе со спиной. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM – спина", "price": "Старший косметолог 3500₽; косметолог 3000₽",
             "description": "Аппаратная услуга: расслабляет, разгоняет лимфоток, кровеносную систему, расслабляет спазмы мышц, сгоняет подкожно-жировую клетчатку. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM – комплекс", "price": "Старший косметолог 4000₽ – 4200₽; косметолог 3500₽ - 3700₽",
             "description": "Комплекс аппаратного массажа тела: 1) руки + спина 3500, 1 час; 2) шейно-воротниковая зона + руки 3500, 1 час; 3) ноги + спина 3700, 1,5 часа; 4) шейно-воротниковая зона + спина 3500, 1,5 часа. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "SHARM + японское водорослевое обёртывание", "price": "Старший косметолог 6500₽; косметолог 6000₽",
             "description": "В комплекс входит: массаж аппаратом sharm, скрабирование, обёртывание японской ламинарией, ароматерапия, душ, крем для тела. Противопоказания: ОРВИ, воспаления, опухоли."},
            {"name": "Водорослевое обёртывание", "price": "Старший косметолог 3500₽; косметолог 3000₽",
             "description": "Обёртывание японской ламинарией устраняет отёки, регенерирует и омолаживает кожу, корректирует проблемные зоны, восстанавливает упругость. Ламинария ангуста - увлажняет."},
            {"name": "Массаж шейно-воротниковой зоны", "price": "Старший косметолог 2000₽; косметолог 1500₽"},
            {"name": "Релакс массаж спины", "price": "2500 ₽"},
            {"name": "Массаж спины лечебный", "price": "3500 ₽",
             "description": "Подходит при наличии болезненности в спине"},
            {"name": "Массаж рук", "price": "от 1500 ₽ до 2000 ₽", "description": "Женский – 1500 ₽; Мужской – 2000 ₽"},
            {"name": "Массаж ног", "price": "3200 ₽", "description": "Массаж выполняется от стоп до ягодиц"},
            {"name": "Массаж колен лечебный", "price": "4000 ₽",
             "description": "Включает: массаж стоп, проработку напряженных мышц, проработку фасций и проработку лодыжек"},
        ]
    },
    "депиляция_воском": {
        "title": "Депиляция воском (горячим/тёплым)",
        "items": [
            {"name": "Депиляция подмышечных впадин (женская)", "price": "900 ₽"},
            {"name": "Депиляция подмышечных впадин (мужская)", "price": "1100 ₽"},
            {"name": "Депиляция голени", "price": "1200 ₽"},
            {"name": "Депиляция ног полностью", "price": "2300 ₽"},
            {"name": "Депиляция рук до локтя", "price": "1100 ₽"},
            {"name": "Депиляция рук полностью", "price": "1700 ₽"},
            {"name": "Удаление усиков", "price": "500 ₽"},
            {"name": "Удаление волос с овала лица", "price": "700 ₽"},
            {"name": "Удаление волос с подбородка", "price": "600 ₽"},
            {"name": "Удаление волос из носа", "price": "500 ₽"},
        ]
    },
    "дополнительные_услуги": {  # Перемещено в конец
        "title": "Дополнительные услуги",
        "items": [
            {"name": "Покрытие одного ногтя гель-лаком", "price": "250 ₽"},
            {"name": "Покрытие всех ногтей обычным лаком", "price": "400 ₽"},
            {"name": "Парафинотерапия", "price": "700 ₽"},
            {"name": "Опил формы", "price": "200 ₽"},
            {"name": "Снятие покрытия", "price": "500 ₽",
             "description": "*снятие чужого покрытия или нашего, без последующего покрытия гель-лак"},
        ]
    },
}

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
    Обработчик нажатия на кнопку "Фотографии салона". Отправляет медиагруппу с фото.
    """
    await callback.answer(text="Загрузка фотографий...", show_alert=False)

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

