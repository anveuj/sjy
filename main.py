import random
import logging
from time import localtime
from requests import get, post
from datetime import datetime, date
from zhdate import ZhDate
import sys
import os

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_color():
    """获取随机颜色"""
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    color_list = get_colors(100)
    return random.choice(color_list)


def get_config():
    """读取配置文件"""
    try:
        with open("config.txt", encoding="utf-8") as f:
            return eval(f.read())
    except FileNotFoundError:
        logging.error("推送消息失败，请检查config.txt文件是否与程序位于同一路径")
        os.system("pause")
        sys.exit(1)
    except SyntaxError:
        logging.error("推送消息失败，请检查配置文件格式是否正确")
        os.system("pause")
        sys.exit(1)


def get_request_headers():
    """获取通用请求头"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }


def get_access_token(config):
    """获取微信 access_token"""
    app_id = config["app_id"]
    app_secret = config["app_secret"]
    post_url = (
        f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    try:
        response = get(post_url, headers=get_request_headers())
        response.raise_for_status()
        return response.json()['access_token']
    except KeyError:
        logging.error("获取access_token失败，请检查app_id和app_secret是否正确")
        os.system("pause")
        sys.exit(1)
    except Exception as e:
        logging.error(f"获取access_token时发生网络错误: {e}")
        os.system("pause")
        sys.exit(1)


def get_weather(region, config):
    """获取天气信息"""
    key = config["weather_key"]
    region_url = f"https://geoapi.qweather.com/v2/city/lookup?location={region}&key={key}"
    try:
        response = get(region_url, headers=get_request_headers())
        response.raise_for_status()
        response = response.json()
        if response["code"] == "404":
            logging.error("推送消息失败，请检查地区名是否有误！")
            os.system("pause")
            sys.exit(1)
        elif response["code"] == "401":
            logging.error("推送消息失败，请检查和风天气key是否正确！")
            os.system("pause")
            sys.exit(1)
        else:
            location_id = response["location"][0]["id"]
    except Exception as e:
        logging.error(f"获取地区ID时发生网络错误: {e}")
        return None, None, None, None

    weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={key}"
    try:
        response = get(weather_url, headers=get_request_headers())
        response.raise_for_status()
        response = response.json()
        if "now" in response:
            now_data = response["now"]
            weather = now_data.get("text", "暂无数据")
            temp = now_data.get("temp")
            if temp is not None:
                temp += u"\N{DEGREE SIGN}" + "C"
            else:
                temp = "暂无数据"
            wind_dir = now_data.get("windDir", "暂无数据")
            air_humidity = now_data.get("humidity", "暂无数据")
            return weather, temp, wind_dir, air_humidity
        else:
            logging.error("天气接口响应数据中不存在 'now' 键:", response)
            return None, None, None, None
    except Exception as e:
        logging.error(f"获取天气信息时发生网络错误: {e}")
        return None, None, None, None


def get_birthday(birthday, year, today):
    """计算距离下次生日的天数"""
    birthday_year = birthday.split("-")[0]
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        try:
            birthday = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            logging.error("请检查生日的日子是否在今年存在")
            os.system("pause")
            sys.exit(1)
        birthday_month = birthday.month
        birthday_day = birthday.day
        year_date = date(year, birthday_month, birthday_day)
    else:
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        year_date = date(year, birthday_month, birthday_day)

    if today > year_date:
        if birthday_year[0] == "r":
            r_last_birthday = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last_birthday.month, r_last_birthday.day)
        else:
            birth_date = date((year + 1), birthday_month, birthday_day)
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    return birth_day


def get_ciba():
    """获取词霸每日金句"""
    url = "http://open.iciba.com/dsapi/"
    try:
        response = get(url, headers=get_request_headers())
        response.raise_for_status()
        note_en = response.json()["content"]
        note_ch = response.json()["note"]
        return note_ch, note_en
    except Exception as e:
        logging.error(f"获取词霸每日金句时发生网络错误: {e}")
        return "获取金句失败", "Failed to get sentence"


def send_message(to_user, access_token, region_name, weather, temp, wind_dir, air_humidity, note_ch, note_en, config):
    """发送微信消息模板"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday
    today = datetime.date(datetime(year=year, month=month, day=day))
    week = week_list[today.isoweekday() % 7]

    love_year = int(config["love_date"].split("-")[0])
    love_month = int(config["love_date"].split("-")[1])
    love_day = int(config["love_date"].split("-")[2])
    love_date = date(love_year, love_month, love_day)
    love_days = str(today.__sub__(love_date)).split(" ")[0]

    birthdays = {}
    for k, v in config.items():
        if k[0:5] == "birth":
            birthdays[k] = v

    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": f"{today} {week}",
                "color": get_color()
            },
            "region": {
                "value": region_name,
                "color": get_color()
            },
            "weather": {
                "value": weather,
                "color": get_color()
            },
            "temp": {
                "value": temp,
                "color": get_color()
            },
            "wind_dir": {
                "value": wind_dir,
                "color": get_color()
            },
            "air_humidity": {
                "value": air_humidity,
                "color": get_color()
            },
            "love_day": {
                "value": love_days,
                "color": get_color()
            },
            "note_en": {
                "value": note_en,
                "color": get_color()
            },
            "note_ch": {
                "value": note_ch,
                "color": get_color()
            }
        }
    }

    for key, value in birthdays.items():
        birth_day = get_birthday(value["birthday"], year, today)
        if birth_day == 0:
            birthday_data = f"{value['name']}的生日emmm。。。就是今天！，祝{value['name']}生日快乐！！！"
        else:
            birthday_data = f"{value['name']}的生日还有{birth_day}天"
        data["data"][key] = {"value": birthday_data, "color": get_color()}

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': get_request_headers()['User-Agent']
    }
    for field, field_data in data["data"].items():
        logging.info(f"Field: {field}, Color: {field_data['color']}")
    try:
        response = post(url, headers=headers, json=data)
        response.raise_for_status()
        response = response.json()
        if response["errcode"] == 40037:
            logging.error("推送消息失败，请检查模板id是否正确")
        elif response["errcode"] == 40036:
            logging.error("推送消息失败，请检查模板id是否为空")
        elif response["errcode"] == 40003:
            logging.error("推送消息失败，请检查微信号是否正确")
        elif response["errcode"] == 0:
            logging.info("推送消息成功")
        else:
            logging.error(response)
    except Exception as e:
        logging.error(f"发送微信消息模板时发生网络错误: {e}")


if __name__ == "__main__":
    config = get_config()
    accessToken = get_access_token(config)
    users = config["user"]
    region = config["region"]
    weather, temp, wind_dir, air_humidity = get_weather(region, config)
    note_ch = config["note_ch"]
    note_en = config["note_en"]
    if note_ch == "" and note_en == "":
        note_ch, note_en = get_ciba()

    for user in users:
        if weather and temp and wind_dir:
            send_message(user, accessToken, region, weather, temp, wind_dir, air_humidity, note_ch, note_en, config)
        else:
            logging.error("未获取到有效的天气信息，无法发送消息给用户:", user)
    os.system("pause")
