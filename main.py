import requests
from bs4 import BeautifulSoup
import os
import datetime
from datetime import timezone

# ================= ⚙️ 配置区域 =================
# 1. PushPlus Token
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')

# 2. 目标频道 ID (直接用你提供的)
CHANNEL_ID = 'alpha123cn' 

# 3. 监控时间窗口 (分钟)
# 脚本每 5 分钟跑一次，我们设为 6 分钟，防止边缘时间漏单
TIME_WINDOW_MINUTES = 6
# ===============================================

BASE_URL = f"https://t.me/s/{CHANNEL_ID}"

def send_wechat(content, link, post_time):
    if not PUSHPLUS_TOKEN: 
        print("⚠️ 未配置 Token，跳过推送")
        return
        
    try:
        # 简单提取标题
        clean_text = content.replace('<br>', ' ').strip()
        title = clean_text[:20] + "..." if len(clean_text) > 20 else clean_text
        
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": f"📢 Alpha线报: {title}",
            "content": (
                f"<b>⌚ 时间:</b> {post_time}<br>"
                f"<b>📄 内容:</b><br>{content}<br><br>"
                f"<a href='{link}'>👉 点击跳转到 Telegram</a>"
            ),
            "template": "html"
        }
        requests.post(url, json=data, timeout=5)
        print("✅ 推送已发送")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def check_tg_web():
    print(f"🚀 开始扫描频道: {CHANNEL_ID} ...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"❌ 访问失败: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 找到所有的消息容器
        messages = soup.find_all('div', class_='tgme_widget_message')
        
        if not messages:
            print("⚠️ 未找到消息，可能是频道为空。")
            return

        print(f"🔍 页面共获取到 {len(messages)} 条消息，正在检查最新消息...")

        # 获取当前 UTC 时间 (TG 网页版的时间标签是 UTC 格式)
        now_utc = datetime.datetime.now(timezone.utc)

        # 倒序遍历（从最新消息看起）
        for msg in reversed(messages):
            try:
                # 1. 获取发布时间
                time_tag = msg.find('time')
                if not time_tag: continue
                
                # datetime 属性格式: "2025-12-22T14:30:15+00:00"
                dt_str = time_tag.get('datetime')
                msg_dt = datetime.datetime.fromisoformat(dt_str)
                
                # 2. 计算时间差 (当前时间 - 消息时间)
                diff = now_utc - msg_dt
                diff_minutes = diff.total_seconds() / 60
                
                # 调试日志
                # print(f"消息时间: {msg_dt} | 距今: {diff_minutes:.1f} 分钟")

                # 3. 判断：是否在监控窗口内 (比如过去 6 分钟内发的)
                if 0 <= diff_minutes <= TIME_WINDOW_MINUTES:
                    print(f"🔥 发现新消息! (发布于 {diff_minutes:.1f} 分钟前)")
                    
                    # 提取消息 ID 和链接
                    post_id = msg.get('data-post')
                    link = f"https://t.me/{post_id}"
                    
                    # 提取文字内容
                    text_div = msg.find('div', class_='tgme_widget_message_text')
                    if text_div:
                        # 处理换行，让推送更好看
                        for br in text_div.find_all("br"):
                            br.replace_with("\n")
                        
                        # 获取 HTML 内容用于推送
                        html_content = text_div.decode_contents()
                        
                        # 发送！
                        send_wechat(html_content, link, msg_dt.strftime('%H:%M:%S'))
                    else:
                        print("⚠️ 消息为图片/贴纸，无文字，跳过。")
                
                elif diff_minutes > TIME_WINDOW_MINUTES:
                    # 如果遇到一条超过 6 分钟的消息，说明后面的更早，直接停止，节省资源
                    # print("✅ 后续消息已过期，停止扫描。")
                    break
                    
            except Exception as e:
                print(f"❌ 解析单条消息出错: {e}")
                continue

    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    check_tg_web()
