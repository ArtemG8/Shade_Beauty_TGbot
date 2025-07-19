from aiogram.fsm.state import State, StatesGroup

class BookingState(StatesGroup):
    choosing_category = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_comment = State()
    entering_phone = State()
    confirming_booking = State()

