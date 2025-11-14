#!/bin/bash
# 修复 WhisperX VAD 模型下载 301 错误
# 用法：bash scripts/fix_whisperx_vad.sh

set -e

echo "======================================"
echo "修复 WhisperX VAD 模型下载 301 错误"
echo "======================================"

# 检查是否在 conda 环境中
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "❌ 错误：请先激活 conda 环境"
    echo "   运行: conda activate linly_dubbing"
    exit 1
fi

echo "✓ 当前 conda 环境: $CONDA_DEFAULT_ENV"

# 检查 whisperx 是否已安装
if ! python -c "import whisperx" 2>/dev/null; then
    echo "❌ 错误：whisperx 未安装"
    echo "   请先安装: pip install git+https://github.com/m-bain/whisperx.git"
    exit 1
fi

echo "✓ whisperx 已安装"

# 获取 whisperx 安装路径
WHISPERX_PATH=$(python -c "import whisperx; import os; print(os.path.dirname(whisperx.__file__))")
VAD_FILE="$WHISPERX_PATH/vad.py"

echo "✓ WhisperX 路径: $WHISPERX_PATH"

# 备份原文件
if [ -f "$VAD_FILE" ]; then
    BACKUP_FILE="${VAD_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$VAD_FILE" "$BACKUP_FILE"
    echo "✓ 已备份原文件: $BACKUP_FILE"
else
    echo "❌ 错误：找不到 vad.py 文件"
    exit 1
fi

# 方法1：从项目 submodules 重新安装（推荐）
if [ -d "submodules/whisperX" ]; then
    echo ""
    echo "方法1：从本地 submodules 重新安装 whisperx（推荐）"
    echo "---------------------------------------"
    pip uninstall -y whisperx
    pip install -e submodules/whisperX
    echo "✅ 已从本地 submodules 安装 whisperx"
else
    # 方法2：直接修改已安装的文件
    echo ""
    echo "方法2：直接修改已安装的 vad.py 文件"
    echo "---------------------------------------"

    python << 'PYTHON_SCRIPT'
import re

vad_file = "$VAD_FILE"

with open(vad_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换下载代码
old_pattern = r'(\s+if not os\.path\.isfile\(model_fp\):\s+)with urllib\.request\.urlopen\(VAD_SEGMENTATION_URL\) as source'
new_code = r'\1# 创建支持重定向的请求，解决HuggingFace 301错误\n        req = urllib.request.Request(VAD_SEGMENTATION_URL, headers={\'User-Agent\': \'Mozilla/5.0\'})\n        with urllib.request.urlopen(req) as source'

content_modified = re.sub(old_pattern, new_code, content)

if content_modified != content:
    with open(vad_file, 'w', encoding='utf-8') as f:
        f.write(content_modified)
    print("✅ 已修复 vad.py 文件")
else:
    print("⚠️  警告：未找到需要修改的代码，可能已经修复过了")
PYTHON_SCRIPT

fi

echo ""
echo "======================================"
echo "✅ 修复完成！"
echo "======================================"
echo ""
echo "现在可以正常使用 WhisperX 了"
echo ""
