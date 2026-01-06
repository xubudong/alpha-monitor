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
TIME_WINDOW_MINUTES = os.environ.get('TIME_WINDOW')

# 4. 定义北京时区 (UTC+8)
SHA_TZ = timezone(timedelta(hours=8))
# ===============================================

BASE_URL = f"https://t.me/s/{CHANNEL_ID}"

def send_wechat(raw_html_content, link, post_time_str, plain_title):
    if not PUSHPLUS_TOKEN: 
        print("⚠️ [推送跳过] 未配置 Token")
        return
        
    try:
        # 1. 标题优化：使用提取好的纯文本标题，截取前30字
        title = plain_title[:30] + "..." if len(plain_title) > 30 else plain_title
        
        print(f"📨 [推送中] 标题: {title}")
        
        # 2. 获取扫描时间 (北京时间)
        scan_time = datetime.datetime.now(SHA_TZ).strftime('%Y-%m-%d %H:%M:%S')

        # 3. 排版优化：使用 HTML 卡片样式，保留 raw_html_content 里的换行
        html_body = (
            f"<div style='border-left: 4px solid #0088cc; padding-left: 10px; margin-bottom: 10px;'>"
            f"  <div style='font-size: 14px; color: #333; font-weight: bold;'>{title}</div>"
            f"  <div style='font-size: 12px; color: #888;'>📅 发布: {post_time_str} (北京时间)</div>"
            f"</div>"
            f"<div style='background-color: #f9f9f9; padding: 15px; border-radius: 5px; font-size: 15px; line-height: 1.6; color: #333;'>"
            f"  {raw_html_content}"
            f"</div>"
            f"<div style='margin-top: 15px; text-align: center;'>"
            f"  <a href='{link}' style='display: inline-block; background-color: #0088cc; color: white; padding: 8px 20px; text-decoration: none; border-radius: 20px; font-size: 14px;'>👉 点击跳转到 Telegram</a>"
            f"</div>"
            f"<div style='margin-top: 10px; text-align: right; font-size: 12px; color: #aaa;'>"
            f"  🤖 扫描于: {scan_time}"
            f"</div>"
        )
        
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": f"📢 Alpha线报: {title}",
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
    print(f"🔗 目标URL: {BASE_URL}")
    print(f"⏰ 监控窗口: {TIME_WINDOW_MINUTES} 分钟")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        print("📡 正在发起 HTTP 请求...")
        resp = requests.get(BASE_URL, headers=headers, timeout=15)
        
        print(f"✅ [请求结果] 状态码: {resp.status_code} | 页面大小: {len(resp.text)} 字符")
        
        if resp.status_code != 200:
            print(f"❌ 访问失败，停止运行。")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        messages = soup.find_all('div', class_='tgme_widget_message')
        
        if not messages:
            print("⚠️ [警告] 未找到消息元素。")
            return

        print(f"🔍 [解析] 页面共找到 {len(messages)} 条消息卡片。")

        # 获取当前 UTC 时间
        now_utc = datetime.datetime.now(timezone.utc)
        print(f"🕒 [基准时间] 当前 UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n--- 开始倒序检查 (从最新消息开始) ---")
        
        processed_count = 0
        pushed_count = 0

        for i, msg in enumerate(reversed(messages)):
            processed_count += 1
            print(f"\n🔹 [检查第 {i+1} 条消息]")
            
            try:
                # 1. 获取发布时间
                time_tag = msg.find('time')
                if not time_tag: 
                    print("   ⚠️ 无法找到 <time> 标签，跳过。")
                    continue
                
                dt_str = time_tag.get('datetime')
                msg_dt_utc = datetime.datetime.fromisoformat(dt_str)
                
                # 计算时间差
                diff = now_utc - msg_dt_utc
                diff_minutes = diff.total_seconds() / 60
                
                # 转换显示时间 (UTC -> 北京时间)
                msg_dt_bj = msg_dt_utc.astimezone(SHA_TZ)
                post_time_str = msg_dt_bj.strftime('%H:%M:%S')
                
                print(f"   📅 发布时间: {post_time_str} (北京时间)")
                print(f"   ⏱️ 距今时间: {diff_minutes:.2f} 分钟")

                # 2. 判断是否在窗口内
                if 0 <= diff_minutes <= TIME_WINDOW_MINUTES:
                    print(f"   ✅ [状态] 符合时间窗口!")
                    
                    post_id = msg.get('data-post')
                    link = f"https://t.me/{post_id}"
                    
                    text_div = msg.find('div', class_='tgme_widget_message_text')
                    if text_div:
                        # === 关键修改 A: 提取纯文本标题 ===
                        # 使用 separator=' ' 保证换行处变成空格，strip=True 去除首尾空白
                        plain_title = text_div.get_text(separator=' ', strip=True)
                        print(f"   📝 [标题] \"{plain_title[:20]}...\"")
                        
                        # === 关键修改 B: 保留原始 HTML 用于正文 ===
                        # ❌ 删除了之前的 br.replace_with("\n")，因为那会导致 PushPlus 换行失效
                        # ✅ 直接使用 decode_contents() 获取带 <br> 的 HTML
                        html_content = text_div.decode_contents()
                        
                        # 发送推送
                        send_wechat(html_content, link, post_time_str, plain_title)
                        pushed_count += 1
                    else:
                        print("   ⚠️ [跳过] 消息为图片/贴纸，没有文字内容。")
                
                elif diff_minutes > TIME_WINDOW_MINUTES:
                    print(f"   ⛔ [停止] 消息时间 ({diff_minutes:.2f}m) 超过窗口阈值。")
                    break
                else:
                    print(f"   ❓ [异常] 时间差为负数。")

            except Exception as e:
                print(f"   ❌ [解析错误] {e}")
                continue
        
        print("\n" + "="*50)
        print(f"🏁 [扫描结束] 共检查 {processed_count} 条，实际推送 {pushed_count} 条。")

    except Exception as e:
        print(f"\n❌ [致命错误] 运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_tg_web()
