"""
小红书签名服务测试脚本
用于测试签名服务是否正常工作
"""

import requests
import json
import time
import sys

# 配置
SIGN_SERVER_URL = "http://localhost:5005"  # 本地测试地址
# SIGN_SERVER_URL = "https://your-deployed-server.com"  # 生产环境地址

# 测试用的 Cookie（请替换为你自己的）
TEST_A1 = ""  # 从浏览器获取
TEST_WEB_SESSION = ""  # 从浏览器获取（可选）

def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def test_health():
    """测试健康检查接口"""
    print_section("测试 1: 健康检查")
    
    try:
        response = requests.get(f"{SIGN_SERVER_URL}/health", timeout=10)
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('browser_ready'):
                print("✅ 浏览器已就绪")
                return True
            else:
                print("⚠️  浏览器未就绪")
                return False
        else:
            print(f"❌ 服务未就绪: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_get_a1():
    """测试获取服务器 a1"""
    print_section("测试 2: 获取服务器 a1")
    
    try:
        response = requests.get(f"{SIGN_SERVER_URL}/a1", timeout=10)
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        data = response.json()
        a1 = data.get('a1', '')
        if a1:
            print(f"✅ 服务器 a1: {a1[:20]}...")
            return a1
        else:
            print("⚠️  服务器 a1 为空")
            return None
            
    except Exception as e:
        print(f"❌ 获取 a1 失败: {e}")
        return None

def test_sign_with_server_a1(server_a1):
    """使用服务器 a1 测试签名"""
    print_section("测试 3: 使用服务器 a1 签名")
    
    try:
        payload = {
            "uri": "/api/sns/web/v1/note",
            "data": None,
            "a1": server_a1,
            "web_session": ""
        }
        
        print(f"📤 请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        start_time = time.time()
        response = requests.post(
            f"{SIGN_SERVER_URL}/sign",
            json=payload,
            timeout=30
        )
        elapsed_time = time.time() - start_time
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
        
        if response.status_code == 200:
            signs = response.json()
            print(f"✅ 签名结果:")
            print(f"   x-s: {signs.get('x-s', '')[:50]}...")
            print(f"   x-t: {signs.get('x-t', '')}")
            return True
        else:
            print(f"❌ 签名失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 签名请求失败: {e}")
        return False

def test_sign_with_user_cookie():
    """使用用户 Cookie 测试签名"""
    print_section("测试 4: 使用用户 Cookie 签名")
    
    if not TEST_A1:
        print("⚠️  跳过：未配置 TEST_A1")
        print("💡 提示：请在脚本顶部配置你的 Cookie")
        return None
    
    try:
        payload = {
            "uri": "/api/sns/web/v1/note",
            "data": None,
            "a1": TEST_A1,
            "web_session": TEST_WEB_SESSION
        }
        
        print(f"📤 请求参数:")
        print(f"   uri: {payload['uri']}")
        print(f"   a1: {TEST_A1[:20]}...")
        print(f"   web_session: {'已提供' if TEST_WEB_SESSION else '未提供'}")
        
        start_time = time.time()
        response = requests.post(
            f"{SIGN_SERVER_URL}/sign",
            json=payload,
            timeout=30
        )
        elapsed_time = time.time() - start_time
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
        
        if response.status_code == 200:
            signs = response.json()
            print(f"✅ 签名结果:")
            print(f"   x-s: {signs.get('x-s', '')[:50]}...")
            print(f"   x-t: {signs.get('x-t', '')}")
            return True
        else:
            print(f"❌ 签名失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 签名请求失败: {e}")
        return False

def test_sign_retry():
    """测试签名重试机制"""
    print_section("测试 5: 签名重试机制")
    
    # 测试多次请求，验证重试和稳定性
    success_count = 0
    total_tests = 3
    
    server_a1 = test_get_a1()
    if not server_a1:
        print("❌ 无法获取服务器 a1，跳过测试")
        return False
    
    for i in range(total_tests):
        print(f"\n第 {i + 1}/{total_tests} 次测试...")
        try:
            payload = {
                "uri": "/api/sns/web/v1/note",
                "data": None,
                "a1": server_a1,
                "web_session": ""
            }
            
            response = requests.post(
                f"{SIGN_SERVER_URL}/sign",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                signs = response.json()
                if 'x-s' in signs and 'x-t' in signs:
                    print(f"  ✅ 成功 - x-t: {signs['x-t']}")
                    success_count += 1
                else:
                    print(f"  ❌ 失败 - 返回格式错误")
            else:
                print(f"  ❌ 失败 - 状态码: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ 失败 - 异常: {e}")
        
        # 间隔一下
        if i < total_tests - 1:
            time.sleep(1)
    
    print(f"\n📊 统计: {success_count}/{total_tests} 次成功")
    print(f"📊 成功率: {success_count/total_tests*100:.1f}%")
    
    return success_count >= total_tests * 0.8  # 80% 成功率

def main():
    """主测试流程"""
    print("=" * 60)
    print(" 小红书签名服务测试")
    print("=" * 60)
    print(f"签名服务地址: {SIGN_SERVER_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 测试 1: 健康检查
    results.append(("健康检查", test_health()))
    
    if not results[0][1]:
        print("\n❌ 签名服务未运行或未就绪，请先启动服务")
        print("\n启动命令:")
        print("  cd EasyGo-xhs-sign-server")
        print("  python server.py")
        return
    
    # 测试 2: 获取 a1
    server_a1 = test_get_a1()
    results.append(("获取 a1", server_a1 is not None))
    
    # 测试 3: 使用服务器 a1 签名
    if server_a1:
        results.append(("服务器 a1 签名", test_sign_with_server_a1(server_a1)))
    
    # 测试 4: 使用用户 Cookie 签名
    user_result = test_sign_with_user_cookie()
    if user_result is not None:
        results.append(("用户 Cookie 签名", user_result))
    
    # 测试 5: 重试机制
    results.append(("重试机制", test_sign_retry()))
    
    # 汇总结果
    print_section("测试结果汇总")
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}  {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！签名服务运行正常。")
    elif passed >= total * 0.8:
        print("\n✅ 大部分测试通过，签名服务基本正常。")
    else:
        print("\n⚠️  多个测试失败，请检查签名服务配置。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
