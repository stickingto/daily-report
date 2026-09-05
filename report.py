#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日日报生成脚本
- 成都天气
- 黄金行情（伦敦金现 + 人民币换算金价）
- 通过 QQ 邮箱 SMTP 发送
"""

import os
import sys
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# ============== 配置 ==============
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = "2205924499@qq.com"
SMTP_PASSWORD = os.environ.get("QQ_MAIL_AUTH_CODE", "")

# 收件人列表：从环境变量读取，多个邮箱用逗号分隔
# 例如：RECEIVER_EMAILS="a@qq.com,b@qq.com,c@163.com"
RECEIVER_EMAILS_RAW = os.environ.get("RECEIVER_EMAILS", "2205924499@qq.com")
RECEIVER_EMAILS = [email.strip() for email in RECEIVER_EMAILS_RAW.split(",") if email.strip()]

CITY = "Chengdu"
OZ_TO_GRAM = 31.1035  # 1盎司 = 31.1035克

# 英文天气描述 → 中文映射
WEATHER_MAP = {
    "Sunny": "晴",
    "Clear": "晴",
    "Partly cloudy": "多云",
    "Partly Cloudy": "多云",
    "Cloudy": "阴",
    "Overcast": "阴天",
    "Mist": "薄雾",
    "Fog": "雾",
    "Freezing fog": "冻雾",
    "Patchy rain possible": "可能有零星小雨",
    "Patchy snow possible": "可能有零星小雪",
    "Patchy sleet possible": "可能有零星雨夹雪",
    "Patchy freezing drizzle possible": "可能有冻毛毛雨",
    "Thundery outbreaks possible": "可能有雷阵雨",
    "Blowing snow": "吹雪",
    "Blizzard": "暴风雪",
    "Light drizzle": "小毛毛雨",
    "Patchy light drizzle": "零星小毛毛雨",
    "Freezing drizzle": "冻毛毛雨",
    "Heavy freezing drizzle": "强冻毛毛雨",
    "Light rain": "小雨",
    "Light rain shower": "小阵雨",
    "Moderate rain at times": "间歇中雨",
    "Moderate rain": "中雨",
    "Heavy rain at times": "间歇大雨",
    "Heavy rain": "大雨",
    "Light freezing rain": "小冻雨",
    "Moderate or heavy freezing rain": "中到大冻雨",
    "Light sleet": "小雨夹雪",
    "Moderate or heavy sleet": "中到大雨夹雪",
    "Light snow": "小雪",
    "Patchy light snow": "零星小雪",
    "Moderate snow": "中雪",
    "Patchy moderate snow": "零星中雪",
    "Heavy snow": "大雪",
    "Patchy heavy snow": "零星大雪",
    "Ice pellets": "冰粒",
    "Light rain shower": "小阵雨",
    "Moderate or heavy rain shower": "中到大阵雨",
    "Torrential rain shower": "暴雨",
    "Light sleet showers": "小阵雨夹雪",
    "Moderate or heavy sleet showers": "中到大阵雨夹雪",
    "Light snow showers": "小阵雪",
    "Moderate or heavy snow showers": "中到大阵雪",
    "Light showers of ice pellets": "小阵冰粒",
    "Moderate or heavy showers of ice pellets": "中到大阵冰粒",
    "Patchy light rain with thunder": "零星小雨伴雷",
    "Moderate or heavy rain with thunder": "中到大雨伴雷",
    "Patchy light snow with thunder": "零星小雪伴雷",
    "Moderate or heavy snow with thunder": "中到大雪伴雷",
}


def translate_weather(desc):
    """天气描述翻译"""
    return WEATHER_MAP.get(desc, desc)


# ============== 天气模块 ==============
def get_weather():
    """获取成都天气"""
    try:
        url = f"https://wttr.in/{CITY}?format=j1"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()

        current = data["current_condition"][0]
        today = data["weather"][0]

        weather_desc_en = current["weatherDesc"][0]["value"]
        weather_desc = translate_weather(weather_desc_en)

        weather = {
            "desc": weather_desc,
            "temp_c": current["temp_C"],
            "feels_like": current["FeelsLikeC"],
            "humidity": current["humidity"],
            "wind_speed": current["windspeedKmph"],
            "wind_dir": current["winddir16Point"],
            "uv_index": current["uvIndex"],
            "visibility": current["visibility"],
            "pressure": current["pressure"],
            "max_temp": today["maxtempC"],
            "min_temp": today["mintempC"],
            "sunrise": today["astronomy"][0]["sunrise"],
            "sunset": today["astronomy"][0]["sunset"],
            "rain_chance": _calc_rain_chance(today),
        }
        return weather
    except Exception as e:
        print(f"[WARN] 获取天气失败: {e}")
        return None


def _calc_rain_chance(today):
    """计算白天平均降水概率"""
    chances = []
    for hour in today.get("hourly", []):
        chance = int(hour.get("chanceofrain", 0))
        chances.append(chance)
    if chances:
        return sum(chances) // len(chances)
    return 0


def weather_advice(weather):
    """根据天气给出出行建议"""
    if not weather:
        return "⚠️ 天气数据获取失败，请自行查看天气预报。"

    lines = []
    rain = weather["rain_chance"]

    if rain >= 50:
        lines.append(f"☂️ **建议带伞** — 今日降水概率约 {rain}%")
    elif rain >= 30:
        lines.append(f"☂️ **可备一把伞** — 降水概率约 {rain}%")
    else:
        lines.append(f"☂️ **不需要带伞** — 降水概率仅 {rain}%")

    uv = int(weather["uv_index"])
    if uv >= 8:
        lines.append(f"🧴 **必须遮阳** — 紫外线极强（{uv}级），涂防晒霜+戴帽子墨镜")
    elif uv >= 6:
        lines.append(f"🧴 **需要遮阳** — 紫外线较强（{uv}级），建议涂防晒霜")
    elif uv >= 3:
        lines.append(f"🧴 **注意防晒** — 紫外线中等（{uv}级），敏感人群注意防护")
    else:
        lines.append(f"🧴 **无需特别防晒** — 紫外线较弱（{uv}级）")

    max_t = int(weather["max_temp"])
    if max_t >= 32:
        lines.append("👕 穿短袖短裤，注意防暑降温，多补水")
    elif max_t >= 25:
        lines.append("👕 穿短袖或薄长袖，舒适为主")
    elif max_t >= 18:
        lines.append("🧥 穿长袖+薄外套，早晚稍凉")
    elif max_t >= 10:
        lines.append("🧥 穿外套+毛衣，注意保暖")
    else:
        lines.append("🧥 穿厚外套+毛衣，天气寒冷")

    return "\n".join(lines)


# ============== 黄金模块 ==============
def get_usd_cny_rate():
    """获取美元兑人民币汇率"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://finance.sina.com.cn/",
        }
        url = "https://hq.sinajs.cn/list=fx_susdcnh"
        resp = requests.get(url, headers=headers, timeout=10)
        text = resp.content.decode("gbk")
        parts = text.split('"')[1].split(",")
        # 格式：时间,买入价,卖出价,当前价,...,名称
        if len(parts) >= 4:
            rate = float(parts[3])
            return rate
    except Exception as e:
        print(f"[WARN] 获取汇率失败: {e}")
    return None


def get_gold_price():
    """获取黄金行情"""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://finance.sina.com.cn/",
    }

    # 1. 伦敦金现（国际现货）
    london_gold = None
    try:
        url = "https://hq.sinajs.cn/list=hf_XAU"
        resp = requests.get(url, headers=headers, timeout=10)
        text = resp.content.decode("gbk")
        parts = text.split('"')[1].split(",")
        # 格式：当前价,昨收,买入价,卖出价,最高,最低,时间,昨收2,今开,...,名称
        if len(parts) >= 9:
            current = float(parts[0])
            prev_close = float(parts[1]) if parts[1] else float(parts[7])
            change = current - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            london_gold = {
                "current": current,
                "prev_close": prev_close,
                "change": change,
                "change_pct": change_pct,
            }
            results.append({
                "name": "伦敦金现（国际现货）",
                "price": f"{current:.2f}",
                "unit": "美元/盎司",
                "change": f"{change:+.2f}",
                "change_pct": f"{change_pct:+.2f}%",
                "is_up": change >= 0,
            })
    except Exception as e:
        print(f"[WARN] 获取伦敦金现失败: {e}")

    # 2. 人民币金价（根据伦敦金现 + 汇率换算）
    if london_gold:
        rate = get_usd_cny_rate()
        if rate and rate > 0:
            cny_price = london_gold["current"] * rate / OZ_TO_GRAM
            cny_prev = london_gold["prev_close"] * rate / OZ_TO_GRAM
            cny_change = cny_price - cny_prev
            cny_change_pct = (cny_change / cny_prev) * 100 if cny_prev else 0
            results.append({
                "name": "人民币金价（参考）",
                "price": f"{cny_price:.2f}",
                "unit": "元/克",
                "change": f"{cny_change:+.2f}",
                "change_pct": f"{cny_change_pct:+.2f}%",
                "is_up": cny_change >= 0,
            })

    # 3. 纽约黄金期货
    try:
        url = "https://hq.sinajs.cn/list=hf_GC"
        resp = requests.get(url, headers=headers, timeout=10)
        text = resp.content.decode("gbk")
        parts = text.split('"')[1].split(",")
        # 格式：当前价,涨跌额(空),买入价,卖出价,最高,最低,时间,昨收,今开,...,名称
        if len(parts) >= 8:
            current = float(parts[0])
            prev_close = float(parts[7]) if parts[7] else 0
            if prev_close > 0:
                change = current - prev_close
                change_pct = (change / prev_close) * 100
                results.append({
                    "name": "纽约黄金期货",
                    "price": f"{current:.2f}",
                    "unit": "美元/盎司",
                    "change": f"{change:+.2f}",
                    "change_pct": f"{change_pct:+.2f}%",
                    "is_up": change >= 0,
                })
    except Exception as e:
        print(f"[WARN] 获取纽约黄金期货失败: {e}")

    return results


def gold_summary(gold_list):
    """黄金行情简评"""
    if not gold_list:
        return "⚠️ 黄金数据获取失败。"

    up_count = sum(1 for g in gold_list if g["is_up"])
    down_count = len(gold_list) - up_count

    if up_count > down_count:
        trend = "全线上涨" if up_count == len(gold_list) else "多数上涨"
    elif down_count > up_count:
        trend = "全线下跌" if down_count == len(gold_list) else "多数下跌"
    else:
        trend = "涨跌互现"

    max_change = max(gold_list, key=lambda x: abs(float(x["change_pct"].replace("%", ""))))

    return (
        f"**简评：** 今日黄金{trend}，"
        f"{max_change['name']}波动最大（{max_change['change_pct']}）。"
        f"人民币金价由伦敦金现按实时汇率换算，仅供参考。"
    )


# ============== 邮件模块 ==============
def build_email_content(weather, gold_list, date_str):
    """构建邮件正文（HTML 格式）"""
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()
    weekday = weekday_map[now.weekday()]

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
  .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .header p {{ margin: 8px 0 0; opacity: 0.9; font-size: 14px; }}
  .section {{ padding: 20px 24px; border-bottom: 1px solid #eee; }}
  .section:last-child {{ border-bottom: none; }}
  .section-title {{ font-size: 16px; font-weight: bold; color: #333; margin: 0 0 12px; display: flex; align-items: center; }}
  .section-title span {{ margin-right: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 10px 8px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
  th {{ background: #f8f9fa; color: #666; font-weight: 600; }}
  .up {{ color: #e74c3c; font-weight: 600; }}
  .down {{ color: #27ae60; font-weight: 600; }}
  .advice {{ background: #f8f9fa; border-radius: 8px; padding: 12px 16px; font-size: 14px; line-height: 1.8; color: #444; }}
  .advice p {{ margin: 4px 0; }}
  .footer {{ text-align: center; padding: 16px; font-size: 12px; color: #999; background: #fafafa; }}
  .weather-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px; margin-bottom: 12px; }}
  .weather-item {{ display: flex; justify-content: space-between; padding: 6px 0; }}
  .weather-item .label {{ color: #888; }}
  .weather-item .value {{ color: #333; font-weight: 500; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📅 每日日报</h1>
    <p>{date_str} {weekday}</p>
  </div>
"""

    # 天气部分
    html += """
  <div class="section">
    <div class="section-title"><span>🌤️</span> 成都今日天气</div>
"""
    if weather:
        html += f"""
    <div class="weather-grid">
      <div class="weather-item"><span class="label">天气状况</span><span class="value">{weather['desc']}</span></div>
      <div class="weather-item"><span class="label">气温范围</span><span class="value">{weather['min_temp']}℃ ~ {weather['max_temp']}℃</span></div>
      <div class="weather-item"><span class="label">当前温度</span><span class="value">{weather['temp_c']}℃（体感 {weather['feels_like']}℃）</span></div>
      <div class="weather-item"><span class="label">紫外线</span><span class="value">{weather['uv_index']}级</span></div>
      <div class="weather-item"><span class="label">降水概率</span><span class="value">{weather['rain_chance']}%</span></div>
      <div class="weather-item"><span class="label">湿度</span><span class="value">{weather['humidity']}%</span></div>
      <div class="weather-item"><span class="label">风力</span><span class="value">{weather['wind_dir']} {weather['wind_speed']}km/h</span></div>
      <div class="weather-item"><span class="label">日出/日落</span><span class="value">{weather['sunrise']} / {weather['sunset']}</span></div>
    </div>
    <div class="advice">
      <p><strong>出行建议：</strong></p>
      <p>{weather_advice(weather).replace(chr(10), '</p><p>')}</p>
    </div>
"""
    else:
        html += '<p style="color:#999;">天气数据获取失败，请自行查看天气预报。</p>'
    html += "</div>"

    # 黄金部分
    html += """
  <div class="section">
    <div class="section-title"><span>💰</span> 黄金行情</div>
"""
    if gold_list:
        html += """
    <table>
      <thead>
        <tr><th>品种</th><th>最新价</th><th>涨跌</th><th>涨跌幅</th></tr>
      </thead>
      <tbody>
"""
        for g in gold_list:
            cls = "up" if g["is_up"] else "down"
            arrow = "↑" if g["is_up"] else "↓"
            html += f"""
        <tr>
          <td>{g['name']}</td>
          <td>{g['price']} {g['unit']}</td>
          <td class="{cls}">{arrow} {g['change']}</td>
          <td class="{cls}">{g['change_pct']}</td>
        </tr>
"""
        html += f"""
      </tbody>
    </table>
    <div class="advice" style="margin-top:12px;">
      <p>{gold_summary(gold_list)}</p>
    </div>
"""
    else:
        html += '<p style="color:#999;">黄金数据获取失败。</p>'
    html += "</div>"

    # 页脚
    html += """
  <div class="footer">
    本邮件由 GitHub Actions 自动生成，每日早8点发送<br>
    数据来源：wttr.in / 新浪财经
  </div>
</div>
</body>
</html>
"""
    return html


def send_email(subject, html_content):
    """通过 QQ 邮箱 SMTP 发送邮件（支持多个收件人）"""
    if not SMTP_PASSWORD:
        print("[ERROR] 未设置 QQ_MAIL_AUTH_CODE 环境变量")
        return False

    if not RECEIVER_EMAILS:
        print("[ERROR] 收件人列表为空")
        return False

    try:
        msg = MIMEMultipart("alternative")
        from_name = Header("每日日报", "utf-8").encode()
        msg["From"] = f"{from_name} <{SENDER_EMAIL}>"
        # 多个收件人用逗号分隔
        msg["To"] = ", ".join(RECEIVER_EMAILS)
        msg["Subject"] = Header(subject, "utf-8")

        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        # 发送给所有收件人
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_string())
        server.quit()
        print(f"[OK] 邮件发送成功，共发送给 {len(RECEIVER_EMAILS)} 个收件人: {', '.join(RECEIVER_EMAILS)}")
        return True
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")
        return False


# ============== 主流程 ==============
def main():
    print("=" * 50)
    print("开始生成每日日报...")
    print("=" * 50)

    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    subject = f"{date_str} 日报总结"

    # 1. 获取天气
    print("\n[1/3] 获取成都天气...")
    weather = get_weather()
    if weather:
        print(f"  → {weather['desc']}, {weather['min_temp']}~{weather['max_temp']}℃")
    else:
        print("  → 获取失败")

    # 2. 获取黄金
    print("\n[2/3] 获取黄金行情...")
    gold_list = get_gold_price()
    for g in gold_list:
        print(f"  → {g['name']}: {g['price']} {g['change_pct']}")

    # 3. 生成并发送邮件
    print("\n[3/3] 生成邮件并发送...")
    html_content = build_email_content(weather, gold_list, date_str)
    success = send_email(subject, html_content)

    if success:
        print(f"\n✅ 日报已发送至 {len(RECEIVER_EMAILS)} 个邮箱: {', '.join(RECEIVER_EMAILS)}")
        sys.exit(0)
    else:
        print("\n❌ 日报发送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
