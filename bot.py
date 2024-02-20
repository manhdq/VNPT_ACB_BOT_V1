# -*- coding: utf-8 -*-
import telebot
import config
import pytz

from helper import check_organ, initialize_knowledges, \
                telebot_send_message


P_TIMEZONE = pytz.timezone(config.TIMEZONE)
TIMEZONE_COMMON_NAME = config.TIMEZONE_COMMON_NAME

# Create a bot given token
bot = telebot.TeleBot(config.TOKEN)
# bot.polling(none_stop=True)

recommend_tickers = [
    "FRT - Bán lẻ FPT",
    "PNJ - Vàng Phú Nhuận",
    "VRE - Vincom Retail",
]

# message_ids = []  # contain history chatlog
current_ticker = ""
current_organ_name = ""
def reset_chatlog():  # Reset chatlog and initialize new chatbot
    global current_ticker, current_organ_name
    current_ticker = ""
    current_organ_name = ""


# /start command handler
@bot.message_handler(commands=["start"])
def start_command(message):
    reset_chatlog()
    chat_id = message.chat.id
    telebot_send_message(bot, chat_id,
                         "Xin chào! Tôi là chatbot tư vấn được phát triển bởi ACB để hỗ trợ bạn trong việc tìm hiểu về các doanh nghiệp và thông tin liên quan.")
    telebot_send_message(bot, chat_id,
                         "Tôi có thể cung cấp tư vấn và đánh giá liệu rằng một doanh nghiệp có đáp ứng đủ các tiêu chí để sử dụng các dịch vụ từ ACB hay không, như vay tín dụng, tài chính, và các dịch vụ khác.")
    telebot_send_message(bot, chat_id,
                         "Bằng việc sử dụng trí thông minh nhân tạo và cơ sở dữ liệu rộng lớn, tôi sẽ cố gắng cung cấp cho bạn những thông tin chính xác và hữu ích nhất có thể để giúp bạn đưa ra quyết định thông minh về việc hợp tác kinh doanh với các doanh nghiệp.")
    # Recommend some tickers for user
    keyboard = telebot.types.InlineKeyboardMarkup()
    for ticker in recommend_tickers:
        keyboard.row(telebot.types.InlineKeyboardButton(ticker, callback_data=f"get-{ticker.split('-')[0].strip()}"))
    
    telebot_send_message(bot, chat_id,
                         "Xin vui lòng cho tôi mã hoặc tên doanh nghiệp, tổ chức để tôi có thể hỗ trợ tư vấn cho bạn",
                         reply_markup=keyboard)

# Click handler
@bot.callback_query_handler(func=lambda call: True)
def iq_callback(query):
    global current_ticker, current_organ_name
    data = query.data
    chat_id = query.message.chat.id
    if data.startswith("get-"):  # infos for specific ticker
        if current_ticker == "":
            ticker = data[4:]
            ticker, organ_name, organ_short_name = check_organ(ticker)
            current_ticker = ticker
            current_organ_name = organ_name

            bot.answer_callback_query(query.id)
            telebot_send_message(bot, chat_id,
                         f"Thông tin cần tư vấn: **{ticker} - {organ_name} - {organ_short_name}**")
            initialize_knowledges(bot, chat_id, ticker, organ_name)
        else:
            telebot_send_message(bot, chat_id,
                         f"Bạn đang hỏi tư vấn thông tin của **{current_ticker} - {current_organ_name}**. Nếu bạn muốn hỏi thông tin về doanh nghiệp, tổ chức khác, xin vui lòng nhập lệnh /start để làm mới quá trình tư vấn ạ!")

# Handles all messages for which the lambda returns True
@bot.message_handler(content_types=['text'])
def handle_text_input(message):
    global current_ticker, current_organ_name
    text = message.text
    chat_id = message.chat.id
    if current_ticker == "":
        result = check_organ(text.strip())
        if result is None:
            telebot_send_message(bot, chat_id,
                         f"Xin lỗi bạn nhưng có vẻ thông tin về doanh nghiệp **{text.strip()}** không có trong cơ sở dữ liệu của tôi, bạn có thể kiểm tra lại thông tin mã doanh nghiệp, tổ chức hoặc tôi có thể giúp bạn tư vấn thông tin doanh nghiệp, tổ chức khác không?")
            telebot_send_message(bot, chat_id,
                         "Bạn có thể xem thêm thông tin mã doanh nghiệp, tổ chức tại [link](https://eodhd.com/exchange/VN)")
            return
        else:
            ticker, organ_name, organ_short_name = result
            current_ticker = ticker
            current_organ_name = organ_name

            telebot_send_message(bot, chat_id,
                         f"Thông tin cần tư vấn: **{ticker} - {organ_name} - {organ_short_name}**")
            initialize_knowledges(bot, ticker)


bot.infinity_polling()