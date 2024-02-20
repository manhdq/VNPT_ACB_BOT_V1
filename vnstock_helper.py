import time

from vnstock import * #import all functions

# Industry
def extract_industry_figures(ticker):
    start = time.time()

    industry = company_overview(ticker)["industry"][0]
    df_listing = listing_companies()
    industry_tickers = df_listing[df_listing["industry"] == industry]["ticker"]
    num_tickers = len(industry_tickers)
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

    for ticker in industry_tickers:
        df = financial_flow(symbol=ticker, report_type='incomestatement', report_range='yearly', get_all=False)
        year_0 = '2023' # replace with lastest year function
        year_1 = '2022'
        year_2 = '2021'

        try:
            revenue_0 = df["revenue"][year_0]
            avg_revenue_0 += revenue_0
            avg_revenue_1 += df["revenue"][year_1]
            avg_revenue_2 += df["revenue"][year_2]

            avg_yearRevenueGrowth_0 += df["yearRevenueGrowth"][year_0]
            avg_yearRevenueGrowth_1 += df["yearRevenueGrowth"][year_1]
            avg_yearRevenueGrowth_2 += df["yearRevenueGrowth"][year_2]

            avg_postTaxProfit_0 += df["postTaxProfit"][year_0]
            avg_postTaxProfit_1 += df["postTaxProfit"][year_1]
            avg_postTaxProfit_2 += df["postTaxProfit"][year_2]

            # Filter top 5 in revenue
            top_tickers.append({"ticker": ticker, "revenue": revenue_0})
        except Exception:
            print(f"There are not enough info for Company <{ticker}>")
            num_tickers -= 1
            continue

    avg_revenue_0 /= num_tickers
    avg_revenue_1 /= num_tickers
    avg_revenue_2 /= num_tickers
    avg_yearRevenueGrowth_0 /= num_tickers
    avg_yearRevenueGrowth_1 /= num_tickers
    avg_yearRevenueGrowth_2 /= num_tickers
    avg_postTaxProfit_0 /= num_tickers
    avg_postTaxProfit_1 /= num_tickers
    avg_postTaxProfit_2 /= num_tickers

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

    return figures, top_5_tickers

def extract_industry_ratios(ticker):
    df = company_fundamental_ratio(symbol=ticker, mode='simplify', missing_pct=0.8)
    try:
        receivableTurnover = 365/float(df["daysReceivable.industryAvgValue"][0])
    except:
        receivableTurnover = None
    ratios = {
      "roe": df["roe.industryAvgValue"][0],
      "roa": df["roa.industryAvgValue"][0],
      "postTaxMargin": df["postTaxMargin.industryAvgValue"][0],
      "debtOnEquity": df["debtOnEquity.industryAvgValue"][0],
      "debtOnAsset": df["debtOnAsset.industryAvgValue"][0],
      "currentPayment": df["currentPayment.industryAvgValue"][0],
      "ebitOnInterest": df["ebitOnInterest.industryAvgValue"][0],
      "receivableTurnover": receivableTurnover,
      "revenueOnWorkCapital": df["revenueOnWorkCapital.industryAvgValue"][0]
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
    df = financial_ratio(symbol=ticker, report_range="yearly", is_all=False).T
    ratios = {}
    for year in df.index:
        try:
            receivableTurnover=365/float(df["daysReceivable"][year])
        except:
            receivableTurnover = None
        item = {
          "roe": df["roe"][year],
          "roa": df["roa"][year],
          "postTaxMargin": df["postTaxMargin"][year],
          "debtOnEquity": df["debtOnEquity"][year],
          "debtOnAsset": df["debtOnAsset"][year],
          "currentPayment": df["currentPayment"][year],
          "ebitOnInterest": df["ebitOnInterest"][year],
          "receivableTurnover": receivableTurnover,
          "revenueOnWorkCapital": df["revenueOnWorkCapital"][year]
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

def parse_industry_ratios(ticker):
    industry_ratios = extract_industry_ratios(ticker)
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
    try:
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
            sub_passage = (
                f"Doanh thu {year}: {industry_figures[year]['revenue']:.2f} tỉ VND. "
                f"Tăng trưởng doanh thu {int(year)-1}-{year}: {industry_figures[year]['yearRevenueGrowth']*100:.2f}%. "
                f"Lợi nhuận sau thuế {year}: {industry_figures[year]['postTaxProfit']:.2f} tỉ VND\n"
            )
            passage_3 += sub_passage

        passage_4 = parse_industry_ratios(ticker)

        # Top 5 same industry
        passage_5 = f"Dưới đây là Top 5 công ty có doanh thu lớn nhất ngành theo số liệu báo cáo tài chính {year}.\n"
        for item in top_5_tickers:
            sub_passage = f"{item['organName']}. Doanh thu: {item['revenue']} tỉ VND\n"
            passage_5 += sub_passage

        final_passage = f"{passage_0}{passage_1}{passage_2}{passage_3}{passage_4}{passage_5}"

    except Exception as e:
        raise(e)
        name = ticker
        final_passage = "Không có thông tin về doanh nghiệp"

    return final_passage