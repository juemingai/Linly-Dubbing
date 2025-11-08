# YouTube视频下载失败问题修复

## 问题分析

根据错误日志，下载失败的主要原因有：

### 1. **YouTube要求Cookie验证**
```
ERROR: [youtube] 6MAufQ6vGtI: Sign in to confirm you're not a bot. 
Use --cookies-from-browser or --cookies for the authentication.
```

**原因**：YouTube检测到机器人行为，要求登录验证才能下载视频。

### 2. **直接HTTP下载失败**
- 当yt-dlp所有格式都失败后，代码尝试了直接HTTP下载
- 但YouTube视频不能直接通过HTTP下载，导致下载的是HTML页面而不是视频文件
- 结果：文件损坏，出现 `moov atom not found` 错误

### 3. **文件验证缺失**
- 下载后没有验证文件是否有效
- 导致损坏的文件被保存，后续处理失败

## 修复内容

### 1. **添加文件验证机制**
- 新增 `_validate_video_file()` 函数
- 检查文件大小、扩展名、文件头
- 检测HTML文件（避免下载错误页面）

### 2. **改进Cookie错误提示**
- 检测到需要Cookie时，提供详细的配置说明
- 显示当前Cookie配置状态
- 提供多种解决方案

### 3. **修复直接HTTP下载**
- YouTube/Bilibili视频不再尝试直接HTTP下载
- 直接抛出清晰的错误信息
- 仅对非YouTube/Bilibili的直接视频链接使用HTTP下载

### 4. **增强错误处理**
- 在所有下载步骤中添加文件验证
- 检测已存在文件是否损坏，自动重新下载
- 提供更清晰的错误信息

## 解决方案

### 方法1：使用Cookie文件（推荐）

1. **导出Cookie文件**
```bash
# 从Chrome浏览器导出Cookie
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com/watch?v=xxxx"

# 从Firefox导出
yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.youtube.com/watch?v=xxxx"
```

2. **设置环境变量**
```bash
export YTDLP_COOKIES_FILE="/path/to/cookies.txt"
```

3. **在代码中设置**（如果使用.env文件）
```bash
# 在 .env 文件中添加
YTDLP_COOKIES_FILE=/path/to/cookies.txt
```

### 方法2：从浏览器自动提取Cookie

```bash
# 从Chrome提取
export YTDLP_COOKIES_BROWSER="chrome"

# 从Firefox提取
export YTDLP_COOKIES_BROWSER="firefox"

# 指定浏览器配置文件（可选）
export YTDLP_COOKIES_PROFILE="Default"
```

### 方法3：使用浏览器扩展导出Cookie

1. 安装浏览器扩展（如 "Get cookies.txt LOCALLY"）
2. 访问YouTube并登录
3. 导出Cookie为Netscape格式
4. 保存为 `cookies.txt`
5. 设置环境变量指向该文件

## 验证修复

修复后，程序会：

1. ✅ **自动检测Cookie需求**：当YouTube要求登录时，会明确提示
2. ✅ **验证下载文件**：确保下载的是有效视频文件
3. ✅ **拒绝无效下载**：不再尝试直接HTTP下载YouTube视频
4. ✅ **提供清晰错误**：给出具体的解决方案

## 测试命令

```bash
# 测试Cookie配置
python -c "
import os
cookie_file = os.getenv('YTDLP_COOKIES_FILE', 'cookies.txt')
browser = os.getenv('YTDLP_COOKIES_BROWSER')
print(f'Cookie文件: {cookie_file}, 存在: {os.path.exists(cookie_file) if cookie_file else False}')
print(f'浏览器Cookie: {browser}')
"

# 测试下载
python tools/step000_video_downloader.py
```

## 注意事项

1. **Cookie文件需要定期更新**：YouTube Cookie会过期，需要重新导出
2. **Cookie文件安全**：不要将Cookie文件提交到Git仓库
3. **浏览器选择**：确保选择的浏览器已登录YouTube账号
4. **网络环境**：某些地区可能需要VPN才能访问YouTube

## 相关链接

- [yt-dlp Cookie文档](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [导出YouTube Cookie](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)

