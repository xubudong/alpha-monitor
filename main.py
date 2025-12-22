import requests
from bs4 import BeautifulSoup
import os
import datetime
from datetime import timezone

# ================= ⚙️ 配置区域 =================
# 1. PushPlus Token
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')

# 2. 目标频道 ID
CHANNEL_ID = 'alpha123cn' 

# 3. 监控时间窗口 (分钟)
TIME_WINDOW_MINUTES = 25
# ===============================================

BASE_URL = f"https://t.me/s/{CHANNEL_ID}"

def send_wechat(content, link, post_time):
    if not PUSHPLUS_TOKEN: 
        print("⚠️ [推送跳过] 未配置 Token")
        return
        
    try:
        # 简单提取标题
        clean_text = content.replace('<br>', ' ').strip()
        title = clean_text[:20] + "..." if len(clean_text) > 20 else clean_text
        
        print(f"📨 [推送中] 标题: {title}")
        
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
        resp = requests.post(url, json=data, timeout=5)
        print(f"✅ [推送完成] 接口响应: {resp.text}")
    except Exception as e:
        print(f"❌ [推送失败] 错误信息: {e}")

def check_tg_web():
    print("="*50)
    print(f"🚀 [任务启动] 扫描频道: {CHANNEL_ID}")
    print(f"🔗 目标URL: {BASE_URL}")
    print(f"⏰ 监控窗口: {TIME_WINDOW_MINUTES} 分钟 (即只推送 {TIME_WINDOW_MINUTES} 分钟内的新消息)")
    
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
        
        # 找到所有的消息容器
        messages = soup.find_all('div', class_='tgme_widget_message')
        
        if not messages:
            print("⚠️ [警告] 页面解析成功，但未找到 class='tgme_widget_message' 的元素。")
            print("   可能原因: 频道为空、频道被封禁、或 Telegram 网页结构变更。")
            return

        print(f"🔍 [解析] 页面共找到 {len(messages)} 条消息卡片。")

        # 获取当前 UTC 时间
        now_utc = datetime.datetime.now(timezone.utc)
        print(f"🕒 [基准时间] 当前 UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n--- 开始倒序检查 (从最新消息开始) ---")
        
        # 计数器
        processed_count = 0
        pushed_count = 0

        # 倒序遍历
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
                msg_dt = datetime.datetime.fromisoformat(dt_str)
                
                # 2. 计算时间差
                diff = now_utc - msg_dt
                diff_minutes = diff.total_seconds() / 60
                
                print(f"   📅 发布时间: {msg_dt.strftime('%H:%M:%S')}")
                print(f"   ⏱️ 距今时间: {diff_minutes:.2f} 分钟")

                # 3. 判断是否在窗口内
                if 0 <= diff_minutes <= TIME_WINDOW_MINUTES:
                    print(f"   ✅ [状态] 符合时间窗口! (阈值: {TIME_WINDOW_MINUTES}m)")
                    
                    # 提取 ID 和链接
                    post_id = msg.get('data-post')
                    link = f"https://t.me/{post_id}"
                    
                    # 提取文字
                    text_div = msg.find('div', class_='tgme_widget_message_text')
                    if text_div:
                        # 预览内容
                        raw_preview = text_div.get_text().replace('\n', ' ')[:30]
                        print(f"   📝 [内容] \"{raw_preview}...\"")
                        
                        # 处理换行
                        for br in text_div.find_all("br"):
                            br.replace_with("\n")
                        
                        html_content = text_div.decode_contents()
                        
                        # 发送推送
                        send_wechat(html_content, link, msg_dt.strftime('%H:%M:%S'))
                        pushed_count += 1
                    else:
                        print("   ⚠️ [跳过] 消息为图片/贴纸，没有文字内容。")
                
                elif diff_minutes > TIME_WINDOW_MINUTES:
                    print(f"   ⛔ [停止] 消息时间 ({diff_minutes:.2f}m) 超过窗口阈值，停止扫描后续旧消息。")
                    break
                else:
                    # 理论上不会出现负数，除非服务器时间有问题
                    print(f"   ❓ [异常] 时间差为负数 ({diff_minutes:.2f}m)，可能是时钟不同步。")

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
