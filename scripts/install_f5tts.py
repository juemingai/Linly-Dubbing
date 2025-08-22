#!/usr/bin/env python3
"""
F5-TTS 安装脚本
用于安装F5-TTS及其依赖项
"""
import os
import sys
import subprocess
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        logger.error("F5-TTS需要Python 3.8或更高版本")
        return False
    logger.info(f"Python版本: {sys.version}")
    return True

def check_torch():
    """检查PyTorch安装"""
    try:
        import torch
        logger.info(f"PyTorch版本: {torch.__version__}")
        if torch.cuda.is_available():
            logger.info(f"CUDA版本: {torch.version.cuda}")
            logger.info(f"可用GPU: {torch.cuda.device_count()}")
        else:
            logger.info("未检测到CUDA支持，将使用CPU")
        return True
    except ImportError:
        logger.warning("未检测到PyTorch，将在安装F5-TTS时自动安装")
        return False

def install_f5tts():
    """安装F5-TTS"""
    try:
        logger.info("开始安装F5-TTS...")
        
        # 先升级pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装F5-TTS
        subprocess.check_call([sys.executable, "-m", "pip", "install", "f5-tts"])
        
        logger.info("F5-TTS安装成功!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"安装F5-TTS失败: {e}")
        return False

def test_installation():
    """测试安装"""
    try:
        logger.info("测试F5-TTS安装...")
        
        # 导入F5-TTS
        import f5_tts
        logger.info(f"F5-TTS版本: {f5_tts.__version__ if hasattr(f5_tts, '__version__') else '未知'}")
        
        # 测试基本功能
        from f5_tts.api import F5TTS
        logger.info("F5-TTS API导入成功")
        
        logger.info("F5-TTS安装验证成功!")
        return True
        
    except ImportError as e:
        logger.error(f"F5-TTS安装验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始F5-TTS安装程序...")
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查PyTorch
    check_torch()
    
    # 安装F5-TTS
    if not install_f5tts():
        logger.error("F5-TTS安装失败")
        sys.exit(1)
    
    # 测试安装
    if not test_installation():
        logger.error("F5-TTS安装验证失败")
        sys.exit(1)
    
    logger.info("F5-TTS安装完成!")
    logger.info("现在您可以在Linly-Dubbing中使用F5-TTS进行语音合成了")

if __name__ == "__main__":
    main()
