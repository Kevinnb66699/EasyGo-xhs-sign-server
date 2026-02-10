"""
小红书签名服务器
用于为 Vercel 部署的小红书发布 API 提供签名服务
"""

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from gevent import pywsgi
import os
import time
import logging

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
page_ready = False  # 标记页面是否已加载小红书网站
last_page_load_time = 0  # 上次加载时间

def init_browser():
    """初始化浏览器环境"""
    global playwright_instance, browser_context, context_page, page_ready
    
    try:
        logger.info("正在初始化 Playwright 浏览器...")
        playwright_instance = sync_playwright().start()
        chromium = playwright_instance.chromium
        
        # 启动浏览器 - 添加更多性能优化参数
        browser = chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',  # 禁用同源策略
                '--disable-features=IsolateOrigins,site-per-process',  # 禁用站点隔离
                '--blink-settings=imagesEnabled=false',  # 禁用图片加载，加快速度
            ]
        )
        
        # 创建浏览器上下文
        browser_context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 加载反检测脚本
        try:
            import requests
            stealth_js_url = "https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js"
            logger.info(f"正在下载 stealth.min.js...")
            stealth_js = requests.get(stealth_js_url, timeout=10).text
            browser_context.add_init_script(stealth_js)
            logger.info("✅ Stealth.js 加载成功")
        except Exception as e:
            logger.warning(f"⚠️ Stealth.js 加载失败: {e}，继续运行...")
        
        # 创建页面
        context_page = browser_context.new_page()
        
        # 启动时预加载小红书网站
        try:
            logger.info("预加载小红书网站...")
            context_page.goto(
                "https://www.xiaohongshu.com", 
                timeout=30000,
                wait_until="domcontentloaded"
            )
            context_page.wait_for_function(
                "typeof window._webmsxyw === 'function'",
                timeout=5000
            )
            page_ready = True
            logger.info("✅ 小红书网站预加载成功")
        except Exception as e:
            logger.warning(f"⚠️ 预加载失败: {e}，将在首次请求时加载")
            page_ready = False
        
        logger.info("✅ 浏览器初始化完成")
        
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
    global page_ready, last_page_load_time
    browser_ready = context_page is not None
    
    return jsonify({
        'status': 'healthy' if (browser_ready and page_ready) else 'initializing',
        'browser_ready': browser_ready,
        'page_ready': page_ready,
        'last_page_load': last_page_load_time,
        'timestamp': time.time()
    }), 200 if (browser_ready and page_ready) else 503

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
    global browser_context, context_page, page_ready, last_page_load_time
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            logger.error("请求体为空")
            return jsonify({
                'error': 'Request body is required',
                'success': False
            }), 400
        
        uri = data.get('uri', '')
        request_data = data.get('data')
        a1 = data.get('a1', '')
        web_session = data.get('web_session', '')
        
        if not uri:
            logger.error("缺少 uri 参数")
            return jsonify({
                'error': 'uri parameter is required',
                'success': False
            }), 400
        
        logger.info(f"收到签名请求 - URI: {uri}, 数据长度: {len(str(request_data)) if request_data else 0}")
        
        # 检查页面是否需要刷新 (每5分钟刷新一次或页面未就绪)
        current_time = time.time()
        needs_refresh = (not page_ready) or (current_time - last_page_load_time > 300)
        
        if needs_refresh:
            # 访问小红书网站 - 使用重试机制
            max_retries = 3
            retry_delay = 2
            page_loaded = False
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"{'刷新' if page_ready else '加载'}小红书网站 (第 {attempt + 1}/{max_retries} 次)")
                    # 增加超时时间到 30 秒，并添加等待策略
                    context_page.goto(
                        "https://www.xiaohongshu.com", 
                        timeout=30000,  # 30秒超时
                        wait_until="domcontentloaded"  # 等待 DOM 加载完成即可
                    )
                    # 等待页面加载关键脚本
                    context_page.wait_for_function(
                        "typeof window._webmsxyw === 'function'",
                        timeout=5000
                    )
                    logger.info("✅ 小红书网站访问成功")
                    page_loaded = True
                    page_ready = True
                    last_page_load_time = current_time
                    break
                except Exception as e:
                    logger.warning(f"第 {attempt + 1} 次访问失败: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        logger.error(f"访问小红书网站失败，已重试 {max_retries} 次")
                        page_ready = False
                        return jsonify({
                            'error': f'Failed to access xiaohongshu.com after {max_retries} retries: {str(e)}',
                            'success': False,
                            'hint': 'Network issue or blocked by anti-crawler. Please try again later.'
                        }), 500
            
            if not page_loaded:
                page_ready = False
                return jsonify({
                    'error': 'Failed to load xiaohongshu.com page',
                    'success': False
                }), 500
        else:
            logger.info("使用已加载的页面（缓存）")
        
        # 设置 Cookie（如果提供）
        if a1 or web_session:
            cookie_list = browser_context.cookies()
            web_session_cookie = list(filter(lambda cookie: cookie["name"] == "web_session", cookie_list))
            
            if not web_session_cookie and (a1 or web_session):
                cookies_to_add = []
                if a1:
                    cookies_to_add.append({
                        'name': 'a1',
                        'value': a1,
                        'domain': ".xiaohongshu.com",
                        'path': "/"
                    })
                if web_session:
                    cookies_to_add.append({
                        'name': 'web_session',
                        'value': web_session,
                        'domain': ".xiaohongshu.com",
                        'path': "/"
                    })
                
                browser_context.add_cookies(cookies_to_add)
                logger.info(f"已设置 Cookie: a1={bool(a1)}, web_session={bool(web_session)}")
                time.sleep(0.5)
        
        # 执行签名算法 - 如果失败，尝试刷新页面后重试
        encrypt_params = None
        for retry in range(2):  # 最多尝试2次
            try:
                encrypt_params = context_page.evaluate(
                    "([url, data]) => window._webmsxyw(url, data)",
                    [uri, request_data]
                )
                break  # 成功则跳出循环
            except Exception as e:
                logger.error(f"执行签名算法失败 (尝试 {retry + 1}/2): {e}")
                if retry == 0:
                    # 第一次失败，尝试刷新页面
                    logger.info("正在刷新页面后重试...")
                    try:
                        context_page.goto(
                            "https://www.xiaohongshu.com", 
                            timeout=30000,
                            wait_until="domcontentloaded"
                        )
                        context_page.wait_for_function(
                            "typeof window._webmsxyw === 'function'",
                            timeout=5000
                        )
                        page_ready = True
                        last_page_load_time = time.time()
                        logger.info("页面刷新成功，继续重试签名")
                    except Exception as refresh_error:
                        logger.error(f"页面刷新失败: {refresh_error}")
                        page_ready = False
                        return jsonify({
                            'error': f'Failed to refresh page: {str(refresh_error)}',
                            'success': False
                        }), 500
                else:
                    # 第二次失败，返回错误
                    page_ready = False
                    return jsonify({
                        'error': f'Failed to execute signature algorithm: {str(e)}',
                        'success': False,
                        'hint': 'Signature function not available. Please try again later.'
                    }), 500
        
        # 提取签名结果
        if not encrypt_params:
            logger.error("签名算法返回空结果")
            return jsonify({
                'error': 'Signature algorithm returned null',
                'success': False
            }), 500
        
        result = {
            "x-s": encrypt_params.get("X-s", ""),
            "x-t": str(encrypt_params.get("X-t", ""))
        }
        
        if not result["x-s"] or not result["x-t"]:
            logger.error(f"签名结果不完整: {result}")
            return jsonify({
                'error': 'Incomplete signature result',
                'success': False,
                'result': result
            }), 500
        
        logger.info(f"✅ 签名生成成功 - x-t: {result['x-t']}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 签名生成失败: {str(e)}", exc_info=True)
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
