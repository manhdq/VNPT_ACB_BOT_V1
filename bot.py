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
    "CTCP Bán lẻ Kỹ thuật số FPT (FRT)",
    "CTCP Vàng bạc Đá quý Phú Nhuận (PNJ)",
    "CTCP Đầu tư Thế giới Di động (MWG)",
    "CTCP G-Automobile (GMA)",
    "CTCP City Auto (CAV)",
    "CTCP Cảng Sài Gòn (SGC)",
    "CTCP Cảng Đồng Nai (PDN)",
    "CTCP Gemadept (GMD)",
    "CTCP Cảng Cát Lái (CLL)",
    "CTCP Vận tải và Xếp dỡ Hải An (HAH)",
]

recommend_tickers_short = \
    [ticker.split()[-1].strip()[1:-1] for ticker in recommend_tickers]

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
    # Recommend some tickers for user
    keyboard = telebot.types.InlineKeyboardMarkup()
    for ticker in recommend_tickers:
        keyboard.row(telebot.types.InlineKeyboardButton(ticker, callback_data=f"get-{ticker.split()[-1].strip()[1:-1]}"))
    
    telebot_send_message(bot, chat_id,
                         """Xin chào! Tôi là VNPT FinAssist, trợ lý ảo chuyên cung cấp giải pháp toàn diện cho việc đánh giá và cấp tín dụng doanh nghiệp. Hiện tại, VNPT FinAssist đang hỗ trợ phân tích các doanh nghiệp sau:
1. CTCP Bán lẻ Kỹ thuật số FPT (FRT)
2. CTCP Vàng bạc Đá quý Phú Nhuận (PNJ)
3. CTCP Đầu tư Thế giới Di động (MWG)
4. CTCP G-Automobile (GMA)
5. CTCP City Auto (CAV)
6. CTCP Cảng Sài Gòn (SGC)
7. CTCP Cảng Đồng Nai (PDN)
8. CTCP Gemadept (GMD)
9. CTCP Cảng Cát Lái (CLL)
10. CTCP Vận tải và Xếp dỡ Hải An (HAH)
Hãy nhập mã ticker doanh nghiệp bạn muốn tìm hiểu để tôi có thể hỗ trợ bạn ngay nhé!""",
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
            ticker, organ_name, organ_short_name = check_organ(ticker, recommend_tickers_short)
            current_ticker = ticker
            current_organ_name = organ_name

            bot.answer_callback_query(query.id)
            telebot_send_message(bot, chat_id,
                         f"Thông tin cần tư vấn: **{ticker} - {organ_name} - {organ_short_name}**")
            initialize_knowledges(bot, chat_id, ticker, organ_name)
            # Finish with the recommend helpful assistance option for user
            telebot_send_message(bot, chat_id,
                                "Hy vọng các thông tin và phân tích VNPT FinAssist vừa cung cấp có hữu ích với bạn. Nếu bạn còn thắc mắc hoặc muốn tôi phân tích một doanh nghiệp khác, đừng ngần ngại đặt câu hỏi cho VNPT FinAssist nhé!")
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
        result = check_organ(text.strip(), recommend_tickers_short)
        if result is None:
            keyboard = telebot.types.InlineKeyboardMarkup()
            for ticker in recommend_tickers:
                keyboard.row(telebot.types.InlineKeyboardButton(ticker, callback_data=f"get-{ticker.split()[-1].strip()[1:-1]}"))
            telebot_send_message(bot, chat_id,
                         f"""Xin lỗi, tôi chưa có thông tin về doanh nghiệp **{text.strip()}** trong cơ sở dữ liệu của mình. Bạn có muốn tìm hiểu về doanh nghiệp nào khác không?""",
                         reply_markup=keyboard)
            return
        else:
            ticker, organ_name, organ_short_name = result
            current_ticker = ticker
            current_organ_name = organ_name

            telebot_send_message(bot, chat_id,
                         f"Thông tin cần tư vấn: **{ticker} - {organ_name} - {organ_short_name}**")
            initialize_knowledges(bot, ticker)
            # Finish with the recommend helpful assistance option for user
            telebot_send_message(bot, chat_id,
                                "Hy vọng các thông tin và phân tích VNPT FinAssist vừa cung cấp có hữu ích với bạn. Nếu bạn còn thắc mắc hoặc muốn tôi phân tích một doanh nghiệp khác, đừng ngần ngại đặt câu hỏi cho VNPT FinAssist nhé!")


bot.infinity_polling()