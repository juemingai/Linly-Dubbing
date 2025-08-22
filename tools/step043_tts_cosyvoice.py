import os
from loguru import logger
import numpy as np
import torch
import time
from .utils import save_wav
import sys
import torchaudio

# CosyVoice相关导入放在函数内部，避免启动时错误
model = None

def download_cosyvoice():
    try:
        from modelscope import snapshot_download
        snapshot_download('iic/CosyVoice-300M', local_dir='models/TTS/CosyVoice-300M')
    except ImportError as e:
        logger.error(f"Failed to import modelscope: {e}")
        raise

def init_cosyvoice():
    load_model()
    
def load_model(model_path="models/TTS/CosyVoice-300M", device='auto'):
    global model
    if model is not None:
        return

    try:
        # 在使用时才导入CosyVoice相关模块
        sys.path.append('CosyVoice/third_party/Matcha-TTS')
        sys.path.append('CosyVoice/')
        from cosyvoice.cli.cosyvoice import CosyVoice
        
        if device=='auto':
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f'Loading CoxyVoice model from {model_path}')
        t_start = time.time()
        if not os.path.exists(model_path):
            download_cosyvoice()
        model = CosyVoice(model_path)
        t_end = time.time()
        logger.info(f'CoxyVoice model loaded in {t_end - t_start:.2f}s')
    except ImportError as e:
        logger.error(f"Failed to import CosyVoice: {e}")
        logger.info("Please install CosyVoice if you want to use this TTS method")
        raise
    
#  <|zh|><|en|><|jp|><|yue|><|ko|> for Chinese/English/Japanese/Cantonese/Korean
language_map = {
    '中文': 'zh',
    'English': 'en',
    'Japanese': 'jp',
    '粤语': 'yue',
    'Korean': 'ko'
}

def tts(text, output_path, speaker_wav, model_name="models/TTS/CosyVoice-300M", device='auto', target_language='中文'):
    global model
    
    if os.path.exists(output_path):
        logger.info(f'TTS {text} 已存在')
        return
    
    try:
        # 动态导入load_wav
        from cosyvoice.utils.file_utils import load_wav
        
        if model is None:
            load_model(model_name, device)
        
        for retry in range(3):
            try:
                prompt_speech_16k = load_wav(speaker_wav, 16000)
                output = model.inference_cross_lingual(f'<|{language_map[target_language]}|>{text}', prompt_speech_16k)
                torchaudio.save(output_path, output['tts_speech'], 22050)

                logger.info(f'TTS {text}')
                break
            except Exception as e:
                logger.warning(f'TTS {text} 失败')
                logger.warning(e)
    except ImportError as e:
        logger.error(f"CosyVoice not available: {e}")
        logger.info("Please install CosyVoice if you want to use this TTS method")
        return False


if __name__ == '__main__':
    speaker_wav = r'videos/村长台钓加拿大/20240805 英文无字幕 阿里这小子在水城威尼斯发来问候/audio_vocals.wav'
    os.makedirs('playground', exist_ok=True)
    while True:
        text = input('请输入：')
        tts(text, f'playground/{text}.wav', speaker_wav = speaker_wav, target_langugae = "粤语")
        
