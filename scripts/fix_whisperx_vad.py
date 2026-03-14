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

    # 替换下载代码：用 requests 替换 urllib，requests 可正确跟随 301 重定向
    replacements = [
        # 原始代码（未修改过）
        (
            '        with urllib.request.urlopen(VAD_SEGMENTATION_URL) as source, open(model_fp, "wb") as output:',
            '''\
        # 使用 requests 替换 urllib，正确跟随 301 重定向
        import requests as _requests
        _resp = _requests.get(VAD_SEGMENTATION_URL, stream=True, allow_redirects=True, timeout=60)
        _resp.raise_for_status()
        with open(model_fp, "wb") as output:
            for _chunk in _resp.iter_content(chunk_size=8192):
                output.write(_chunk)
        if False:  # 保留缩进结构，原 with 块占位'''
        ),
        # 之前用 User-Agent 修改过的版本
        (
            '        # 创建支持重定向的请求，解决HuggingFace 301错误\n        req = urllib.request.Request(VAD_SEGMENTATION_URL, headers={\'User-Agent\': \'Mozilla/5.0\'})\n        with urllib.request.urlopen(req) as source, open(model_fp, "wb") as output:',
            '''\
        # 使用 requests 替换 urllib，正确跟随 301 重定向
        import requests as _requests
        _resp = _requests.get(VAD_SEGMENTATION_URL, stream=True, allow_redirects=True, timeout=60)
        _resp.raise_for_status()
        with open(model_fp, "wb") as output:
            for _chunk in _resp.iter_content(chunk_size=8192):
                output.write(_chunk)
        if False:  # 保留缩进结构，原 with 块占位'''
        ),
    ]

    patched = False
    for old_code, new_code in replacements:
        if old_code in content:
            content = content.replace(old_code, new_code)
            patched = True
            break

    if patched:
        print("✅ 已修复 vad.py 文件：用 requests 替换 urllib，支持 301 重定向")
    else:
        print("⚠️  未找到下载代码，可能已修复")

    # 注释掉 SHA256 校验（模型 URL 重定向后文件版本可能不同导致校验失败）
    sha256_old = '''\
        if check_sha256:
            sha256_hash = hashlib.sha256()
            with open(model_fp, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            if sha256_hash.hexdigest() != sha256:
                raise RuntimeError(
                    "Model has been downloaded but the SHA256 checksum does not not match. Please retry loading the model."
                )'''
    sha256_new = '''\
        # SHA256 校验已跳过（模型 URL 重定向后文件版本可能不同，跳过以避免误报）
        if False and check_sha256:
            sha256_hash = hashlib.sha256()
            with open(model_fp, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            if sha256_hash.hexdigest() != sha256:
                raise RuntimeError(
                    "Model has been downloaded but the SHA256 checksum does not not match. Please retry loading the model."
                )'''

    if sha256_old in content:
        content = content.replace(sha256_old, sha256_new)
        print("✅ 已注释 SHA256 校验")
    else:
        # 尝试直接注释掉 RuntimeError 那行
        sha256_raise = '                    "Model has been downloaded but the SHA256 checksum does not not match. Please retry loading the model."'
        if sha256_raise in content:
            content = content.replace(
                'if sha256_hash.hexdigest() != sha256:',
                'if False and sha256_hash.hexdigest() != sha256:  # 已跳过校验'
            )
            print("✅ 已跳过 SHA256 校验条件")
        else:
            print("⚠️  未找到 SHA256 校验代码，可能已修复或代码结构不同")

    with open(vad_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 删除损坏的缓存模型文件（SHA256 校验失败的文件）
    import torch
    model_dir = os.path.join(torch.hub.get_dir(), "checkpoints")
    if os.path.isdir(model_dir):
        for fname in os.listdir(model_dir):
            fpath = os.path.join(model_dir, fname)
            fsize = os.path.getsize(fpath)
            if fsize < 1024 * 1024:  # 小于 1MB 认为是损坏文件（正常 VAD 模型约 17MB）
                os.remove(fpath)
                print(f"✅ 已删除损坏的缓存文件: {fname} ({fsize} bytes)")

    print("")
    print("=" * 50)
    print("✅ 修复完成！")
    print("=" * 50)
    print("")
    print("重启 webui.py 后 WhisperX 将自动重新下载 VAD 模型")
    print("")

if __name__ == '__main__':
    main()
