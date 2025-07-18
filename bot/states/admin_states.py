# your_bot_project/states/admin_states.py
from aiogram.fsm.state import State, StatesGroup

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

