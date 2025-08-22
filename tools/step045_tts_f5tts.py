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
import numpy as np
import torch
import torchaudio


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


def load_f5tts_model(model_name="F5TTS_v1_Base", device="auto"):
    """加载F5-TTS模型"""
    try:
        # 确保F5-TTS已安装
        if not install_f5tts():
            raise ImportError("Failed to install F5-TTS")
        
        # 导入F5-TTS相关模块
        from f5_tts.api import F5TTS
        from f5_tts.infer.utils_infer import load_vocoder
        
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading F5-TTS model: {model_name} on {device}")
        
        # 初始化F5-TTS模型
        f5tts = F5TTS(model_type=model_name, ckpt_file=None)
        
        # 加载vocoder
        vocoder = load_vocoder(vocoder_name="vocos", is_local=False, local_path="", device=device)
        
        logger.info("F5-TTS model loaded successfully")
        return f5tts, vocoder, device
    
    except Exception as e:
        logger.error(f"Failed to load F5-TTS model: {e}")
        return None, None, None


def tts(text, output_path, speaker_wav=None, model_name="F5TTS_v1_Base", device='auto', target_language='中文'):
    """
    使用F5-TTS进行语音合成
    
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
        # 加载模型
        f5tts, vocoder, device = load_f5tts_model(model_name, device)
        if f5tts is None:
            logger.error("Failed to load F5-TTS model")
            return False
        
        # 处理参考音频
        ref_audio = None
        ref_text = ""
        
        if speaker_wav and os.path.exists(speaker_wav):
            # 加载参考音频
            ref_audio, sample_rate = torchaudio.load(speaker_wav)
            # 确保采样率为24kHz
            if sample_rate != 24000:
                ref_audio = torchaudio.functional.resample(ref_audio, sample_rate, 24000)
            
            # 如果是立体声，转换为单声道
            if ref_audio.shape[0] > 1:
                ref_audio = ref_audio.mean(dim=0, keepdim=True)
            
            ref_audio = ref_audio.squeeze().numpy()
            
            # 参考文本 - 在实际应用中，这里应该是参考音频的转录文本
            # 由于没有ASR模块，我们使用一个通用的参考文本
            if target_language == '中文':
                ref_text = "这是一段参考音频的转录文本。"
            else:
                ref_text = "This is a reference audio transcription text."
        else:
            logger.warning("No reference audio provided, using zero-shot mode")
            # 在零样本模式下，F5-TTS可能需要默认的说话人音色
        
        # 语言映射
        language_mapping = {
            '中文': 'zh',
            'English': 'en', 
            'Japanese': 'ja',
            'Korean': 'ko',
            'French': 'fr',
            'Spanish': 'es',
            'German': 'de',
            'Italian': 'it',
            'Portuguese': 'pt',
            'Polish': 'pl',
            'Turkish': 'tr',
            'Russian': 'ru',
            'Dutch': 'nl',
            'Czech': 'cs',
            'Arabic': 'ar',
            'Hungarian': 'hu',
            'Hindi': 'hi'
        }
        
        lang_code = language_mapping.get(target_language, 'zh')
        
        # 进行语音合成
        logger.info(f"Generating speech for: {text[:50]}...")
        
        # F5-TTS推理
        if ref_audio is not None:
            # 声音克隆模式
            wav, sr, _ = f5tts.infer(
                ref_audio=ref_audio,
                ref_text=ref_text,
                gen_text=text,
                model_obj=None,
                vocoder=vocoder,
                cross_fade_duration=0.15,
                speed=1.0,
                show_info=True
            )
        else:
            # 零样本模式
            wav, sr, _ = f5tts.infer(
                ref_audio=None,
                ref_text="",
                gen_text=text,
                model_obj=None,
                vocoder=vocoder,
                cross_fade_duration=0.15,
                speed=1.0,
                show_info=True
            )
        
        # 保存音频文件
        if isinstance(wav, torch.Tensor):
            wav = wav.cpu().numpy()
        
        # 确保音频是单声道
        if wav.ndim > 1:
            wav = wav.squeeze()
        
        # 归一化音频
        wav = wav / np.max(np.abs(wav)) * 0.9
        
        # 保存为WAV文件
        torchaudio.save(
            output_path,
            torch.tensor(wav).unsqueeze(0),
            sample_rate=sr
        )
        
        logger.info(f"F5-TTS synthesis successful: {output_path}")
        return True
        
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
        os.remove(output_path)
        return True
    else:
        logger.error("F5-TTS test failed")
        return False


if __name__ == "__main__":
    # 运行测试
    test_f5tts()
