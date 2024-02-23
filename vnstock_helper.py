import time
import numpy as np
from datetime import datetime
from tenacity import retry, wait_random_exponential, stop_after_attempt

from vnstock import * #import all functions

# Industry
def extract_industry_figures(ticker, apply_cache=True, min_outdate=30):
    start = time.time()
    industry = company_overview(ticker)["industry"][0]

    # Check if exist
    if os.path.exists("cache/industry_states.json"):
        with open("cache/industry_states.json", "r") as f:
                industry_states_dict = json.load(f)

        if apply_cache:
            if industry in industry_states_dict:
                industry_states = industry_states_dict[industry]
                # Check if outdated
                last_dtime = industry_states["datetime"]
                if (datetime.now() - datetime.strptime(last_dtime, "%Y-%m-%d")).days < min_outdate:
                    ## Using cache
                    figures = industry_states["figures"]
                    top_5_tickers = industry_states["top_5_tickers"]
                    return figures, top_5_tickers
    else:
        industry_states_dict = {}

    df_listing = listing_companies()
    industry_tickers = df_listing[df_listing["industry"] == industry]["ticker"]
    # num_tickers = len(industry_tickers)
    num_tickers = 0
    avg_revenue_0 = 0
    avg_revenue_1 = 0
    avg_revenue_2 = 0
    avg_yearRevenueGrowth_0 = 0
    avg_yearRevenueGrowth_1 = 0
    avg_yearRevenueGrowth_2 = 0
    avg_postTaxProfit_0 = 0
    avg_postTaxProfit_1 = 0
    avg_postTaxProfit_2 = 0
    top_tickers = []

    def get_fig_element(df, report_part, year, total_value, count):
        # Get element value of incomestatement for brief
        # Some time value can be nan so return average value
        ele_val = float(df[report_part][year]) if not np.isnan(float(df[report_part][year])) else (total_value/count if count>0 else 0.0)
        return ele_val

    for ticker in industry_tickers:
        try:
            df = financial_flow(symbol=ticker, report_type='incomestatement', report_range='yearly', get_all=False)
            year_0 = '2023' # replace with lastest year function
            year_1 = '2022'
            year_2 = '2021'

            revenue_0 = float(df["revenue"][year_0]) if not np.isnan(float(df["revenue"][year_0])) else 0.0
            avg_revenue_0 += get_fig_element(df, "revenue", year_0, avg_revenue_0, num_tickers)
            avg_revenue_1 += get_fig_element(df, "revenue", year_1, avg_revenue_1, num_tickers)
            avg_revenue_2 += get_fig_element(df, "revenue", year_2, avg_revenue_2, num_tickers)

            avg_yearRevenueGrowth_0 += get_fig_element(df, "yearRevenueGrowth", year_0, avg_yearRevenueGrowth_0, num_tickers)
            avg_yearRevenueGrowth_1 += get_fig_element(df, "yearRevenueGrowth", year_1, avg_yearRevenueGrowth_1, num_tickers)
            avg_yearRevenueGrowth_2 += get_fig_element(df, "yearRevenueGrowth", year_2, avg_yearRevenueGrowth_2, num_tickers)

            avg_postTaxProfit_0 += get_fig_element(df, "postTaxProfit", year_0, avg_postTaxProfit_0, num_tickers)
            avg_postTaxProfit_1 += get_fig_element(df, "postTaxProfit", year_1, avg_postTaxProfit_1, num_tickers)
            avg_postTaxProfit_2 += get_fig_element(df, "postTaxProfit", year_2, avg_postTaxProfit_2, num_tickers)

            # Filter top 5 in revenue
            top_tickers.append({"ticker": ticker, "revenue": float(revenue_0)})

            num_tickers += 1
        except Exception:
            print(f"There are not enough info for Company <{ticker}>")
            continue

    avg_revenue_0 /= num_tickers
    avg_revenue_0 = float(avg_revenue_0)
    avg_revenue_1 /= num_tickers
    avg_revenue_1 = float(avg_revenue_1)
    avg_revenue_2 /= num_tickers
    avg_revenue_2 = float(avg_revenue_2)
    avg_yearRevenueGrowth_0 /= num_tickers
    avg_yearRevenueGrowth_0 = float(avg_yearRevenueGrowth_0)
    avg_yearRevenueGrowth_1 /= num_tickers
    avg_yearRevenueGrowth_1 = float(avg_yearRevenueGrowth_1)
    avg_yearRevenueGrowth_2 /= num_tickers
    avg_yearRevenueGrowth_2 = float(avg_yearRevenueGrowth_2)
    avg_postTaxProfit_0 /= num_tickers
    avg_postTaxProfit_0 = float(avg_postTaxProfit_0)
    avg_postTaxProfit_1 /= num_tickers
    avg_postTaxProfit_1 = float(avg_postTaxProfit_1)
    avg_postTaxProfit_2 /= num_tickers
    avg_postTaxProfit_2 = float(avg_postTaxProfit_2)

  # Top 5 in the same industry
    top_5_tickers = sorted(top_tickers, key=lambda x: x["revenue"], reverse=True)[:5]
    for item in top_5_tickers:
        organName = df_listing[df_listing["ticker"]==item["ticker"]]["organName"].values[0]
        organShortName = df_listing[df_listing["ticker"]==item["ticker"]]["organShortName"].values[0]
        item["organName"] = organName
        item["organShortName"] = organShortName

    figures = {
              str(year_0): {"revenue":avg_revenue_0, "yearRevenueGrowth": avg_yearRevenueGrowth_0, "postTaxProfit": avg_postTaxProfit_0},
              str(year_1): {"revenue":avg_revenue_1, "yearRevenueGrowth": avg_yearRevenueGrowth_1, "postTaxProfit": avg_postTaxProfit_1},
              str(year_2): {"revenue":avg_revenue_2, "yearRevenueGrowth": avg_yearRevenueGrowth_2, "postTaxProfit": avg_postTaxProfit_2}
            }

    print(f"Taking {time.time()-start}s to calculate industry average for {num_tickers} company")

    # Save to cache
    industry_states = {
        "figures": figures,
        "top_5_tickers": top_5_tickers,
        "datetime": datetime.now().strftime("%Y-%m-%d")
    }
    industry_states_dict[industry] = industry_states

    with open("cache/industry_states.json", "w") as f:
        json.dump(industry_states_dict, f, indent=4)

    return figures, top_5_tickers


def extract_industry_ratios(ticker):
    def safe_get(df, key):
        try:
            return df[key][0]
        except KeyError:
            return None
    
    df = company_fundamental_ratio(symbol=ticker, mode='simplify', missing_pct=0.8)
    try:
        receivableTurnover = 365/float(df["daysReceivable.industryAvgValue"][0])
    except:
        receivableTurnover = None
    ratios = {
        "roe": safe_get(df, "roe.industryAvgValue"),
        "roa": safe_get(df, "roa.industryAvgValue"),
        "postTaxMargin": safe_get(df, "postTaxMargin.industryAvgValue"),
        "debtOnEquity": safe_get(df, "debtOnEquity.industryAvgValue"),
        "debtOnAsset": safe_get(df, "debtOnAsset.industryAvgValue"),
        "currentPayment": safe_get(df, "currentPayment.industryAvgValue"),
        "ebitOnInterest": safe_get(df, "ebitOnInterest.industryAvgValue"),
        "receivableTurnover": receivableTurnover, 
        "revenueOnWorkCapital": safe_get(df, "revenueOnWorkCapital.industryAvgValue")
    }

    return ratios

# Ticker specific
def extract_ticker_figures(ticker):
    df = financial_flow(symbol=ticker, report_type='incomestatement', report_range='yearly', get_all=False)
    figures = {}
    for year in df.index:
        item = {
            "revenue": df["revenue"][year],
            "yearRevenueGrowth": df["yearRevenueGrowth"][year],
            "postTaxProfit": df["postTaxProfit"][year]
            }

        figures[str(year)] = item
    return figures

def extract_ticker_ratios(ticker):
    def safe_get(df, column, index, default=None):
        try:
            return df.loc[index, column]
        except KeyError:
            return None
    
    df = financial_ratio(symbol=ticker, report_range='yearly', is_all=False).T
    ratios = {}
    for year in df.index:
        try:
            receivableTurnover = 365 / float(df.loc[year, "daysReceivable"])
        except:
            receivableTurnover = None
        item = {
            "roe": safe_get(df, "roe", year),
            "roa": safe_get(df, "roa", year),
            "postTaxMargin": safe_get(df, "postTaxMargin", year),
            "debtOnEquity": safe_get(df, "debtOnEquity", year),
            "debtOnAsset": safe_get(df, "debtOnAsset", year),
            "currentPayment": safe_get(df, "currentPayment", year),
            "ebitOnInterest": safe_get(df, "ebitOnInterest", year),
            "receivableTurnover": receivableTurnover,
            "revenueOnWorkCapital": safe_get(df, "revenueOnWorkCapital", year)
        }
        ratios[str(year)] = item
    return ratios


def parse_ticker_ratios(ticker):
    ticker_ratios = extract_ticker_ratios(ticker)
    name = company_profile(ticker)["companyName"].values[0]
    year = list(ticker_ratios.keys())[0]  # 1 năm gần nhất
    equity = financial_flow(symbol=ticker, report_type='balancesheet', report_range='yearly', get_all=False)["equity"].values[0]
    passage = (
        f"Các chỉ số tài chính của {name} năm {year}.\n"
        f"Vốn chủ sở hữu (Equity): {equity} tỷ VND\n"
        f"Tỷ suất sinh lời trên vốn chủ sở hữu (ROE): {ticker_ratios[year]['roe']}\n"
        f"Tỷ suất sinh lời trên tổng tài sản (ROA): {ticker_ratios[year]['roa']}\n"
        f"Biên lợi nhuận sau thuế (Post-Tax Margin): {ticker_ratios[year]['postTaxMargin']}\n"
        f"Tỷ lệ nợ trên vốn chủ sở hữu (Debt on Equity): {ticker_ratios[year]['debtOnEquity']}\n"
        f"Tỷ lệ nợ trên tổng tài sản (Debt on Asset): {ticker_ratios[year]['debtOnAsset']}\n"
        f"Tỷ lệ lãi suất bao phủ (EBIT on Interest): {ticker_ratios[year]['ebitOnInterest']}\n"
        f"Tỷ số thanh toán hiện hành (Current Payment): {ticker_ratios[year]['currentPayment']}\n"
        f"Vòng quay khoản phải thu (Receivable Turnover): {round(ticker_ratios[year]['receivableTurnover'], 2)}\n"
        f"Tỷ lệ doanh thu trên vốn lưu động (Revenue on Work Capital): {ticker_ratios[year]['revenueOnWorkCapital']}\n"
    )
    return passage

@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def parse_industry_ratios(ticker):
    industry_ratios = extract_industry_ratios(ticker)
    # print(ticker)
    industry = company_overview(ticker)["industry"][0]
    passage = (
        f"Các chỉ số tài chính của trung bình ngành {industry}.\n"
        f"Tỷ suất sinh lời trên vốn chủ sở hữu (ROE): {industry_ratios['roe']}\n"
        f"Tỷ suất sinh lời trên tổng tài sản (ROA): {industry_ratios['roa']}\n"
        f"Biên lợi nhuận sau thuế (Post-Tax Margin): {industry_ratios['postTaxMargin']}\n"
        f"Tỷ lệ nợ trên vốn chủ sở hữu (Debt on Equity): {industry_ratios['debtOnEquity']}\n"
        f"Tỷ lệ nợ trên tổng tài sản (Debt on Asset): {industry_ratios['debtOnAsset']}\n"
        f"Tỷ lệ lãi suất bao phủ (EBIT on Interest): {industry_ratios['ebitOnInterest']}\n"
        f"Tỷ số thanh toán hiện hành (Current Payment): {industry_ratios['currentPayment']}\n"
        f"Vòng quay khoản phải thu: {round(industry_ratios['receivableTurnover'], 2)}\n"
        f"Tỷ lệ doanh thu trên vốn lưu động (Revenue on Work Capital): {industry_ratios['revenueOnWorkCapital']}\n"
    )
    return passage

def parse_ratios(ticker):
    # Profile
    df = company_profile(ticker)
    name = df["companyName"].values[0]
    industry = company_overview(ticker)["industry"][0]
    passage_0 = f"Tên công ty: {name}\nLĩnh vực: {industry}\n"

    # Ticker
    ticker_figures = extract_ticker_figures(ticker)
    years = list(ticker_figures.keys())[:3]  # 3 năm gần nhất
    passage_1 = f"Doanh thu, lợi nhuận của {name}.\n"
    for year in years:
        sub_passage = (
            f"Doanh thu {year}: {ticker_figures[year]['revenue']:.2f} tỉ VND. "
            f"Tăng trưởng doanh thu {int(year)-1}-{year}: {ticker_figures[year]['yearRevenueGrowth']*100:.2f}%. "
            f"Lợi nhuận sau thuế {year}: {ticker_figures[year]['postTaxProfit']:.2f} tỉ VND\n"
        )
        passage_1 += sub_passage

    passage_2 = parse_ticker_ratios(ticker)

    # Industry
    industry_figures, top_5_tickers = extract_industry_figures(ticker)
    years = list(industry_figures.keys())[:3]  # 3 năm gần nhất
    passage_3 = "Doanh thu, lợi nhuận trung bình ngành.\n"
    for year in years:
        year_revenue = industry_figures[year]['revenue'] if industry_figures[year]['revenue'] is not None else np.nan
        year_revenue_growth = industry_figures[year]['yearRevenueGrowth'] if industry_figures[year]['yearRevenueGrowth'] is not None else np.nan
        year_post_tax_profit = industry_figures[year]['postTaxProfit'] if industry_figures[year]['postTaxProfit'] is not None else np.nan
        sub_passage = (
            f"Doanh thu {year}: {year_revenue:.2f} tỉ VND. "
            f"Tăng trưởng doanh thu {int(year)-1}-{year}: {year_revenue_growth*100:.2f}%. "
            f"Lợi nhuận sau thuế {year}: {year_post_tax_profit:.2f} tỉ VND\n"
        )
        passage_3 += sub_passage

    passage_4 = parse_industry_ratios(ticker)

    # Top 5 same industry
    passage_5 = f"Dưới đây là Top 5 công ty có doanh thu lớn nhất ngành theo số liệu báo cáo tài chính {year}.\n"
    for item in top_5_tickers:
        sub_passage = f"{item['organName']}. Doanh thu: {item['revenue']} tỉ VND\n"
        passage_5 += sub_passage

    final_passage = f"{passage_0}{passage_1}{passage_2}{passage_3}{passage_4}{passage_5}"

    return final_passage


def get_industry_of_ticker(ticker):
    industry = company_overview(ticker)["industry"][0]
    return industry