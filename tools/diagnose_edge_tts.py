#!/usr/bin/env python3
"""
Edge-TTS 网络连接诊断工具
用于诊断和解决Edge-TTS连接问题
"""

import subprocess
import requests
import time
import os
from loguru import logger

def test_network_connectivity():
    """测试网络连接"""
    logger.info("正在测试网络连接...")
    
    # 测试基本网络连接
    try:
        response = requests.get("https://www.microsoft.com", timeout=10)
        if response.status_code == 200:
            logger.info("✓ 基本网络连接正常")
        else:
            logger.warning(f"⚠ 网络连接异常，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"✗ 网络连接失败: {e}")
        return False
    
    # 测试Edge-TTS服务连接
    try:
        response = requests.get("https://speech.platform.bing.com", timeout=10)
        logger.info(f"✓ Edge-TTS服务连接测试完成，状态码: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠ Edge-TTS服务连接可能有问题: {e}")
    
    return True

def test_edge_tts_command():
    """测试edge-tts命令"""
    logger.info("正在测试edge-tts命令...")
    
    try:
        # 测试edge-tts是否安装
        result = subprocess.run(['edge-tts', '--help'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✓ edge-tts命令可用")
        else:
            logger.error("✗ edge-tts命令不可用")
            return False
    except FileNotFoundError:
        logger.error("✗ edge-tts未安装，请运行: pip install edge-tts")
        return False
    except Exception as e:
        logger.error(f"✗ edge-tts命令测试失败: {e}")
        return False
    
    # 测试简单的TTS生成
    test_text = "测试"
    test_output = "/tmp/test_edge_tts.mp3"
    
    try:
        logger.info("正在测试TTS生成...")
        result = subprocess.run([
            'edge-tts', 
            '--text', test_text,
            '--write-media', test_output,
            '--voice', 'zh-CN-XiaoxiaoNeural'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(test_output):
            logger.info("✓ TTS生成测试成功")
            # 清理测试文件
            os.remove(test_output)
            return True
        else:
            logger.error(f"✗ TTS生成测试失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("✗ TTS生成超时")
        return False
    except Exception as e:
        logger.error(f"✗ TTS生成测试出错: {e}")
        return False

def check_system_proxy():
    """检查系统代理设置"""
    logger.info("正在检查系统代理设置...")
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    proxy_found = False
    
    for var in proxy_vars:
        if var in os.environ:
            logger.info(f"✓ 发现代理设置: {var}={os.environ[var]}")
            proxy_found = True
    
    if not proxy_found:
        logger.info("✓ 未发现系统代理设置")
    
    return proxy_found

def suggest_solutions():
    """提供解决方案建议"""
    logger.info("\n" + "="*50)
    logger.info("解决方案建议:")
    logger.info("="*50)
    
    logger.info("1. 网络连接问题:")
    logger.info("   - 检查网络连接是否正常")
    logger.info("   - 如果使用代理，确保代理设置正确")
    logger.info("   - 尝试切换到其他网络环境")
    
    logger.info("\n2. Edge-TTS服务问题:")
    logger.info("   - 微软服务可能暂时不可用，稍后重试")
    logger.info("   - 检查防火墙是否阻止了连接")
    logger.info("   - 考虑使用其他TTS方法 (如 xtts, cosyvoice)")
    
    logger.info("\n3. 替代TTS方法:")
    logger.info("   - 使用 method='xtts' (需要GPU)")
    logger.info("   - 使用 method='cosyvoice' (需要GPU)")
    logger.info("   - 使用本地TTS引擎")
    
    logger.info("\n4. 临时解决方案:")
    logger.info("   - 代码已更新，TTS失败时会生成静音文件")
    logger.info("   - 程序可以继续运行而不会崩溃")

def main():
    """主函数"""
    logger.info("Edge-TTS 诊断工具启动")
    logger.info("="*50)
    
    # 检查网络连接
    network_ok = test_network_connectivity()
    
    # 检查系统代理
    proxy_found = check_system_proxy()
    
    # 测试edge-tts命令
    if network_ok:
        command_ok = test_edge_tts_command()
    else:
        logger.warning("跳过edge-tts命令测试（网络连接问题）")
        command_ok = False
    
    # 提供解决方案
    suggest_solutions()
    
    # 总结
    logger.info("\n" + "="*50)
    logger.info("诊断结果总结:")
    logger.info("="*50)
    logger.info(f"网络连接: {'✓ 正常' if network_ok else '✗ 异常'}")
    logger.info(f"Edge-TTS命令: {'✓ 可用' if command_ok else '✗ 不可用'}")
    
    if network_ok and command_ok:
        logger.info("✓ Edge-TTS应该可以正常使用")
    else:
        logger.info("⚠ 建议使用其他TTS方法或检查网络设置")

if __name__ == "__main__":
    main()
