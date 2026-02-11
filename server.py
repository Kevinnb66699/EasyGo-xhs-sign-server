"""
小红书签名服务器
用于为 Vercel 部署的小红书发布 API 提供签名服务
基于官方 xhs 库的实现：https://github.com/ReaJason/xhs
"""

# 重要：gevent monkey patch 必须在所有导入之前执行
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from gevent import pywsgi
import os
import time
import logging
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局变量
playwright_instance = None
browser_context = None
context_page = None
global_a1 = ""  # 当前浏览器中的 a1 值

def download_stealth_js():
    """下载 stealth.min.js 到本地"""
    stealth_js_path = "stealth.min.js"
    
    # 如果文件已存在，直接返回
    if os.path.exists(stealth_js_path):
        logger.info(f"✅ stealth.min.js 已存在")
        return stealth_js_path
    
    # 多个备用下载源
    cdn_urls = [
        "https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js",
        "https://fastly.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js",
        "https://raw.githubusercontent.com/requireCool/stealth.min.js/main/stealth.min.js",
    ]
    
    for idx, url in enumerate(cdn_urls):
        try:
            logger.info(f"正在从源 {idx + 1}/{len(cdn_urls)} 下载 stealth.min.js...")
            logger.info(f"URL: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 验证下载内容
            if len(response.text) < 100:
                logger.warning(f"下载的文件太小，可能不是有效的脚本: {len(response.text)} bytes")
                continue
            
            with open(stealth_js_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"✅ stealth.min.js 下载成功 ({len(response.text)} bytes)")
            return stealth_js_path
            
        except Exception as e:
            logger.warning(f"从源 {idx + 1} 下载失败: {e}")
            if idx < len(cdn_urls) - 1:
                logger.info(f"尝试下一个下载源...")
            continue
    
    logger.error(f"❌ 所有下载源都失败了")
    logger.warning(f"💡 提示: 您可以手动下载 stealth.min.js 文件到当前目录")
    logger.warning(f"   下载地址: https://github.com/requireCool/stealth.min.js")
    return None


def init_browser():
    """
    初始化浏览器环境
    参考官方实现：https://github.com/ReaJason/xhs/blob/master/example/basic_usage.py
    
    注意：
    - 官方示例使用 headless=True（无头模式）
    - 如果一直失败可尝试设置成 False 让其打开浏览器
    - 适当添加 sleep 可查看浏览器状态
    """
    global playwright_instance, browser_context, context_page, global_a1
    
    try:
        # 1. 下载 stealth.js（反检测脚本）
        stealth_js_path = download_stealth_js()
        if not stealth_js_path:
            logger.warning("⚠️ stealth.js 下载失败，将在没有反检测脚本的情况下启动")
        
        # 2. 启动 Playwright
        logger.info("正在启动 playwright...")
        playwright_instance = sync_playwright().start()
        chromium = playwright_instance.chromium
        
        # 3. 启动浏览器（headless=True，官方推荐）
        # 如果一直失败可尝试设置成 False 让其打开浏览器
        logger.info("正在启动 chromium 浏览器（无头模式）...")
        browser = chromium.launch(headless=True)
        
        # 4. 创建浏览器上下文
        browser_context = browser.new_context()
        
        # 5. 加载反检测脚本（重要！）
        if stealth_js_path:
            browser_context.add_init_script(path=stealth_js_path)
            logger.info("✅ stealth.min.js 反检测脚本已加载")
        
        # 6. 创建页面
        context_page = browser_context.new_page()
        
        # 7. 访问小红书首页（必须先访问首页）
        logger.info("正在访问小红书首页...")
        context_page.goto("https://www.xiaohongshu.com")
        
        # 8. 这个地方设置完浏览器 cookie 之后，如果这儿不 sleep 一下签名获取就失败了
        # 如果经常失败请设置长一点试试（官方注释）
        logger.info("等待页面完全加载（1秒）...")
        time.sleep(1)
        
        # 9. 提取浏览器生成的 a1 cookie
        cookies = browser_context.cookies()
        for cookie in cookies:
            if cookie["name"] == "a1":
                global_a1 = cookie["value"]
                logger.info(f"✅ 浏览器已生成 a1: {global_a1[:20]}...")
                logger.info("💡 提示: 您可以将自己的 cookie 中的 a1 设置成一样，方可签名成功")
                break
        
        if not global_a1:
            logger.warning("⚠️ 未能获取到 a1 cookie，签名可能会失败")
        
        logger.info("✅ 浏览器初始化完成，等待签名请求")
        
    except Exception as e:
        logger.error(f"❌ 浏览器初始化失败: {e}", exc_info=True)
        raise

@app.before_request
def ensure_browser():
    """确保浏览器已初始化"""
    global context_page
    if context_page is None:
        logger.warning("浏览器未初始化，正在初始化...")
        init_browser()

@app.route('/', methods=['GET'])
def index():
    """首页 - API 信息"""
    return jsonify({
        'service': 'XHS Signature Server',
        'description': '小红书 API 签名服务',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'health': {
                'path': '/health',
                'method': 'GET',
                'description': '健康检查'
            },
            'sign': {
                'path': '/sign',
                'method': 'POST',
                'description': '生成签名',
                'parameters': {
                    'uri': 'API 路径',
                    'data': '请求数据（可选）',
                    'a1': 'Cookie a1 字段',
                    'web_session': 'Cookie web_session 字段'
                }
            }
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    browser_ready = context_page is not None
    
    return jsonify({
        'status': 'healthy' if browser_ready else 'initializing',
        'browser_ready': browser_ready,
        'a1': global_a1[:20] + "..." if global_a1 else "",
        'timestamp': time.time()
    }), 200 if browser_ready else 503

@app.route('/a1', methods=['GET'])
def get_a1():
    """获取当前浏览器的 a1 值"""
    return jsonify({'a1': global_a1})

def generate_sign(uri, data, a1, web_session):
    """
    生成签名（参考官方 basic_usage.py 实现）
    参考：https://github.com/ReaJason/xhs/blob/master/example/basic_usage.py
    
    支持两种模式：
    1. 共享 a1 模式：所有请求使用相同的 a1（官方推荐）
    2. 用户 Cookie 模式：每个用户使用自己的 cookie（更灵活）
    
    关键改进（基于官方示例）：
    - 添加重试机制（最多10次）
    - 确保 cookie 设置后有足够的等待时间
    - 捕获 window._webmsxyw is not a function 等常见错误
    """
    global browser_context, context_page, global_a1
    
    # 重试最多 10 次（参考官方实现）
    for attempt in range(10):
        try:
            # 如果提供了用户的 cookie，更新浏览器 cookie
            cookies_updated = False
            
            if a1 and a1 != global_a1:
                logger.info(f"[尝试 {attempt + 1}/10] 检测到用户 a1，更新 cookie")
                
                # 准备要更新的 cookies
                cookies_to_add = [
                    {'name': 'a1', 'value': a1, 'domain': ".xiaohongshu.com", 'path': "/"}
                ]
                
                # 如果提供了 web_session，也一起更新
                if web_session:
                    cookies_to_add.append({
                        'name': 'web_session', 
                        'value': web_session, 
                        'domain': ".xiaohongshu.com", 
                        'path': "/"
                    })
                    logger.info(f"[尝试 {attempt + 1}/10] 同时更新 web_session")
                
                # 更新 cookies
                browser_context.add_cookies(cookies_to_add)
                context_page.reload()
                
                # 关键：这儿不 sleep 一下签名获取就失败了（官方注释）
                # 如果经常失败请设置长一点试试
                time.sleep(1)
                
                global_a1 = a1
                cookies_updated = True
                logger.info(f"[尝试 {attempt + 1}/10] ✅ 用户 cookie 已更新")
            
            # 执行签名函数
            logger.info(f"[尝试 {attempt + 1}/10] 执行签名 - URI: {uri}")
            encrypt_params = context_page.evaluate(
                "([url, data]) => window._webmsxyw(url, data)",
                [uri, data]
            )
            
            # 返回结果
            result = {
                "x-s": encrypt_params["X-s"],
                "x-t": str(encrypt_params["X-t"])
            }
            
            logger.info(f"[尝试 {attempt + 1}/10] ✅ 签名生成成功 - x-t: {result['x-t']}")
            return result
            
        except Exception as e:
            # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误
            # 因此加一个失败重试（官方注释）
            error_msg = str(e)
            logger.warning(f"[尝试 {attempt + 1}/10] ❌ 签名生成失败: {error_msg}")
            
            # 如果是最后一次尝试，抛出异常
            if attempt == 9:
                logger.error(f"重试了 10 次还是无法签名成功")
                raise Exception(f"签名失败（重试10次）: {error_msg}")
            
            # 否则继续重试
            logger.info(f"等待 0.5 秒后重试...")
            time.sleep(0.5)
    
    # 理论上不会到这里
    raise Exception("重试了这么多次还是无法签名成功，寄寄寄")


@app.route('/sign', methods=['POST'])
def sign():
    """
    生成小红书 API 签名
    参考：https://github.com/ReaJason/xhs/blob/master/example/basic_usage.py
    
    请求体：
    {
        "uri": "/api/sns/web/v2/note",
        "data": {...},  // 可选，请求数据
        "a1": "cookie_a1_value",  // 必需，来自 cookie
        "web_session": "cookie_web_session_value"  // 可选
    }
    
    返回：
    {
        "x-s": "签名值",
        "x-t": "时间戳字符串"
    }
    
    注意：即便做了重试，还是有可能会遇到签名失败的情况，客户端应该重试
    """
    try:
        # 获取请求数据
        json_data = request.get_json()
        if not json_data:
            logger.error("请求体为空")
            return jsonify({
                'error': 'Request body is required',
                'success': False
            }), 400
        
        uri = json_data.get('uri', '')
        data = json_data.get('data')
        a1 = json_data.get('a1', '')
        web_session = json_data.get('web_session', '')
        
        # 验证必需参数
        if not uri:
            logger.error("缺少 uri 参数")
            return jsonify({
                'error': 'uri parameter is required',
                'success': False
            }), 400
        
        # 记录请求信息（隐藏敏感信息）
        logger.info(f"收到签名请求:")
        logger.info(f"  - URI: {uri}")
        logger.info(f"  - 有 data: {bool(data)}")
        logger.info(f"  - 有 a1: {bool(a1)} ({a1[:10]}...)" if a1 else "  - 有 a1: False")
        logger.info(f"  - 有 web_session: {bool(web_session)}")
        
        # 生成签名（带重试机制）
        result = generate_sign(uri, data, a1, web_session)
        
        logger.info(f"✅ 签名请求处理成功")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 签名请求处理失败: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'success': False,
            'hint': '即便做了重试，还是有可能会遇到签名失败的情况，请重试'
        }), 500

@app.errorhandler(404)
def not_found(e):
    """404 错误处理"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/', '/health', '/sign']
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """500 错误处理"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500

if __name__ == '__main__':
    # 获取端口（Railway/Render 会自动设置 PORT 环境变量）
    port = int(os.environ.get('PORT', 5005))
    
    logger.info("=" * 60)
    logger.info("小红书签名服务器")
    logger.info("=" * 60)
    logger.info(f"启动端口: {port}")
    logger.info(f"环境变量 PORT: {os.environ.get('PORT', '未设置')}")
    
    # 初始化浏览器
    try:
        init_browser()
    except Exception as e:
        logger.error(f"初始化失败，服务器将以降级模式启动: {e}")
    
    # 启动服务器
    # 使用 gevent 提高并发性能
    logger.info(f"正在启动 HTTP 服务器...")
    server = pywsgi.WSGIServer(('0.0.0.0', port), app, log=logger)
    
    logger.info("=" * 60)
    logger.info(f"✅ 服务器启动成功！")
    logger.info(f"监听地址: http://0.0.0.0:{port}")
    logger.info(f"健康检查: http://0.0.0.0:{port}/health")
    logger.info(f"签名接口: http://0.0.0.0:{port}/sign (POST)")
    logger.info("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
        if playwright_instance:
            playwright_instance.stop()
        logger.info("服务器已关闭")
