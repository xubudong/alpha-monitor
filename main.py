from curl_cffi import requests as cffi_requests # 用于过盾
import requests as normal_requests # 用于推送
import os
import time
import random
from datetime import datetime

# ================= ⚙️ 配置区域 =================
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')
API_URL = 'https://alpha123.uk/api/data?fresh=1'

# 重试配置
MAX_RETRIES = 5        # 重试次数
TIMEOUT_SECONDS = 30   # 超时时间 (30秒)
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

def check_alpha123():
    print(f"🚀 开始扫描 Alpha123... [{datetime.now().strftime('%H:%M:%S')}]")
    
    response = None
    
    # === 🔄 重试循环机制 ===
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"📡 尝试第 {attempt}/{MAX_RETRIES} 次请求 (超时30s)...")
            
            # 使用 curl_cffi 伪装 Chrome 120
            # 随机化 impersonate 版本有时能提高通过率
            browser_ver = random.choice(["chrome110", "chrome120", "safari15_5"])
            
            response = cffi_requests.get(
                API_URL, 
                impersonate=browser_ver, 
                timeout=TIMEOUT_SECONDS
            )
            
            # 如果是 200，直接跳出循环，去处理数据
            if response.status_code == 200:
                print("✅ 接口连接成功！")
                break
            
            # 如果是 403，说明被盾了
            elif response.status_code == 403:
                print(f"❌ 遇到 403 Forbidden (Cloudflare 拦截)")
            else:
                print(f"❌ 状态码异常: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 请求发生错误: {e}")
        
        # 如果还没成功，且不是最后一次，就休息一会
        if attempt < MAX_RETRIES:
            wait_time = attempt * 3  # 第一次等3秒，第二次等6秒，第三次9秒...
            print(f"⏳ 等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    # === 🛑 循环结束后的判断 ===
    if not response or response.status_code != 200:
        print("💀 5次重试全部失败，放弃本次扫描。")
        return

    # === ✅ 数据处理逻辑 (只有成功才会走到这里) ===
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
                target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                diff = target_dt - now
                minutes_left = diff.total_seconds() / 60
                
                # print(f"   项目: {token} | 剩余: {minutes_left:.1f} 分钟")

                # 触发条件：20分钟内
                if 0 < minutes_left <= 20:
                    print(f"🔥 命中报警: {token} (剩余 {minutes_left:.1f} 分钟)")
                    chain = item.get('chain_id', '未知')
                    contract = item.get('contract_address', '暂无')
                    
                    msg = (
                        f"<b>⚡ 空投最后倒计时 (20分钟内)</b><br><br>"
                        f"💎 项目: {token} ({name})<br>"
                        f"⏰ 开始时间: {time_str}<br>"
                        f"⏳ 剩余时间: {int(minutes_left)} 分钟<br>"
                        f"🔗 链ID: {chain}<br>"
                        f"📝 合约: {contract}<br>"
                    )
                    send_wechat(f"🚀 {token} 马上开始", msg)
                
            except ValueError:
                continue

    except Exception as e:
        print(f"❌ 数据解析出错: {e}")

if __name__ == "__main__":
    check_alpha123()
