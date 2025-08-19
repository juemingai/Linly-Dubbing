import os
from loguru import logger
import numpy as np
import torch
import time
from .utils import save_wav
import sys

import torchaudio
model = None



#  <|zh|><|en|><|jp|><|yue|><|ko|> for Chinese/English/Japanese/Cantonese/Korean
language_map = {
    '中文': 'zh-CN-XiaoxiaoNeural',
    'English': 'en-US-MichelleNeural',
    'Japanese': 'ja-JP-NanamiNeural',
    '粤语': 'zh-HK-HiuMaanNeural',
    'Korean': 'ko-KR-SunHiNeural'
}

def tts(text, output_path, target_language='中文', voice = 'zh-CN-XiaoxiaoNeural'):
    if os.path.exists(output_path):
        logger.info(f'TTS {text} 已存在')
        return True
    
    mp3_path = output_path.replace(".wav", ".mp3")
    
    for retry in range(3):
        try:
            # 使用subprocess替代os.system以获得更好的错误处理
            import subprocess
            cmd = f'edge-tts --text "{text}" --write-media "{mp3_path}" --voice {voice}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # 检查MP3文件是否生成成功
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                    # 将MP3转换为WAV格式
                    try:
                        import librosa
                        import soundfile as sf
                        audio, sr = librosa.load(mp3_path, sr=24000)
                        sf.write(output_path, audio, sr)
                        
                        # 删除临时MP3文件
                        if os.path.exists(mp3_path):
                            os.remove(mp3_path)
                        
                        logger.info(f'TTS {text} 生成成功')
                        return True
                    except Exception as e:
                        logger.warning(f'MP3转WAV失败: {e}')
                        # 如果转换失败，至少保留MP3文件
                        if os.path.exists(mp3_path):
                            os.rename(mp3_path, output_path.replace('.wav', '.mp3'))
                        return False
                else:
                    logger.warning(f'Edge-TTS生成文件失败或文件为空: {mp3_path}')
            else:
                logger.warning(f'Edge-TTS命令执行失败: {result.stderr}')
                
        except subprocess.TimeoutExpired:
            logger.warning(f'TTS {text} 超时 (第{retry+1}次尝试)')
        except Exception as e:
            logger.warning(f'TTS {text} 失败 (第{retry+1}次尝试): {e}')
            
        if retry < 2:  # 不是最后一次重试
            logger.info(f'等待2秒后重试...')
            time.sleep(2)
    
    logger.error(f'TTS {text} 最终失败，已尝试3次')
    return False


if __name__ == '__main__':
    speaker_wav = r'videos/村长台钓加拿大/20240805 英文无字幕 阿里这小子在水城威尼斯发来问候/audio_vocals.wav'
    while True:
        text = input('请输入：')
        tts(text, f'playground/{text}.wav', target_language='中文')
        
