# F5-TTS 集成文档

## 概述

F5-TTS是一个基于Flow Matching的高质量语音合成模型，支持多语言和语音克隆功能。本项目已经集成了F5-TTS作为新的TTS方法选项。

## 功能特性

- **高质量语音合成**: 基于最新的Flow Matching技术
- **多语言支持**: 支持17种语言包括中文、英文、日文、韩文、法文、西班牙文、德文、意大利文、葡萄牙文、波兰文、土耳其文、俄文、荷兰文、捷克文、阿拉伯文、匈牙利文、印地文
- **语音克隆**: 支持使用参考音频进行声音克隆
- **零样本合成**: 即使没有参考音频也可以生成语音

## 服务器安装说明

### 环境要求

- Python 3.8+
- PyTorch 2.0+ (推荐使用GPU版本)
- CUDA 11.8+ (如果使用GPU)

### 安装步骤

1. **安装PyTorch** (根据您的CUDA版本选择)
   ```bash
   # CUDA 11.8
   pip install torch==2.4.0+cu118 torchaudio==2.4.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
   
   # CUDA 12.1
   pip install torch==2.4.0+cu121 torchaudio==2.4.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121
   
   # CPU版本
   pip install torch==2.4.0+cpu torchaudio==2.4.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
   ```

2. **安装F5-TTS**
   ```bash
   pip install f5-tts
   ```

3. **验证安装**
   ```bash
   python -c "import f5_tts; print('F5-TTS安装成功')"
   ```

### 模型下载

F5-TTS会在首次运行时自动下载模型文件，包括：
- F5TTS_v1_Base模型
- Vocos vocoder模型

模型文件将下载到 `~/.cache/huggingface/hub/` 目录。

## 使用方法

### 在UI界面中使用

1. 打开Linly-Dubbing主界面
2. 切换到"TTS语音合成"标签页
3. 在"AI语音生成方法"下拉菜单中选择"f5tts"
4. 选择目标语言
5. 设置视频文件夹路径
6. 点击"开始生成语音"

### 支持的语言

F5-TTS支持以下语言：
- 中文 (zh)
- English (en)
- Japanese (ja)
- Korean (ko)
- French (fr)
- Spanish (es)
- German (de)
- Italian (it)
- Portuguese (pt)
- Polish (pl)
- Turkish (tr)
- Russian (ru)
- Dutch (nl)
- Czech (cs)
- Arabic (ar)
- Hungarian (hu)
- Hindi (hi)

### 语音克隆功能

F5-TTS支持使用参考音频进行语音克隆：
- 将参考音频文件放置在 `{video_folder}/SPEAKER/{speaker_name}.wav` 路径下
- 系统会自动使用参考音频进行声音克隆
- 参考音频建议：清晰、无噪音、3-10秒长度

## 技术实现细节

### 集成文件

1. **核心模块**: `tools/step045_tts_f5tts.py`
   - F5-TTS模型加载和推理
   - 语音合成主要逻辑
   - 错误处理和日志记录

2. **主TTS模块**: `tools/step040_tts.py`
   - 集成F5-TTS到现有TTS流程
   - 支持语言列表更新
   - 统一的语音生成接口

3. **UI界面**: `tabs/tts_tab.py`
   - 添加F5-TTS选项到界面
   - 扩展支持语言列表

### API接口

```python
from tools.step045_tts_f5tts import tts as f5tts_tts

# 基本语音合成
success = f5tts_tts(
    text="要合成的文本",
    output_path="output.wav",
    target_language="中文"
)

# 语音克隆
success = f5tts_tts(
    text="要合成的文本",
    output_path="output.wav",
    speaker_wav="reference.wav",
    target_language="中文"
)
```

## 性能优化建议

### GPU使用
- 推荐使用GPU进行推理，速度比CPU快10-20倍
- 推荐显存：6GB+
- 支持多GPU并行处理

### 内存管理
- 长文本会自动分块处理
- 模型会在首次使用时加载，后续重用
- 推荐系统内存：8GB+

### 音频质量
- 输出采样率：24kHz
- 音频格式：WAV (16-bit)
- 支持自动音频长度调整

## 故障排除

### 常见问题

1. **模型下载失败**
   - 检查网络连接
   - 确保有足够的磁盘空间
   - 可以手动下载模型文件

2. **CUDA内存不足**
   - 降低batch size
   - 使用CPU模式
   - 分块处理长文本

3. **音频质量问题**
   - 检查参考音频质量
   - 确保参考音频采样率正确
   - 调整推理参数

### 日志调试

F5-TTS模块使用loguru进行日志记录，可以通过以下方式查看详细日志：

```python
from loguru import logger
logger.add("f5tts_debug.log", level="DEBUG")
```

## 更新和维护

### 模型更新
```bash
pip install --upgrade f5-tts
```

### 清理缓存
```bash
rm -rf ~/.cache/huggingface/hub/models--SWivid--F5-TTS
```

## 参考资源

- [F5-TTS GitHub仓库](https://github.com/SWivid/F5-TTS)
- [F5-TTS论文](https://arxiv.org/abs/2410.06885)
- [Hugging Face模型页面](https://huggingface.co/SWivid/F5-TTS)

## 许可证

F5-TTS使用MIT许可证，预训练模型由于训练数据原因使用CC-BY-NC许可证。
