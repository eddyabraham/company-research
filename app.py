import os
import re
import time

from flask import Flask, flash, make_response, redirect, render_template, request, send_from_directory, url_for

from company_research import (
    ddg_search,
    fetch_yahoo_data,
    find_ticker,
    fmt_market_cap,
    process_news_items,
)
from db import get_history, get_search, init_db, save_search

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-prod")

init_db()


@app.template_filter("regex_replace")
def regex_replace(value, pattern, replacement):
    return re.sub(pattern, replacement, value or "")


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    resp = make_response(send_from_directory("static", "sw.js"))
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Content-Type"] = "application/javascript"
    return resp


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
    data = dict(
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
    search_id = save_search(data)
    return redirect(url_for("result", search_id=search_id))


@app.route("/result/<int:search_id>")
def result(search_id):
    data = get_search(search_id)
    if not data:
        flash("Search not found.")
        return redirect(url_for("index"))
    return render_template("results.html", **data)


@app.route("/history")
def history():
    return render_template("history.html", searches=get_history())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
