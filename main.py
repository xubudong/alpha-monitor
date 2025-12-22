import cloudscraper
import os
import time
from datetime import datetime

# ================= ⚙️ 配置区域 =================
# 从 GitHub Secrets 读取 Token，如果本地运行则使用默认值
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')
API_URL = 'https://alpha123.uk/api/data?fresh=1'
# ===============================================

def send_wechat(title, content):
    """发送微信推送"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return
    
    try:
        # 推送服务不需要过盾，直接用 requests 即可 (cloudscraper 也可以)
        scraper = cloudscraper.create_scraper()
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": content,
            "template": "html"
        }
        scraper.post(url, json=data)
        print(f"✅ 推送已发送: {title}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def check_alpha123():
    print(f"🚀 开始扫描 Alpha123... [{datetime.now().strftime('%H:%M:%S')}]")
    
    # 使用 cloudscraper 自动处理 5秒盾
    scraper = cloudscraper.create_scraper()

    try:
        # 设置超时，防止卡死
        resp = scraper.get(API_URL, timeout=20)
        
        if resp.status_code != 200:
            print(f"❌ 接口请求失败: {resp.status_code}")
            return

        data = resp.json()
        airdrops = data.get('airdrops', [])
        
        # 获取服务器时间 (System Timestamp)
        server_ts = data.get('system_timestamp')
        if server_ts:
            now = datetime.fromtimestamp(server_ts)
        else:
            now = datetime.now()
            
        print(f"🕒 当前基准时间: {now.strftime('%Y-%m-%d %H:%M')}")
        print(f"🔍 扫描到 {len(airdrops)} 个项目")

        for item in airdrops:
            name = item.get('name')
            token = item.get('token')
            date_str = item.get('date')
            time_str = item.get('time')
            completed = item.get('completed') # 是否已结束

            # 跳过已结束或时间无效的项目
            if completed or not (date_str and time_str):
                continue

            try:
                # 解析目标时间
                target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                
                # 计算剩余分钟数
                diff = target_dt - now
                minutes_left = diff.total_seconds() / 60
                
                # 打印日志方便调试
                # print(f"   [{token}] 剩余: {minutes_left:.1f} 分钟")

                # ================= 核心修改 =================
                # 触发条件：20分钟内 (0 < 剩余时间 <= 20)
                # ===========================================
                if 0 < minutes_left <= 20:
                    print(f"🔥 命中报警规则: {token} (剩余 {minutes_left:.1f} 分钟)")
                    
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
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    check_alpha123()
