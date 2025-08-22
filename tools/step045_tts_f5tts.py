"""
F5-TTS 语音合成模块
Official code for "F5-TTS: A Fairytaler that Fakes Fluent and Faithful Speech with Flow Matching"
GitHub: https://github.com/SWivid/F5-TTS
"""
import os
import sys
import subprocess
import importlib.util
from loguru import logger

# 延迟导入可能缺失的依赖
try:
    import numpy as np
    import torch
    import torchaudio
except ImportError as e:
    logger.warning(f"Some dependencies not available for F5-TTS: {e}")


def install_f5tts():
    """安装F5-TTS依赖"""
    try:
        # 检查是否已安装
        import f5_tts
        logger.info("F5-TTS already installed")
        return True
    except ImportError:
        logger.info("F5-TTS not found, please install it manually with: pip install f5-tts")
        return False


def load_f5tts_model(model_name="F5-TTS", device="auto"):
    """加载F5-TTS模型"""
    try:
        # 确保F5-TTS已安装
        if not install_f5tts():
            raise ImportError("Failed to install F5-TTS")
        
        # 导入F5-TTS相关模块 - 使用命令行接口更稳定
        import f5_tts
        
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"F5-TTS package loaded successfully on {device}")
        
        # 返回一个标志表示F5-TTS可用
        return True, device, None
    
    except Exception as e:
        logger.error(f"Failed to load F5-TTS model: {e}")
        return None, None, None


def tts(text, output_path, speaker_wav=None, model_name="F5-TTS", device='auto', target_language='中文'):
    """
    使用F5-TTS进行语音合成 - 使用命令行接口
    
    Args:
        text (str): 要合成的文本
        output_path (str): 输出音频文件路径
        speaker_wav (str): 参考音频文件路径（用于声音克隆）
        model_name (str): 模型名称
        device (str): 运行设备
        target_language (str): 目标语言
    
    Returns:
        bool: 合成是否成功
    """
    try:
        # 检查F5-TTS是否可用
        model_available, device, _ = load_f5tts_model(model_name, device)
        if not model_available:
            logger.error("Failed to load F5-TTS model")
            return False
        
        # 构建命令行参数
        cmd = ["f5-tts_infer-cli"]
        
        # 如果有参考音频，添加声音克隆参数
        if speaker_wav and os.path.exists(speaker_wav):
            cmd.extend(["--ref_audio", speaker_wav])
            # 添加参考文本（简单起见，使用固定文本）
            if target_language == '中文':
                ref_text = "这是一段参考音频。"
            else:
                ref_text = "This is a reference audio."
            cmd.extend(["--ref_text", ref_text])
        
        # 添加生成文本
        cmd.extend(["--gen_text", text])
        
        # 添加输出路径
        cmd.extend(["--output_dir", os.path.dirname(output_path)])
        
        # 设置输出文件名
        filename = os.path.basename(output_path)
        if filename.endswith('.wav'):
            filename = filename[:-4]  # 移除.wav扩展名
        cmd.extend(["--output_name", filename])
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        logger.info(f"Running F5-TTS command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # F5-TTS生成的文件可能在输出目录中，需要重命名
            generated_file = os.path.join(os.path.dirname(output_path), filename + ".wav")
            if os.path.exists(generated_file) and generated_file != output_path:
                # 重命名到目标路径
                import shutil
                shutil.move(generated_file, output_path)
            
            if os.path.exists(output_path):
                logger.info(f"F5-TTS synthesis successful: {output_path}")
                return True
            else:
                logger.error(f"F5-TTS generated file not found at expected location")
                return False
        else:
            logger.error(f"F5-TTS command failed: {result.stderr}")
            if result.stdout:
                logger.error(f"F5-TTS stdout: {result.stdout}")
            return False
        
    except subprocess.TimeoutExpired:
        logger.error("F5-TTS synthesis timed out")
        return False
    except FileNotFoundError:
        logger.error("f5-tts_infer-cli command not found. Please ensure F5-TTS is properly installed.")
        return False
    except Exception as e:
        logger.error(f"F5-TTS synthesis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_f5tts():
    """测试F5-TTS功能"""
    test_text = "这是一个F5-TTS语音合成测试。"
    output_path = "test_f5tts_output.wav"
    
    success = tts(
        text=test_text,
        output_path=output_path,
        target_language='中文'
    )
    
    if success and os.path.exists(output_path):
        logger.info(f"F5-TTS test successful! Output saved to {output_path}")
        # 清理测试文件
        try:
            os.remove(output_path)
        except:
            pass
        return True
    else:
        logger.error("F5-TTS test failed")
        return False


if __name__ == "__main__":
    # 运行测试
    test_f5tts()
