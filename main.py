import requests
from bs4 import BeautifulSoup
import os
import datetime
from datetime import timezone, timedelta

# ================= ⚙️ 配置区域 =================
# 1. PushPlus Token
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')

# 2. 目标频道 ID
CHANNEL_ID = 'alpha123cn' 

# 3. 监控时间窗口 (分钟)
TIME_WINDOW_MINUTES = 250

# 4. 定义北京时区 (UTC+8)
SHA_TZ = timezone(timedelta(hours=8))
# ===============================================

BASE_URL = f"https://t.me/s/{CHANNEL_ID}"

def send_wechat(raw_html_content, link, post_time_str, plain_title):
    if not PUSHPLUS_TOKEN: 
        print("⚠️ [推送跳过] 未配置 Token")
        return
        
    try:
        # 1. 标题处理：截取纯文本的前30个字
        title = plain_title[:30] + "..." if len(plain_title) > 30 else plain_title
        
        print(f"📨 [推送中] 标题: {title}")
        
        # 2. 扫描时间
        scan_time = datetime.datetime.now(SHA_TZ).strftime('%Y-%m-%d %H:%M:%S')

        # 3. 构建精美 HTML 排版
        # 注意：这里直接嵌入 raw_html_content，保留了 TG 的 <br> 换行
        html_body = (
            f"<div style='font-family: sans-serif; color: #333; line-height: 1.6;'>"
            f"  <div style='margin-bottom: 10px; padding-bottom: 10px; border-bottom: 2px solid #0088cc;'>"
            f"    <span style='font-size: 14px; color: #0088cc;'><b>🔔 Alpha 线报捕获</b></span>"
            f"    <div style='font-size: 12px; color: #888; margin-top: 5px;'>"
            f"      📅 发布时间: {post_time_str} (北京时间)"
            f"    </div>"
            f"  </div>"
            f"  <div style='font-size: 15px; background-color: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #0088cc;'>"
            f"    {raw_html_content}" 
            f"  </div>"
            f"  <div style='margin-top: 15px; text-align: center;'>"
            f"    <a href='{link}' style='display: inline-block; background-color: #0088cc; color: white; padding: 8px 20px; text-decoration: none; border-radius: 20px; font-size: 14px;'>👉 点击跳转到 Telegram</a>"
            f"  </div>"
            f"  <div style='margin-top: 20px; font-size: 12px; color: #aaa; text-align: right;'>"
            f"    🤖 扫描于: {scan_time}"
            f"  </div>"
            f"</div>"
        )
        
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": f"📢 {title}", # 标题不需要太复杂
            "content": html_body,
            "template": "html"
        }
        resp = requests.post(url, json=data, timeout=5)
        print(f"✅ [推送完成] 接口响应: {resp.text}")

    except Exception as e:
        print(f"❌ [推送失败] 错误信息: {e}")

def check_tg_web():
    print("="*50)
    print(f"🚀 [任务启动] 扫描频道: {CHANNEL_ID}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"❌ 访问失败: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message')
        
        if not messages:
            print("⚠️ 未找到消息。")
            return

        print(f"🔍 [解析] 发现 {len(messages)} 条消息。")

        now_utc = datetime.datetime.now(timezone.utc)
        processed_count = 0

        # 倒序遍历
        for msg in reversed(messages):
            processed_count += 1
            try:
                # 1. 获取时间
                time_tag = msg.find('time')
                if not time_tag: continue
                
                dt_str = time_tag.get('datetime')
                msg_dt_utc = datetime.datetime.fromisoformat(dt_str)
                diff_minutes = (now_utc - msg_dt_utc).total_seconds() / 60
                
                # 转换显示时间 (北京时间)
                msg_dt_bj = msg_dt_utc.astimezone(SHA_TZ)
                post_time_str = msg_dt_bj.strftime('%H:%M:%S')

                # 2. 判定窗口
                if 0 <= diff_minutes <= TIME_WINDOW_MINUTES:
                    print(f"🔥 发现新消息! 发布于 {post_time_str} ({diff_minutes:.1f}分前)")
                    
                    post_id = msg.get('data-post')
                    link = f"https://t.me/{post_id}"
                    
                    # === 核心修改区域 ===
                    text_div = msg.find('div', class_='tgme_widget_message_text')
                    if text_div:
                        # A. 提取纯文本用于标题 (把换行替换成空格，保持标题一行)
                        plain_title = text_div.get_text(separator=' ', strip=True)

                        # B. 提取 HTML 用于正文 (关键！不要 replace br 标签！)
                        # decode_contents() 会保留 <br>, <b>, <a> 等所有标签
                        html_content = text_div.decode_contents()
                        
                        # 发送
                        send_wechat(html_content, link, post_time_str, plain_title)
                    else:
                        print("   ⚠️ 图片/贴纸消息，无文字，跳过")
                
                elif diff_minutes > TIME_WINDOW_MINUTES:
                    break

            except Exception as e:
                print(f"❌ 解析错误: {e}")
                continue
        
        print(f"🏁 扫描结束。")

    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    check_tg_web()
