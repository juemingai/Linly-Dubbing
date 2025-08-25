# TTS 集成指南

## 问题背景

用户在使用 Edge-TTS 时遇到 403 错误：
```
aiohttp.client_exceptions.WSServerHandshakeError: 403, message='Invalid response status', url='wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=6A5AA1D4EAFF4E9FB37E23D68491D6F4&ConnectionId=2dc1bc8fd5354070864440109dd15118'
```

这表明微软对 Edge-TTS 服务实施了更严格的访问限制。

## 解决方案

### 1. 立即解决 Edge-TTS 问题

#### 方法一：更新 Edge-TTS
```bash
pip install --upgrade edge-tts
```

#### 方法二：使用 Edge-TTS 诊断工具
```bash
cd Linly-Dubbing
python tools/diagnose_edge_tts.py
```

#### 方法三：切换到其他 TTS 方法
推荐使用以下替代方案：
- `cosyvoice` (阿里巴巴，支持语音克隆)
- `xtts` (Coqui，开源语音克隆)
- `minimax` (商业API，本指南新增)

### 2. 集成 Minimax TTS (推荐)

#### 优势
- ✅ 商业级稳定性和质量保证
- ✅ 官方技术支持
- ✅ 语音克隆功能
- ✅ 多语言支持
- ✅ 无需本地GPU资源

#### 安装配置

1. **获取 Minimax API Key**
   - 访问 [Minimax 官网](https://www.minimaxi.com/)
   - 注册账号并获取 API Key

2. **配置环境变量**
   ```bash
   # 编辑 .env 文件
   echo "MINIMAX_API_KEY=your_minimax_api_key_here" >> .env
   ```

3. **验证安装**
   ```bash
   python -c "from tools.step046_tts_minimax import tts; print('Minimax TTS 可用')"
   ```

#### 使用方法

##### 在 WebUI 中使用
1. 打开 Linly-Dubbing 主界面
2. 在 "AI语音生成方法" 下拉菜单中选择 "minimax"
3. 选择目标语言
4. 开始处理

##### 在代码中使用
```python
from tools.step046_tts_minimax import tts

# 基本用法
success = tts(
    text="这是测试文本",
    output_path="output.wav",
    target_language="中文"
)

# 语音克隆用法
success = tts(
    text="这是测试文本",
    output_path="output.wav", 
    speaker_wav="reference_audio.wav",  # 参考音频
    target_language="中文"
)
```

### 3. 支持的语言和功能

#### Minimax TTS 支持的语言
- 中文 (zh)
- English (en)
- Japanese (ja)
- Korean (ko)
- French (fr)
- Spanish (es)
- German (de)
- Italian (it)
- Portuguese (pt)

#### 主要功能
1. **文本转语音**：将文本转换为自然的语音
2. **语音克隆**：基于参考音频克隆特定音色
3. **参数调节**：
   - 语速控制 (0.5-2.0)
   - 音量控制 (0.1-1.0)
   - 音高调节 (0.5-2.0)

### 4. 成本考虑

#### 各 TTS 方案成本对比

| 方案 | 类型 | 成本 | 质量 | 稳定性 | 语音克隆 |
|------|------|------|------|--------|----------|
| Edge-TTS | 免费 | 免费 | 中等 | 不稳定⚠️ | ❌ |
| CosyVoice | 本地 | GPU成本 | 高 | 稳定 | ✅ |
| XTTS | 本地 | GPU成本 | 高 | 稳定 | ✅ |
| Minimax | 商业API | 按量付费 | 很高 | 很稳定 | ✅ |

#### Minimax 定价建议
- 新用户通常有免费额度
- 按字符数或音频时长计费
- 大批量使用建议联系商务获取优惠

### 5. 最佳实践建议

#### 混合使用策略
```python
# 推荐的 TTS 方法优先级
TTS_PRIORITY = [
    'minimax',     # 首选：商业API，稳定可靠
    'cosyvoice',   # 次选：高质量本地方案
    'xtts',        # 备选：开源方案
    'EdgeTTS'      # 最后：免费但不稳定
]
```

#### 批量处理优化
1. **预检查**：处理前先测试 TTS 服务可用性
2. **重试机制**：失败时自动切换到备用方案
3. **并发控制**：避免API频率限制
4. **缓存机制**：避免重复生成相同内容

### 6. 故障排除

#### 常见问题

**Q: Minimax API 调用失败**
A: 检查以下项目：
- API Key 是否正确设置
- 网络连接是否正常
- API 余额是否充足
- 请求频率是否过高

**Q: 语音克隆效果不理想**
A: 优化建议：
- 使用清晰、无噪音的参考音频
- 参考音频长度建议 10-30 秒
- 确保参考音频为单一说话人
- 调整语速、音高等参数

**Q: 处理大批量内容时失败**
A: 解决方案：
- 启用重试机制
- 增加请求间隔
- 分批处理
- 监控API使用量

### 7. 集成其他商业 TTS API

项目架构支持轻松集成其他商业 TTS 服务：

#### 支持的商业 API
- **Azure Cognitive Services**
- **Google Cloud Text-to-Speech**
- **AWS Polly**
- **百度语音合成**
- **讯飞语音合成**

#### 集成步骤
1. 参考 `step046_tts_minimax.py` 创建新的集成模块
2. 在 `step040_tts.py` 中添加支持
3. 更新 WebUI 选项列表
4. 添加环境变量配置

### 8. 总结

通过集成 Minimax 等商业 TTS API，Linly-Dubbing 项目可以：

1. **解决 Edge-TTS 不稳定问题**
2. **提供企业级的服务质量**
3. **支持高质量语音克隆**
4. **确保长期服务稳定性**

建议根据具体使用场景选择合适的 TTS 方案，对于商业用途推荐使用 Minimax 等付费服务确保质量和稳定性。

---

## 快速开始

1. **设置 Minimax API Key**
   ```bash
   echo "MINIMAX_API_KEY=your_api_key" >> .env
   ```

2. **测试集成**
   ```bash
   python tools/step046_tts_minimax.py
   ```

3. **在项目中使用**
   - 启动 WebUI：`python webui.py`
   - 选择 "minimax" 作为 TTS 方法
   - 开始处理视频

有任何问题请参考项目文档或提交 Issue。
