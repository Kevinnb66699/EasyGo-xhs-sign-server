#!/usr/bin/env python3
"""
独立的 stealth.min.js 下载脚本
用于在服务启动前预先下载反检测脚本
"""

import os
import sys

def download_stealth_js():
    """下载 stealth.min.js 文件"""
    # 注意：这里不导入 requests，避免 gevent 冲突
    import urllib.request
    
    stealth_js_path = "stealth.min.js"
    
    # 如果文件已存在
    if os.path.exists(stealth_js_path):
        file_size = os.path.getsize(stealth_js_path)
        print(f"✅ stealth.min.js 已存在 ({file_size} bytes)")
        
        # 询问是否重新下载
        response = input("是否重新下载？(y/N): ").strip().lower()
        if response != 'y':
            print("保持现有文件")
            return True
        
        print("删除现有文件...")
        os.remove(stealth_js_path)
    
    # 多个备用下载源
    cdn_urls = [
        ("jsDelivr CDN (主)", "https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js"),
        ("jsDelivr CDN (备)", "https://fastly.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js"),
        ("GitHub Raw", "https://raw.githubusercontent.com/requireCool/stealth.min.js/main/stealth.min.js"),
    ]
    
    print("\n" + "=" * 60)
    print(" stealth.min.js 下载工具")
    print("=" * 60)
    
    for idx, (name, url) in enumerate(cdn_urls):
        print(f"\n[{idx + 1}/{len(cdn_urls)}] 尝试从 {name} 下载...")
        print(f"URL: {url}")
        
        try:
            # 使用 urllib 下载（不依赖 requests）
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read().decode('utf-8')
            
            # 验证内容
            if len(content) < 100:
                print(f"⚠️  下载的文件太小: {len(content)} bytes")
                print("可能不是有效的脚本，尝试下一个源...")
                continue
            
            # 保存文件
            with open(stealth_js_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = len(content)
            file_size_kb = file_size / 1024
            
            print(f"✅ 下载成功!")
            print(f"   文件大小: {file_size} bytes ({file_size_kb:.1f} KB)")
            print(f"   保存位置: {os.path.abspath(stealth_js_path)}")
            
            # 显示文件前几行
            lines = content.split('\n')[:3]
            print(f"\n文件预览（前3行）:")
            for line in lines:
                preview = line[:80] + "..." if len(line) > 80 else line
                print(f"   {preview}")
            
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            if idx < len(cdn_urls) - 1:
                print("尝试下一个源...")
            continue
    
    # 所有源都失败
    print("\n" + "=" * 60)
    print("❌ 所有下载源都失败了")
    print("=" * 60)
    print("\n手动下载方法:")
    print("1. 访问: https://github.com/requireCool/stealth.min.js")
    print("2. 下载 stealth.min.js 文件")
    print(f"3. 将文件放到: {os.path.abspath('.')}")
    print("\n或使用 curl 命令:")
    print("  curl -o stealth.min.js https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js")
    
    return False

def main():
    """主函数"""
    print("=" * 60)
    print(" 小红书签名服务 - stealth.min.js 下载工具")
    print("=" * 60)
    print("\n此脚本会下载反检测脚本 stealth.min.js")
    print("这是签名服务正常工作的重要组件\n")
    
    try:
        success = download_stealth_js()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 准备完成！")
            print("=" * 60)
            print("\n现在可以启动签名服务:")
            print("  python server.py")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("⚠️  下载失败")
            print("=" * 60)
            print("\n请按照上述说明手动下载文件")
            print("下载完成后再运行:")
            print("  python server.py")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  下载被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
