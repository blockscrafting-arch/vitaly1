"""Клавиатуры разделов меню в личке."""
from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def main_menu_keyboard(channel_url: str) -> InlineKeyboardBuilder:
    """Главное меню: Напитки, Путешествия, Лайфхаки, Для удалёнки, Сразу в канал."""
    b = InlineKeyboardBuilder()
    b.row(
        CallbackButton(text="Напитки", payload="section:drinks"),
        CallbackButton(text="Путешествия", payload="section:travel"),
    )
    b.row(
        CallbackButton(text="Лайфхаки", payload="section:lifehack"),
        CallbackButton(text="Для удалёнки", payload="section:remote"),
    )
    b.row(LinkButton(text="Сразу в канал", url=channel_url))
    return b


def drinks_keyboard() -> InlineKeyboardBuilder:
    """Напитки: Что пить в стране, Локальный кофе, Чай и рынки, Бары и коктейли, Назад."""
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="Что пить в стране", payload="item:drinks:what_drink"))
    b.row(CallbackButton(text="Локальный кофе", payload="sub:drinks:coffee"))
    b.row(CallbackButton(text="Чай и рынки", payload="item:drinks:tea_markets"))
    b.row(CallbackButton(text="Бары и коктейли", payload="item:drinks:bars"))
    b.row(CallbackButton(text="Назад", payload="main"))
    return b


def coffee_countries_keyboard() -> InlineKeyboardBuilder:
    """Локальный кофе: Япония, Таиланд, Турция, Португалия, Назад."""
    b = InlineKeyboardBuilder()
    b.row(
        CallbackButton(text="Япония", payload="item:drinks:coffee:japan"),
        CallbackButton(text="Таиланд", payload="item:drinks:coffee:thailand"),
    )
    b.row(
        CallbackButton(text="Турция", payload="item:drinks:coffee:turkey"),
        CallbackButton(text="Португалия", payload="item:drinks:coffee:portugal"),
    )
    b.row(CallbackButton(text="Назад", payload="section:drinks"))
    return b


def travel_keyboard() -> InlineKeyboardBuilder:
    """Путешествия: Маршрут на 3 дня, Как выбрать район, Где гулять без толпы, Что попробовать, Назад."""
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="Маршрут на 3 дня", payload="item:travel:route_3d"))
    b.row(CallbackButton(text="Как выбрать район", payload="item:travel:district"))
    b.row(CallbackButton(text="Где гулять без толпы", payload="item:travel:no_crowd"))
    b.row(CallbackButton(text="Что попробовать в стране", payload="item:travel:try_country"))
    b.row(CallbackButton(text="Назад", payload="main"))
    return b


def lifehack_keyboard() -> InlineKeyboardBuilder:
    """Лайфхаки: Документы, Интернет и связь, Аптечка, Транспорт, Что скачать, Назад."""
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="Документы", payload="item:lifehack:docs"))
    b.row(CallbackButton(text="Интернет и связь", payload="item:lifehack:internet"))
    b.row(CallbackButton(text="Аптечка", payload="item:lifehack:pharmacy"))
    b.row(CallbackButton(text="Транспорт", payload="item:lifehack:transport"))
    b.row(CallbackButton(text="Что скачать перед вылетом", payload="item:lifehack:download"))
    b.row(CallbackButton(text="Назад", payload="main"))
    return b


def remote_keyboard() -> InlineKeyboardBuilder:
    """Для удалёнки: Где жить, Где работать, Как не сливать бюджет, Что купить, Как выбрать страну, Назад."""
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="Где жить", payload="item:remote:live"))
    b.row(CallbackButton(text="Где работать", payload="item:remote:work"))
    b.row(CallbackButton(text="Как не сливать бюджет", payload="item:remote:budget"))
    b.row(CallbackButton(text="Что купить сразу после приезда", payload="item:remote:buy_after"))
    b.row(CallbackButton(text="Как выбрать страну", payload="item:remote:choose_country"))
    b.row(CallbackButton(text="Назад", payload="main"))
    return b


def item_reply_keyboard(channel_url: str, same_payload: str | None = None) -> InlineKeyboardBuilder:
    """Под ответом по теме: Открыть канал, Ещё (если same_payload), В меню."""
    b = InlineKeyboardBuilder()
    b.row(LinkButton(text="Открыть канал", url=channel_url))
    if same_payload:
        b.row(CallbackButton(text="Ещё одну страну", payload=same_payload))
    b.row(CallbackButton(text="В меню", payload="main"))
    return b
