# 修复 WhisperX VAD 模型下载 301 错误

## 问题描述

使用 WhisperX 进行语音识别时，VAD（Voice Activity Detection）模型自动下载失败：

```
urllib.error.HTTPError: HTTP Error 301: Moved Permanently
```

## 已修改的内容

本项目已在 `submodules/whisperX/whisperx/vad.py` 中修复了此问题：

- ✅ 添加了 HTTP 重定向支持
- ✅ 添加了 User-Agent 头部
- ✅ 注释掉了 SHA256 校验（可选）

## 部署修复（远程环境）

推送代码到远程服务器后，有以下几种方法应用修复：

### 方法1：使用自动修复脚本（推荐）

```bash
# 激活 conda 环境
conda activate linly_dubbing

# 进入项目目录
cd /workspace/Linly-Dubbing

# 运行 Python 修复脚本
python scripts/fix_whisperx_vad.py
```

### 方法2：从本地 submodules 重新安装 whisperx

```bash
# 激活 conda 环境
conda activate linly_dubbing

# 进入项目目录
cd /workspace/Linly-Dubbing

# 卸载现有的 whisperx
pip uninstall -y whisperx

# 从本地 submodules 安装（使用修改后的代码）
pip install -e submodules/whisperX
```

### 方法3：手动下载模型（最快速）

如果不想修改代码，直接手动下载模型：

```bash
# 查看模型存放路径
TARGET_PATH=$(python3 -c "import torch; import os; print(os.path.join(torch.hub._get_torch_home(), 'whisperx-vad-segmentation.bin'))")
echo "目标路径: $TARGET_PATH"

# 创建目录
mkdir -p $(dirname $TARGET_PATH)

# 下载模型
wget -O $TARGET_PATH https://huggingface.co/Synthetai/whisperx-vad-segmentation/resolve/main/pytorch_model.bin

# 验证
ls -lh $TARGET_PATH
```

## 验证修复

修复后运行测试：

```bash
python -c "
import whisperx
import torch

# 测试加载 VAD 模型
from whisperx.vad import load_vad_model
device = 'cuda' if torch.cuda.is_available() else 'cpu'
vad_model = load_vad_model(torch.device(device))
print('✅ VAD 模型加载成功！')
"
```

## 技术细节

### 原代码（有问题）

```python
with urllib.request.urlopen(VAD_SEGMENTATION_URL) as source, open(model_fp, "wb") as output:
```

### 修复后的代码

```python
# 创建支持重定向的请求，解决HuggingFace 301错误
req = urllib.request.Request(VAD_SEGMENTATION_URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as source, open(model_fp, "wb") as output:
```

### 修改说明

1. **添加 Request 对象**：允许自定义请求头
2. **添加 User-Agent**：模拟浏览器请求，避免被拦截
3. **自动处理重定向**：urllib 的 Request 对象会自动跟随 301/302 重定向

## 相关文件

- `submodules/whisperX/whisperx/vad.py` - 已修复的源代码
- `scripts/fix_whisperx_vad.py` - 自动修复脚本
- `scripts/fix_whisperx_vad.sh` - Bash 修复脚本
- `问题参考汇总.md` - 完整的问题和解决方案汇总

## 参考链接

- [WhisperX GitHub](https://github.com/m-bain/whisperx)
- [VAD 模型页面](https://huggingface.co/Synthetai/whisperx-vad-segmentation)
- [Python urllib 重定向处理](https://docs.python.org/3/library/urllib.request.html)
