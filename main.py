import cloudscraper
import requests as normal_requests
import os
import time
from datetime import datetime

# ================= ⚙️ 配置区域 =================
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')
API_URL = 'https://alpha123.uk/api/data?fresh=1'
MAX_RETRIES = 5  # 重试次数
# ===============================================

def send_wechat(title, content):
    """发送微信推送"""
    if not PUSHPLUS_TOKEN:
        print(f"⚠️ 未配置 Token，模拟推送: {title}")
        return
    
    try:
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": content,
            "template": "html"
        }
        normal_requests.post(url, json=data, timeout=10)
        print(f"✅ 推送已发送: {title}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def check_alpha123_auto():
    print(f"🚀 启动自动扫描 (cloudscraper版)... [{datetime.now().strftime('%H:%M:%S')}]")

    # 创建 scraper 实例
    # browser 参数模拟不同的浏览器，有助于绕过某些检测
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    response = None

    # === 🔄 重试循环 ===
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"📡 第 {attempt}/{MAX_RETRIES} 次尝试连接...")
            
            # Cloudscraper 的请求方式
            response = scraper.get(API_URL, timeout=30)
            
            if response.status_code == 200:
                print("✅ 穿透成功！")
                break
            elif response.status_code == 403:
                print("❌ 403 Forbidden - 盾太厚了")
            else:
                print(f"❌ 状态码: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 请求出错: {e}")

        # 失败等待
        if attempt < MAX_RETRIES:
            time.sleep(attempt * 5) # 5s, 10s, 15s...

    # === 🛑 最终检查 ===
    if not response or response.status_code != 200:
        print("💀 所有重试均失败，放弃。")
        return

    # === 📊 数据处理 ===
    try:
        data = response.json()
        airdrops = data.get('airdrops', [])
        
        server_ts = data.get('system_timestamp')
        now = datetime.fromtimestamp(server_ts) if server_ts else datetime.now()
        
        print(f"🕒 基准时间: {now.strftime('%Y-%m-%d %H:%M')}")
        print(f"🔍 扫描到 {len(airdrops)} 个项目")

        for item in airdrops:
            name = item.get('name')
            token = item.get('token')
            date_str = item.get('date')
            time_str = item.get('time')
            completed = item.get('completed')

            if completed or not (date_str and time_str):
                continue

            try:
                # 解析时间
                target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                diff = target_dt - now
                minutes_left = diff.total_seconds() / 60
                
                # print(f"   项目: {token} | 剩余: {minutes_left:.1f} 分钟")

                # ==========================================
                # 🚨 触发条件：20分钟内 (0 < x <= 20)
                # ==========================================
                if 0 < minutes_left <= 20:
                    print(f"🔥 触发报警: {token}")
                    
                    chain = item.get('chain_id', '未知')
                    contract = item.get('contract_address', '暂无')
                    
                    msg = (
                        f"<b>⏳ 空投倒计时 (20分钟内)</b><br><br>"
                        f"💎 币种: {token} ({name})<br>"
                        f"⏰ 时间: {time_str}<br>"
                        f"⏳ 剩余: {int(minutes_left)} 分钟<br>"
                        f"🔗 链: {chain}<br>"
                        f"📝 合约: {contract}"
                    )
                    send_wechat(f"🚀 {token} 即将开始", msg)

            except ValueError:
                continue

    except Exception as e:
        print(f"❌ 解析出错: {e}")

if __name__ == "__main__":
    check_alpha123_auto()
