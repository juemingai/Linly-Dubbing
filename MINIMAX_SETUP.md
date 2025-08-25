# Minimax TTS 快速设置指南

## 🚀 快速开始

### 1. 获取 Minimax API 凭证

访问 [Minimax 官网](https://www.minimaxi.com/) 获取：
- `API Key` 
- `Group ID`

### 2. 配置环境变量

在项目根目录的 `.env` 文件中添加：

```bash
# Minimax TTS API 配置
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_GROUP_ID=your_minimax_group_id_here
```

### 3. 安装依赖

确保已安装必要的依赖：

```bash
pip install requests librosa soundfile
```

### 4. 测试集成

```bash
cd Linly-Dubbing
python tools/step046_tts_minimax.py
```

如果看到 "测试成功" 表示集成正常。

### 5. 在 WebUI 中使用

1. 启动 WebUI：
   ```bash
   python webui.py
   ```

2. 在界面中：
   - 选择 "AI语音生成方法" → `minimax`
   - 在 "Minimax音色ID" 输入框中输入您想要的音色ID
   - 选择目标语言
   - 开始处理

## 🎨 默认音色ID

**默认音色（推荐）:**
- **音色ID**: `cobra_design_20250717_162427_683071`
- **音色名称**: 都市白领
- **模型版本**: `speech-2.5-hd-preview`
- **适用场景**: 通用场景，声音自然流畅

> 💡 **提示**: 您也可以使用自己通过 Minimax 语音克隆功能创建的自定义音色ID

## 🔧 高级配置

### 支持的参数

Minimax TTS 支持以下参数调节：

- **语速** (speed): 0.5-2.0，默认 1.0
- **音量** (volume): 0.1-10.0，默认 1.0  
- **音高** (pitch): -12 到 12，默认 0
- **情感** (emotion): happy, sad, angry, fearful, disgusted, surprised, neutral

### 模型版本

本集成使用最新的 `speech-2.5-hd-preview` 模型，提供最佳的语音合成质量。

## 📝 使用示例

### 在代码中直接调用

```python
from tools.step046_tts_minimax import tts

# 基本使用（使用默认音色）
success = tts(
    text="这是一个测试文本", 
    output_path="output.wav",
    target_language="中文"
)

# 使用指定音色ID
success = tts(
    text="这是一个测试文本", 
    output_path="output.wav",
    target_language="中文",
    voice_id="cobra_design_20250717_162427_683071"
)

# 高级参数调节
success = tts(
    text="Hello, this is a test",
    output_path="output_en.wav", 
    target_language="English",
    voice_id="your_custom_voice_id",  # 您的自定义音色ID
    speed=1.2,
    volume=1.5,
    pitch=2,
    emotion="happy"
)
```

### 批量处理

```python
from tools.step040_tts import generate_all_wavs_under_folder

result = generate_all_wavs_under_folder(
    root_folder="videos",
    method="minimax",
    target_language="中文", 
    voice_id="cobra_design_20250717_162427_683071"
)
```

## ❗ 故障排除

### 常见问题

**Q: API调用失败，返回401错误**  
A: 检查 `MINIMAX_API_KEY` 是否正确设置

**Q: API调用失败，返回403错误**  
A: 检查 `MINIMAX_GROUP_ID` 是否正确，或账户是否有足够额度

**Q: 音色ID无效**  
A: 确认音色ID拼写正确，或联系Minimax获取可用音色列表

**Q: 生成的音频有问题**  
A: 
- 检查文本内容是否包含特殊字符
- 尝试调整语速、音量等参数
- 确认目标语言与音色ID匹配

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 💰 成本优化建议

1. **使用最新模型**: `speech-2.5-hd-preview` 提供最佳性价比
2. **批量处理**: 减少API调用频率
3. **文本预处理**: 移除不必要的标点和格式
4. **缓存机制**: 避免重复生成相同内容
5. **音色复用**: 对于同一类型内容，复用相同音色ID

## 🔗 相关链接

- [Minimax 官方文档](https://www.minimaxi.com/document)
- [音色ID 参考](https://www.minimaxi.com/document/voice-ids)
- [API 定价](https://www.minimaxi.com/pricing)

---

## ✅ 完成设置后

您现在可以享受稳定、高质量的 AI 配音服务了！

- ✅ 解决了 Edge-TTS 的 403 错误问题
- ✅ 获得了商业级的语音合成质量  
- ✅ 支持语音克隆和多种音色选择
- ✅ 稳定的 API 服务，无需担心服务中断

有任何问题请查看 `docs/TTS_Integration_Guide.md` 或提交 Issue。
