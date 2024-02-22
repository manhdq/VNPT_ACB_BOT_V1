import markdown2
import re
import os
import numpy as np
import pandas as pd
import warnings
import dataframe_image as dfi
from PIL import Image, ImageDraw, ImageFont

import google.generativeai as genai
from telegram import ChatAction
from vnstock import * #import all functions

from utils import to_lower, to_upper
from vnstock_helper import parse_ratios, get_industry_of_ticker

GOOGLE_API_KEY=os.environ["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

generation_config=genai.types.GenerationConfig(
        # Only one candidate for now.
#         candidate_count=1,
#         stop_sequences=['x'],
#         max_output_tokens=20,
        temperature=0.2)

model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)
passage_cache = ""  # Save time when generate answer 2 and 3


# @retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def get_completion(prompt):
    return model.generate_content(prompt)


df_list = listing_companies()

ticker_list = df_list.ticker.tolist()
ticker_list = list(map(to_lower, ticker_list))

organ_name_list = df_list.organName.tolist()
organ_name_list = list(map(to_lower, organ_name_list))

organ_short_name_list = df_list.organShortName.tolist()
organ_short_name_list = list(map(to_lower, organ_short_name_list))


def check_organ(name, stricted_tickers=[]):
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
    if len(stricted_tickers) > 0:
        if row.ticker not in stricted_tickers:
            return None
    return row.ticker, row.organName, row.organShortName


##### Generate all pre-knowledges #####
def initialize_knowledges(bot, chat_id, ticker, organ_name):
    question_list = [
        "Phân tích tổng quan về công ty **{0} - {1}**",  # ticker, organ_name
        "Đánh giá tình hình kinh doanh của công ty **{0} - {1}** trong 3 năm gần đây và so sánh với trung bình các công ty trong ngành **{2}**.",  # ticker, organ_name, industry
        "Đánh giá mức độ phù hợp của doanh nghiệp **{0} - {1}** so với điều kiện cấp tín dụng của ACB",  # ticker, organ_name
    ]
    base_knowledges_dict = {

    }
    industry = get_industry_of_ticker(ticker)

    # QA 1
    telebot_send_message(bot, chat_id,
                         f"**Q1:** {question_list[0].format(ticker, organ_name)}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_1(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict[question_list[0].format(ticker, organ_name)] = answer

    # QA 2
    telebot_send_message(bot, chat_id,
                         f"**Q2:** {question_list[1].format(ticker, organ_name, industry)}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_2(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict[question_list[1].format(ticker, organ_name, industry)] = answer

    # QA 3
    telebot_send_message(bot, chat_id,
                         f"**Q3:** {question_list[2].format(ticker, organ_name)}")
    bot.send_chat_action(chat_id, action=ChatAction.TYPING)
    answer = generate_answer_3(ticker)
    telebot_send_message(bot, chat_id,
                         answer)
    base_knowledges_dict[question_list[2].format(ticker, organ_name)] = answer

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
    response = get_completion(prompt)

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
    response = get_completion(prompt)

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
    response = get_completion(prompt)

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
    os.makedirs("cache", exist_ok=True)
    def find_tables_with_indices(text):
        # Define a regular expression pattern for identifying tables
        table_pattern = re.compile(r'\|.*\|')

        # Find all matches in the text along with their starting indices
        matches = [(match.group(), match.start()) for match in table_pattern.finditer(text)]

        return matches
    
    def beautify_table_saving(table_string, index):
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
                val = val.replace("&gt;", ">")
                val = val.replace("&lt;", "<")
                table_dict[id2col[i]].append(val)
        
        df = pd.DataFrame(table_dict)
        dfi.export(df, f'cache/table_{index}.jpg')
    
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

    for i, tab in enumerate(tables):
        beautify_table_saving(tab, i)
        
    return text, len(start_indices)


def convert_to_html(text):
    html_text = markdown2.markdown(text)
    html_text = html_text.replace('<p>', '').replace('</p>', '')
    html_text = html_text.replace('<ul>\n', '').replace('</ul>\n', '').replace('</ul>', '')
    html_text = html_text.replace('<li>', '• ').replace('</li>', '')
    html_text = html_text.replace('<ol>\n', '• ').replace('</ol>\n', '').replace('</ol>', '')
    # Convert all table for better visual
    html_text, num_table = reformat_table(html_text)
    return html_text, num_table


def breakdown_message_by_endline(message, message_max_length):
    ##TODO: Not necessary for now
    return [message]


def breakdown_message_by_header(message, message_max_length):
    def find_header_with_indices(text):
        # Define a regular expression pattern for identifying tables
        table_pattern = re.compile(r'\*\*.*\*\*')

        # Find all matches in the text along with their starting indices
        matches = [(match.group(), match.start()) for match in table_pattern.finditer(text)]

        return matches
    
    len_msg = len(message)
    num_parts = np.ceil(len_msg / message_max_length)
    avg_words_per_part = len_msg // num_parts  # for scale all parts after splitation

    subparts = []; header_ids = []
    headers_found_with_indices = find_header_with_indices(message)
    for _, start_index in headers_found_with_indices:
        header_ids.append(start_index)

    # Get subparts, each subpart start with one header
    if len(header_ids) == 0 or len(header_ids) == 1:
        subparts = [message]
    else:
        if header_ids[0] > 1:
            # If start index of first header != 0, get first subpart
            subparts.append(message[:header_ids[0] - 1])
        for i in range(len(header_ids) - 1):
            subparts.append(message[header_ids[i]: header_ids[i+1]])

    parts_by_header = []
    part_by_header = ""
    for subpart in subparts:
        if len(part_by_header + subpart) > avg_words_per_part:
            parts_by_header.append(part_by_header)
            part_by_header = subpart
        else:
            part_by_header += subpart
    parts_by_header.append(part_by_header)  # append the last one

    results = []
    for part_by_header in parts_by_header:
        parts = breakdown_message_by_endline(part_by_header, message_max_length)
        results.extend(parts)

    return results


def telebot_send_message(bot, chat_id, message, reply_markup=None, message_max_length = 4096):
    message_list = breakdown_message_by_header(message, message_max_length)
    num_messages = len(message_list)
    for i, message in enumerate(message_list):
        # print(len(message))
        # First convert to HTML format
        html_message, num_table = convert_to_html(message)

        if reply_markup is not None and i==num_messages-1:
            try:
                bot.send_message(
                    chat_id,
                    html_message,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except:
                bot.send_message(
                    chat_id,
                    message,
                    reply_markup=reply_markup
                )
        else:
            try:
                bot.send_message(
                    chat_id,
                    html_message,
                    parse_mode="HTML"
                )
            except:
                # print(html_message)
                bot.send_message(
                    chat_id,
                    message
                )
        if num_table:
            for i in range(num_table):
                with open(f"cache/table_{i}.jpg", "rb") as photo:
                    bot.send_photo(
                        chat_id,
                        photo
                    )


class ACBAssistant:
    def __init__(self, base_knowledges=dict()):
        # TODO: Dynamic the prompt by config file
        self.system_guide = """Bạn là VNPT FinAssist, trợ lý ảo chuyên cung cấp giải pháp toàn diện cho việc phân tích và đánh giá doanh nghiệp.
Hãy dựa vào các thông tin dưới đây để đưa ra những phân tích chi tiết, hỗ trợ giải đáp câu hỏi của khách hàng. 

Lưu ý:
    - Không được sử dụng những cụm từ như ""theo đoạn văn"", ""trong đoạn văn"",... trong câu trả lời cuối cùng
    - Nếu không có thông tin trong các đoạn văn để trả lời câu hỏi, hãy viết 1 câu xin lỗi khách hàng do chưa đủ thông tin để trả lời

Đoạn văn: {}
Câu hỏi: {}"""
        self.base_knowledges = base_knowledges
        self.num_answer_retry = 10  # if answer process error 10 times, return exception

    def setup_system_guide(self, system_guide):
        self.system_guide = system_guide

    def setup_base_knowledges(self, base_knowledges):
        if isinstance(base_knowledges, str):  # if is path
            assert base_knowledges[:-5] == ".json"
            with open(base_knowledges, "r") as f:
                base_knowledges = json.load(f)
        
        self.base_knowledges = base_knowledges

    def get_answer(self, question, passages, retry_count=0):
        if retry_count >= self.num_answer_retry:
            return "xin lỗi, Hiện tại tôi không có đủ thông tin để trả lời câu hỏi này."

        text = self.system_guide.format(passages, question)
        try:
            response = model.generate_content(text,
                                            generation_config=genai.types.GenerationConfig(
                                                temperature=0.1
                                            ))
            text = response.text
            return text
        except:
            return self.get_answer(question, passages, retry_count+1)

    def request_answer(self, question, knowledges, passage_thres=0.5, use_base_knowledges=True):
        passages = self.process_passages(knowledges, use_base_knowledges, passage_thres)
        answer = self.get_answer(question, passages)
        return answer

    def process_passages(self, knowledges, use_base_knowledges=True, passage_thres=0.5):
        # Filter passages with low score
        passages = []
        index = 1
        for kl in knowledges:
            # Filter passages with low score
            if float(kl["score_ranking"]) < passage_thres:
                continue
            title = kl["passage_title"]
            content = kl["passage_content"]
            passages.append(f"[{index}] Tiêu đề: {title}\nNội dung: {content}")
            index += 1
        # Use base_knowledges if activate
        if use_base_knowledges:
            for title, content in self.base_knowledges.items():
                passages.append(f"[{index}] Tiêu đề: {title}\nNội dung: {content}")
        return "\n\n".join(passages)
