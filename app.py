import os
import time

from flask import Flask, flash, redirect, render_template, request, url_for

from company_research import (
    ddg_search,
    fetch_yahoo_data,
    find_ticker,
    fmt_market_cap,
    process_news_items,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-prod")


@app.template_filter("regex_replace")
def regex_replace(value, pattern, replacement):
    import re
    return re.sub(pattern, replacement, value or "")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/research", methods=["POST"])
def research():
    query = request.form.get("company", "").strip()
    if not query:
        flash("Please enter a company name or ticker symbol.")
        return redirect(url_for("index"))

    try:
        ticker_symbol, display_name = find_ticker(query)
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("index"))

    yahoo = fetch_yahoo_data(ticker_symbol)
    revenue = ddg_search(f"{display_name} revenue model business model how does it make money")
    time.sleep(1)
    risks = ddg_search(f"{display_name} key risks investor concerns headwinds challenges 2025")

    info = yahoo["info"]
    return render_template(
        "results.html",
        ticker=ticker_symbol,
        name=info.get("longName") or info.get("shortName") or display_name,
        sector=info.get("sector", "N/A"),
        industry=info.get("industry", "N/A"),
        market_cap=fmt_market_cap(info.get("marketCap")),
        exchange=info.get("exchange", "N/A"),
        description=info.get("longBusinessSummary") or "No description available.",
        revenue_results=revenue,
        risk_results=risks,
        news=process_news_items(yahoo["news"]),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
