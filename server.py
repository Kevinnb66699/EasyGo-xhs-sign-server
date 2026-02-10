"""
小红书签名服务器
用于为 Vercel 部署的小红书发布 API 提供签名服务
基于官方 xhs 库的实现：https://github.com/ReaJason/xhs
"""

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from gevent import monkey, pywsgi
import os
import time
import logging
import requests

# 重要：gevent monkey patch，提高并发性能
monkey.patch_all()

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
    
    try:
        logger.info("正在下载 stealth.min.js...")
        stealth_js_url = "https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js"
        response = requests.get(stealth_js_url, timeout=30)
        response.raise_for_status()
        
        with open(stealth_js_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logger.info("✅ stealth.min.js 下载成功")
        return stealth_js_path
    except Exception as e:
        logger.error(f"❌ stealth.min.js 下载失败: {e}")
        return None


def init_browser():
    """
    初始化浏览器环境
    基于官方实现：https://github.com/ReaJason/xhs/blob/master/xhs-api/app.py
    """
    global playwright_instance, browser_context, context_page, global_a1
    
    try:
        # 1. 下载 stealth.js
        stealth_js_path = download_stealth_js()
        
        # 2. 启动 Playwright
        logger.info("正在启动 playwright...")
        playwright_instance = sync_playwright().start()
        chromium = playwright_instance.chromium
        
        # 3. 启动浏览器
        browser = chromium.launch(headless=True)
        
        # 4. 创建浏览器上下文
        browser_context = browser.new_context()
        
        # 5. 加载反检测脚本
        if stealth_js_path:
            browser_context.add_init_script(path=stealth_js_path)
            logger.info("✅ stealth.js 已加载")
        
        # 6. 创建页面
        context_page = browser_context.new_page()
        
        # 7. 访问小红书首页（官方方式）
        logger.info("正在跳转至小红书首页...")
        context_page.goto("https://www.xiaohongshu.com")
        
        # 8. 等待5秒（官方推荐）
        logger.info("等待页面加载...")
        time.sleep(5)
        
        # 9. 刷新页面一次（官方推荐）
        logger.info("刷新页面...")
        context_page.reload()
        time.sleep(1)
        
        # 10. 提取 a1 cookie
        cookies = browser_context.cookies()
        for cookie in cookies:
            if cookie["name"] == "a1":
                global_a1 = cookie["value"]
                logger.info(f"✅ 当前浏览器中 a1 值为: {global_a1[:20]}...")
                logger.info("提示: 请将您的 cookie 中的 a1 也设置成一样，方可签名成功")
                break
        
        logger.info("✅ 跳转小红书首页成功，等待调用")
        
    except Exception as e:
        logger.error(f"❌ 浏览器初始化失败: {e}")
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
    生成签名（官方实现 + 增强的用户 Cookie 支持）
    参考：https://github.com/ReaJason/xhs/blob/master/xhs-api/app.py
    
    支持两种模式：
    1. 共享 a1 模式：所有请求使用相同的 a1（官方推荐）
    2. 用户 Cookie 模式：每个用户使用自己的 cookie（更灵活）
    """
    global browser_context, context_page, global_a1
    
    try:
        # 如果提供了用户的 cookie，更新浏览器 cookie
        cookies_updated = False
        
        if a1 and a1 != global_a1:
            logger.info(f"检测到用户 a1，更新 cookie")
            
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
                logger.info(f"同时更新 web_session")
            
            # 更新 cookies
            browser_context.add_cookies(cookies_to_add)
            context_page.reload()
            time.sleep(1)
            
            global_a1 = a1
            cookies_updated = True
            logger.info(f"✅ 用户 cookie 已更新: a1={a1[:20]}..., web_session={bool(web_session)}")
        
        # 执行签名函数
        logger.info(f"执行签名 - URI: {uri}, 使用{'用户' if cookies_updated else '服务器'}cookie")
        encrypt_params = context_page.evaluate(
            "([url, data]) => window._webmsxyw(url, data)",
            [uri, data]
        )
        
        # 返回结果
        result = {
            "x-s": encrypt_params["X-s"],
            "x-t": str(encrypt_params["X-t"])
        }
        
        logger.info(f"✅ 签名生成成功 - x-t: {result['x-t']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ 签名生成失败: {e}", exc_info=True)
        raise


@app.route('/sign', methods=['POST'])
def sign():
    """
    生成小红书 API 签名
    
    请求体：
    {
        "uri": "/api/sns/web/v2/note",
        "data": {...},  // 可选
        "a1": "cookie_a1_value",
        "web_session": "cookie_web_session_value"
    }
    
    返回：
    {
        "x-s": "签名值",
        "x-t": "时间戳"
    }
    """
    try:
        # 获取请求数据
        json_data = request.get_json()
        if not json_data:
            return jsonify({
                'error': 'Request body is required',
                'success': False
            }), 400
        
        uri = json_data.get('uri', '')
        data = json_data.get('data')
        a1 = json_data.get('a1', '')
        web_session = json_data.get('web_session', '')
        
        if not uri:
            return jsonify({
                'error': 'uri parameter is required',
                'success': False
            }), 400
        
        # 生成签名
        result = generate_sign(uri, data, a1, web_session)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"签名请求处理失败: {e}")
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'success': False
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
