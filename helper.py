import markdown2
import re
import os
import pandas as pd
import warnings
from PIL import Image, ImageDraw, ImageFont
from functools import wraps

import google.generativeai as genai
from telegram import ChatAction
from vnstock import * #import all functions

from utils import to_lower, to_upper
from vnstock_helper import parse_ratios

GOOGLE_API_KEY=""
genai.configure(api_key=GOOGLE_API_KEY)

generation_config=genai.types.GenerationConfig(
        # Only one candidate for now.
#         candidate_count=1,
#         stop_sequences=['x'],
#         max_output_tokens=20,
        temperature=0.2)

model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)
passage_cache = ""  # Save time when generate answer 2 and 3


df_list = listing_companies()

ticker_list = df_list.ticker.tolist()
ticker_list = list(map(to_lower, ticker_list))

organ_name_list = df_list.organName.tolist()
organ_name_list = list(map(to_lower, organ_name_list))

organ_short_name_list = df_list.organShortName.tolist()
organ_short_name_list = list(map(to_lower, organ_short_name_list))


def check_organ(name):
    # If name is ticker and exist
    if name.lower() in ticker_list:
        id = ticker_list.index(name.lower())
    elif name.lower() in organ_name_list:
        id = organ_name_list.index(name.lower())
    elif name.lower() in organ_short_name_list:
        id = organ_short_name_list.index(name.lower())
    else:
        return None
    row = df_list.iloc[id]
    return row.ticker, row.organName, row.organShortName


##### Generate all pre-knowledges #####
def initialize_knowledges(bot, chat_id, ticker, organ_name):
    question_list = [
        f"Phân tích tổng quan về công ty {ticker} - {organ_name}",
        "Đánh giá tình hình kinh doanh của công ty trong 3 năm gần đây và so sánh với trung bình các công ty trong ngành.",
        "Đánh giá mức độ phù hợp của doanh nghiệp so với điều kiện cấp tín dụng của ACB",
    ]
    base_knowledges_dict = {

    }

    # QA 1
    telebot_send_message(bot, chat_id,
                         f"**Q1:** {question_list[0]}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_1(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict["Q1"] = question_list[0]
    base_knowledges_dict["A1"] = answer

    # QA 2
    telebot_send_message(bot, chat_id,
                         f"**Q2:** {question_list[1]}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_2(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict["Q2"] = question_list[1]
    base_knowledges_dict["A2"] = answer

    # QA 3
    telebot_send_message(bot, chat_id,
                         f"**Q3:** {question_list[2]}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_3(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict["Q3"] = question_list[2]
    base_knowledges_dict["A3"] = answer

    return base_knowledges_dict


##### Question 1: Phân tích tổng quan về công ty XYZ #####
def generate_answer_1(ticker):
    def parse_profile(ticker):
        df = company_profile(ticker)
        try:
            name = df["companyName"].values[0]
            passage = (
                f"Tên công ty: {df['companyName'].values[0]}\n"
                f"Lĩnh vực: {df['keyDevelopments'].values[0]}\n"
                f"Thông tin chung: {df['companyProfile'].values[0]}\n"
                f"Lịch sử phát triển: {df['historyDev'].values[0]}\n"
                f"Tiềm năng: {df['companyPromise'].values[0]}\n"
                f"Rủi ro: {df['businessRisk'].values[0]}\n"
                f"Chiến lược kinh doanh: {df['businessStrategies'].values[0]}"
            )
        except KeyError:
            name = ticker
            passage = "Không có thông tin về doanh nghiệp"
        return passage, name
    
    passage, _ = parse_profile(ticker)

    prompt = f"""Hãy tổng hợp các thông tin tổng quan về doanh nghiệp dựa vào thông tin dưới đây.
    Yêu cầu bản tổng hợp cần phải chuyên nghiệp, làm rõ được bức tranh chân dung của 1 doanh nghiệp.

    Thông tin doanh nghiệp:
    {passage}"""
    response = model.generate_content(prompt)

    return response.text


##### Question 2: Đánh giá tình hình kinh doanh của công ty trong 3 năm gần đây và so sánh với trung bình các công ty trong ngành. #####
def generate_answer_2(ticker):
    global passage_cache
    PROMPT_2 = f"""Dựa vào các thông tin dưới đây, hãy đưa ra 1 báo cáo thực hiện phân tích và đánh giá toàn diện về hiệu suất kinh doanh của công ty trong 3 năm gần đây.
Báo cáo nên bao gồm một số so sánh chi tiết với hiệu suất trung bình của các công ty cùng ngành,
như doanh thu, lợi nhuận, tăng trưởng và 1 số chỉ số tài chính quan trọng để hiểu rõ vị thế và khả năng cạnh tranh của công ty.
Yêu cầu báo cáo chuyên nghiệp và chi tiết, làm cơ sở để hỗ trợ nghiệp vụ cấp tín dụng trong ngân hàng.
Ở cuối báo cáo hãy liệt kê top 5 công ty có doanh thu lớn nhất trong ngành.
"""
    
    passage_cache = parse_ratios(ticker)

    prompt = f"""{PROMPT_2}

    Thông tin doanh nghiệp:
    {passage_cache}"""
    response = model.generate_content(prompt)

    return response.text


##### Question 3: Đánh giá mức độ phù hợp của doanh nghiệp so với điều kiện cấp tín dụng của ACB. #####
def generate_answer_3(ticker):
    global passage_cache
    ACB_CRITERIA = """Tiêu chí cấp tín dụng của ACB:
- Vốn chủ sở hữu: > 30 tỷ VND.
- Tỷ suất lợi nhuận trên vốn chủ sở hữu (Return on Equity - ROE): > 0.15
- Tỷ suất lợi nhuận trên tổng tài sản (Return on Assets - ROA): > 0.05
- Biên lợi nhuận ròng (Net Profit Margin): > 0.05
- Tỷ lệ nợ trên vốn chủ sở hữu (Debt-to-Equity Ratio): < 2
- Tỷ lệ nợ trên tổng tài sản (Debt-to-Asset Ratio): < 0.7
- Tỷ lệ lãi suất bao phủ (Interest Coverage Ratio): > 3
- Tỷ số thanh toán hiện hành (Current Ratio): > 1
- Vòng quay khoản phải thu (Accounts Receivable Turnover): > 6
- Doanh thu trên vốn lưu động (Revenue-to-Working Capital): > 2
"""

    PROMPT_3 = f"""Dựa vào các thông tin dưới đây, hãy đưa ra bảng biểu đánh giá mức độ phù hợp của doanh nghiệp so với điều kiện cấp tín dụng của ACB.
Sau khi so sánh, đưa ra kết luận về số lượng tiêu chí doanh nghiệp đáp ứng đồng thời nêu ra các tiêu chí doanh nghiệp chưa thỏa mãn.
Lưu ý cần đưa ra tên doanh nghiệp trong đánh giá.
"""

    prompt = f"""{PROMPT_3}

Thông tin doanh nghiệp:
{passage_cache}

{ACB_CRITERIA}
"""
    response = model.generate_content(prompt)

    passage_cache = ""  # Naive reset

    return response.text


def table_to_image(table_str, index=0):
    os.makedirs("cache", exist_ok=True)
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    font = ImageFont.truetype("courbd.ttf", 15)
    text_width, text_height = font.getsize_multiline(table_str)
    im = Image.new("RGB", (text_width + 15, text_height + 15), "white")
    draw = ImageDraw.Draw(im)
    draw.text((7, 7), table_str, font=font, fill="black")
    im.save(f"cache/table_{index}.jpg", 'JPEG')


def reformat_table(text):
    def find_tables_with_indices(text):
        # Define a regular expression pattern for identifying tables
        table_pattern = re.compile(r'\|.*\|')

        # Find all matches in the text along with their starting indices
        matches = [(match.group(), match.start()) for match in table_pattern.finditer(text)]

        return matches
    
    def beautify_table(table_string):
        lines = table_string.strip().split("\n")
        # Extract header and data rows
        header = [col.strip() for col in lines[0].split('|')[1:-1]]
        data = [row.strip() for row in lines[2:]]

        # Convert to list of dictionaries
        id2col = {i: col for i, col in enumerate(header)}
        table_dict = {col: [] for col in header}
        for row in data:
            values = [col.strip() for col in row.split('|')[1:-1]]
            for i, val in enumerate(values):
                table_dict[id2col[i]].append(val)

        df = pd.DataFrame(table_dict)

        # Convert DataFrame to Markdown table
        markdown_table = df.to_markdown(index=False)

        return markdown_table
    
    start_index_parts = []
    table_parts = []
    start_indices = []
    tables = []

    # Find tables in the example text along with their starting indices
    tables_found_with_indices = find_tables_with_indices(text)
    for i, (table, start_index) in enumerate(tables_found_with_indices, 1):
        start_index_parts.append(start_index)
        table_parts.append(table)
    
    # Check if any table
    if len(start_index_parts) == 0:
        return text, 0
    
    start_indices.append(start_index_parts[0])
    table = table_parts[0]
    for i in range(len(start_index_parts) - 1):
        cur_id = start_index_parts[i]
        cur_table_part = table_parts[i]
        next_id = start_index_parts[i + 1]
        next_table_part = table_parts[i + 1]

        if cur_id + len(cur_table_part) + 1 - next_id > 5:
            tables.append(table)
            start_indices.append(next_id)
            table = next_table_part
        else:
            table += "\n" + next_table_part
    tables.append(table)

    reformat_tables = [beautify_table(tab) for tab in tables]

    for i, re_tab in enumerate(reformat_tables):
        re_tab = re_tab.replace("&gt;", ">")
        re_tab = re_tab.replace("&lt;", "<")
        table_to_image(re_tab, i)
    return text, len(start_indices)


def convert_to_html(text):
    html_text = markdown2.markdown(text)
    html_text = html_text.replace('<p>', '').replace('</p>', '')
    html_text = html_text.replace('<ul>\n', '').replace('</ul>\n', '')
    html_text = html_text.replace('<li>', '• ').replace('</li>', '')
    html_text = html_text.replace('<ol>\n', '• ').replace('</ol>\n', '')
    # Convert all table for better visual
    html_text, num_table = reformat_table(html_text)
    return html_text, num_table


def telebot_send_message(bot, chat_id, message, reply_markup=None):
    # First convert to HTML format
    html_message, num_table = convert_to_html(message)

    if reply_markup is not None:
        bot.send_message(
            chat_id,
            html_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        bot.send_message(
            chat_id,
            html_message,
            parse_mode="HTML"
        )
    if num_table:
        for i in range(num_table):
            with open(f"cache/table_{i}.jpg", "rb") as photo:
                bot.send_photo(
                    chat_id,
                    photo
                )