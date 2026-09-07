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
import random
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


# ============== 健身提示模块 ==============
FITNESS_TIPS = [
    "久坐每50分钟起身活动2分钟，做几组肩颈环绕，缓解颈椎压力。",
    "深蹲时膝盖不要超过脚尖，重心放在脚后跟，感受臀部发力。",
    "平板支撑时收紧核心，不要塌腰，保持身体一条直线，每次30秒起步。",
    "训练后拉伸10分钟，重点拉伸大腿前侧、后侧和臀部，减少次日酸痛。",
    "俯卧撑时双手略宽于肩，身体保持直线，下放时胸部接近地面。",
    "跑步前先快走5分钟热身，跑完不要立刻停下，慢走3分钟再做拉伸。",
    "硬拉时背部挺直，用腿部和臀部发力拉起，不要弯腰弓背。",
    "每天饮水2000ml以上，训练时每15分钟补充少量水分，不要等口渴才喝。",
    "卧推时肩胛骨收紧下沉，杠铃下落至胸部中下方，推起时手臂不要完全锁死。",
    "引体向上下放时控制速度，不要自由落体，感受背部肌肉拉伸。",
    "训练日保证7-8小时睡眠，肌肉在休息时生长，不是在训练时。",
    "蛋白质摄入每公斤体重1.2-1.6克，分散到三餐，帮助肌肉恢复。",
    "膝盖有弹响时减少深度深蹲，优先做半蹲和腿举，注重臀部发力保护膝关节。",
    "久坐人群多做髋屈肌拉伸，每侧30秒，改善骨盆前倾和腰部不适。",
    "力量训练先练大肌群（胸背腿），再练小肌群（肩臂腹），效率更高。",
    "热身不要只做静态拉伸，先做5分钟动态热身（高抬腿、开合跳），再开始训练。",
    "减重期间每周减重不超过体重的1%，过快减重会流失肌肉，降低基础代谢。",
    "训练时记录重量和次数，逐步递增负荷，肌肉才会持续生长（渐进超负荷）。",
    "饭后1小时再进行剧烈运动，避免肠胃不适；运动后30分钟内补充蛋白质和碳水。",
    "站姿时刻意收紧核心，肩膀下沉后展，改善圆肩驼背，提升气质。",
]


def get_fitness_tip():
    """随机获取一条健身提示"""
    return random.choice(FITNESS_TIPS)


# ============== 职场沟通技巧模块 ==============
WORKPLACE_TIPS = [
    "汇报问题先说结论+1个核心原因，最后说你需要什么支持，不要铺细节。",
    "接需求先确认三件事：截止时间、验收标准、优先级，避免做无用功。",
    "产线沟通先讲设备号+异常现象，再讲你的判断，最后说需要谁配合。",
    "被领导追问时，不确定就说\"我确认一下，10分钟内回复你\"，不要硬编答案。",
    "开会发言用三段式：现状是什么→问题在哪→建议怎么做，控制在30秒内。",
    "跨部门沟通先讲对方关心的利益点，再讲你的需求，对方才愿意配合。",
    "写邮件/消息标题写清楚\"什么事+需要谁做+截止时间\"，不要只写\"帮忙看一下\"。",
    "遇到冲突先复述对方观点（\"我理解你的意思是…\"），再表达自己的看法，避免情绪化。",
    "向上汇报进度用\"已完成X→正在做Y→下一步计划Z\"的结构，让领导一目了然。",
    "拒绝请求时先说\"我现在手头有A和B，优先级你看怎么排\"，把决定权交回去。",
    "提问前先自己想3个可能的答案，带着方案去问，比直接问\"怎么办\"专业得多。",
    "交接工作时写清楚：做了什么→做到哪一步→下一步谁接手→有什么风险点，不要口头交接。",
    "被表扬时大方说\"谢谢，这是和XX一起做的\"，既不谦虚过度也不独吞功劳。",
    "产线异常上报时附一张截图或设备面板照片，比纯文字描述效率高10倍。",
    "和老员工沟通多请教少争辩，先认可经验再提新想法，对方更容易接受。",
    "每日下班前花5分钟写今日小结：完成了什么、卡在哪、明天先做什么，长期坚持复盘能力会明显提升。",
    "遇到不懂的术语当场记下来，会后查清楚再问，不要在会上反复追问显得不专业。",
    "给领导发消息不要发长语音，文字分点写清楚，领导可以快速扫完。",
    "项目延期时主动提前说，附上原因和新的时间计划，不要等到截止日才说做不完。",
    "和同事协作时明确分工边界，\"这块我负责，那块你确认\"，避免事后扯皮。",
]


def get_workplace_tip():
    """随机获取一条职场沟通技巧"""
    return random.choice(WORKPLACE_TIPS)


# ============== 半导体专业术语模块 ==============
SEMICON_TERMS = [
    ("EAP", "Equipment Automation Program，设备自动化程序。EAP工程师的核心工作就是写和维护这个程序，负责MES系统和产线设备之间的通信调度。"),
    ("SECS/GEM", "SEMI标准的设备通信协议。SECS定义消息格式，GEM定义设备行为规范，是半导体厂设备和MES通信的通用语言，EAP必须吃透。"),
    ("MES", "Manufacturing Execution System，制造执行系统。管产线上每一片晶圆的流程、参数、追溯，EAP就是MES和设备之间的翻译官。"),
    ("FDC", "Fault Detection and Classification，故障检测与分类。实时采集设备传感器数据，用算法判断设备是否异常，是EAP进阶方向。"),
    ("APC", "Advanced Process Control，先进工艺控制。根据前一批的测量结果自动调整下一批的工艺参数，减少偏差，EAP需要理解其触发逻辑。"),
    ("R2R", "Run-to-Run Control，批次间控制。每跑完一批晶圆就根据反馈微调下一批参数，属于APC的一种，常见于CMP、刻蚀等工艺。"),
    ("EES", "Equipment Engineering System，设备工程系统。比EAP更上层，管设备的工程数据采集、分析、SPC监控，EAP工程师往上走常接触。"),
    ("SPC", "Statistical Process Control，统计过程控制。用控制图监控工艺参数是否在正常范围，超限报警，是产线质量管控的基础工具。"),
    ("Wafer Map", "晶圆图。把一片晶圆上每个die的测试结果（良/坏/类型）用颜色标在图上，EAP经常要解析和传递这个数据。"),
    ("Lot", "批次。产线上一批晶圆（通常25片）作为一个流转单位，EAP调度的基本单位就是Lot。"),
    ("Recipe", "配方/工艺程序。设备跑某道工艺时用的参数集合，EAP要负责把正确的Recipe下发给正确的设备。"),
    ("Carrier/Foup", "晶圆传送盒。装晶圆的容器，FOUP是12寸厂标准，EAP要跟踪哪个Carrier在哪个设备端口。"),
    ("Port", "设备端口。设备上放FOUP的位置，EAP要管理Port的状态（占用/空闲/异常）和晶圆上下料。"),
    ("Track In/Out", "进站/出站。晶圆进入某道工艺叫Track In，完成离开叫Track Out，EAP要把这两个事件准确报给MES。"),
    ("OHT", "Overhead Hoist Transport，天车传输系统。12寸厂晶圆在设备间靠头顶的天车搬运，EAP要和OHT系统配合调度上下料。"),
    ("AGV", "Automated Guided Vehicle，自动导引车。部分厂区用地面小车搬晶圆，和OHT对应，EAP同样要配合调度。"),
    ("Chamber", "工艺腔。设备内部真正做工艺的腔体，一台设备可能有多个Chamber，EAP要管理每个Chamber的状态和Recipe。"),
    ("PM", "Preventive Maintenance，预防性维护。设备定期保养，EAP要在PM期间锁定设备，避免MES派活过来。"),
    ("Interlock", "联锁。设备的安全机制，比如门没关好就不能启动工艺，EAP要处理Interlock触发时的异常流程。"),
    ("Alarm", "报警。设备异常时发出的告警，EAP要采集Alarm信息、分级、上报MES，严重的要触发停机。"),
    ("CIM", "Computer Integrated Manufacturing，计算机集成制造。泛指工厂里所有自动化系统的总称，EAP属于CIM的一部分。"),
    ("Stripmap", "条带图。把多片晶圆的测试结果按条带排列展示，用于分析工艺均匀性，EAP数据可视化常用。"),
    ("Yield", "良率。一片晶圆上合格die占总数的比例，是半导体厂最核心的指标，EAP所有工作最终都服务于Yield。"),
    ("CD", "Critical Dimension，关键尺寸。光刻后线条的宽度，是工艺控制的核心参数，EAP常配合APC做CD的闭环控制。"),
    ("Overlay", "套刻精度。前后两层光刻图案的对齐偏差，EAP要配合APC根据Overlay测量结果调整下一批曝光参数。"),
]


def get_semicon_term():
    """随机获取一个半导体专业术语及解释"""
    return random.choice(SEMICON_TERMS)


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
def build_email_content(weather, gold_list, fitness_tip, workplace_tip, semicon_term, date_str):
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

    # 健身提示部分
    html += f"""
  <div class="section">
    <div class="section-title"><span>💪</span> 每日健身提示</div>
    <div class="advice">
      <p>{fitness_tip}</p>
    </div>
  </div>
"""

    # 职场沟通技巧部分
    html += f"""
  <div class="section">
    <div class="section-title"><span>💼</span> 职场沟通小技巧</div>
    <div class="advice">
      <p>{workplace_tip}</p>
    </div>
  </div>
"""

    # 半导体专业术语部分
    term_name, term_desc = semicon_term
    html += f"""
  <div class="section">
    <div class="section-title"><span>🔬</span> 半导体术语小课堂</div>
    <div class="advice">
      <p><strong>{term_name}</strong>：{term_desc}</p>
    </div>
  </div>
"""

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
    print("\n[1/6] 获取成都天气...")
    weather = get_weather()
    if weather:
        print(f"  → {weather['desc']}, {weather['min_temp']}~{weather['max_temp']}℃")
    else:
        print("  → 获取失败")

    # 2. 获取黄金
    print("\n[2/6] 获取黄金行情...")
    gold_list = get_gold_price()
    for g in gold_list:
        print(f"  → {g['name']}: {g['price']} {g['change_pct']}")

    # 3. 获取健身提示
    print("\n[3/6] 获取健身提示...")
    fitness_tip = get_fitness_tip()
    print(f"  → {fitness_tip[:30]}...")

    # 4. 获取职场沟通技巧
    print("\n[4/6] 获取职场沟通技巧...")
    workplace_tip = get_workplace_tip()
    print(f"  → {workplace_tip[:30]}...")

    # 5. 获取半导体术语
    print("\n[5/6] 获取半导体术语...")
    semicon_term = get_semicon_term()
    print(f"  → {semicon_term[0]}: {semicon_term[1][:30]}...")

    # 6. 生成并发送邮件
    print("\n[6/6] 生成邮件并发送...")
    html_content = build_email_content(weather, gold_list, fitness_tip, workplace_tip, semicon_term, date_str)
    success = send_email(subject, html_content)

    if success:
        print(f"\n✅ 日报已发送至 {len(RECEIVER_EMAILS)} 个邮箱: {', '.join(RECEIVER_EMAILS)}")
        sys.exit(0)
    else:
        print("\n❌ 日报发送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
