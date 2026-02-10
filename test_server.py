"""
测试签名服务器
使用方法：
  python test_server.py http://localhost:5005
  python test_server.py https://your-app.railway.app
"""

import requests
import sys
import json

def test_health(base_url):
    """测试健康检查接口"""
    print("\n" + "=" * 60)
    print("测试 1: 健康检查")
    print("=" * 60)
    
    try:
        url = f"{base_url}/health"
        print(f"请求: GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and response.json().get('browser_ready'):
            print("✅ 健康检查通过")
            return True
        else:
            print("❌ 健康检查失败")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_sign(base_url):
    """测试签名生成接口"""
    print("\n" + "=" * 60)
    print("测试 2: 签名生成")
    print("=" * 60)
    
    try:
        url = f"{base_url}/sign"
        print(f"请求: POST {url}")
        
        payload = {
            "uri": "/api/sns/web/v2/note",
            "data": None,
            "a1": "test_a1_value",
            "web_session": "test_web_session_value"
        }
        
        print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        result = response.json()
        if response.status_code == 200 and result.get('x-s') and result.get('x-t'):
            print("✅ 签名生成成功")
            print(f"   x-s: {result['x-s'][:50]}...")
            print(f"   x-t: {result['x-t']}")
            return True
        else:
            print("❌ 签名生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_root(base_url):
    """测试根路径"""
    print("\n" + "=" * 60)
    print("测试 0: API 信息")
    print("=" * 60)
    
    try:
        url = f"{base_url}/"
        print(f"请求: GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ API 信息获取成功")
            return True
        else:
            print("❌ API 信息获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_server.py <服务器地址>")
        print("\n示例:")
        print("  python test_server.py http://localhost:5005")
        print("  python test_server.py https://your-app.railway.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    print("=" * 60)
    print("小红书签名服务器测试工具")
    print("=" * 60)
    print(f"服务器地址: {base_url}")
    
    # 运行测试
    results = []
    results.append(("API 信息", test_root(base_url)))
    results.append(("健康检查", test_health(base_url)))
    results.append(("签名生成", test_sign(base_url)))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("\n" + "=" * 60)
    print(f"总计: {passed_count}/{total_count} 个测试通过")
    print("=" * 60)
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！服务器运行正常。")
        print("\n下一步:")
        print(f"1. 在 Vercel 环境变量中设置:")
        print(f"   XHS_SIGN_SERVER_URL={base_url}")
        print(f"2. 重新部署 Vercel 项目")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查服务器日志。")
        sys.exit(1)

if __name__ == "__main__":
    main()
