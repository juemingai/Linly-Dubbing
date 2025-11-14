#!/usr/bin/env python3
"""
修复 WhisperX VAD 模型下载 301 错误
用法：python scripts/fix_whisperx_vad.py
"""

import os
import sys
import shutil
from datetime import datetime

def main():
    print("=" * 50)
    print("修复 WhisperX VAD 模型下载 301 错误")
    print("=" * 50)

    # 检查 whisperx 是否已安装
    try:
        import whisperx
    except ImportError:
        print("❌ 错误：whisperx 未安装")
        print("   请先安装: pip install git+https://github.com/m-bain/whisperx.git")
        sys.exit(1)

    print("✓ whisperx 已安装")

    # 获取 whisperx 安装路径
    whisperx_path = os.path.dirname(whisperx.__file__)
    vad_file = os.path.join(whisperx_path, 'vad.py')

    print(f"✓ WhisperX 路径: {whisperx_path}")

    if not os.path.exists(vad_file):
        print(f"❌ 错误：找不到 vad.py 文件: {vad_file}")
        sys.exit(1)

    # 备份原文件
    backup_file = f"{vad_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(vad_file, backup_file)
    print(f"✓ 已备份原文件: {backup_file}")

    # 读取文件内容
    with open(vad_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换下载代码
    old_code = '        with urllib.request.urlopen(VAD_SEGMENTATION_URL) as source, open(model_fp, "wb") as output:'

    new_code = '''        # 创建支持重定向的请求，解决HuggingFace 301错误
        req = urllib.request.Request(VAD_SEGMENTATION_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as source, open(model_fp, "wb") as output:'''

    if old_code in content:
        content_modified = content.replace(old_code, new_code)

        # 写回文件
        with open(vad_file, 'w', encoding='utf-8') as f:
            f.write(content_modified)

        print("✅ 已修复 vad.py 文件，添加301重定向支持")
    else:
        print("⚠️  警告：未找到需要修改的代码，可能已经修复过了")

    print("")
    print("=" * 50)
    print("✅ 修复完成！")
    print("=" * 50)
    print("")
    print("现在可以正常使用 WhisperX 了")
    print("")

if __name__ == '__main__':
    main()
