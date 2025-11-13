import os
import re
from loguru import logger
import yt_dlp
import json
from urllib.parse import urlparse, parse_qs

def sanitize_title(title):
    # Only keep numbers, letters, Chinese characters, and spaces
    title = re.sub(r'[^\w\u4e00-\u9fff \d_-]', '', title)
    # Replace multiple spaces with a single space
    title = re.sub(r'\s+', ' ', title)
    return title


def get_target_folder(info, folder_path):
    if info is None:
        logger.error('视频信息为None，无法获取目标文件夹')
        return None
    
    if 'title' not in info or not info.get('title'):
        logger.error('视频信息缺少title字段')
        return None
    
    sanitized_title = sanitize_title(info['title'])
    sanitized_uploader = sanitize_title(info.get('uploader', 'Unknown'))
    upload_date = info.get('upload_date', 'Unknown')
    if upload_date == 'Unknown':
        return None

    output_folder = os.path.join(
        folder_path, sanitized_uploader, f'{upload_date} {sanitized_title}')

    return output_folder

def download_single_video(info, folder_path, resolution='1080p'):
    if info is None:
        logger.error('视频信息为None，无法下载')
        return None
    
    if 'title' not in info or not info.get('title'):
        logger.error('视频信息缺少title字段，无法下载')
        return None
    
    sanitized_title = sanitize_title(info['title'])
    sanitized_uploader = sanitize_title(info.get('uploader', 'Unknown'))
    upload_date = info.get('upload_date', 'Unknown')
    if upload_date == 'Unknown':
        logger.warning('视频信息缺少upload_date，无法下载')
        return None
    
    output_folder = os.path.join(folder_path, sanitized_uploader, f'{upload_date} {sanitized_title}')
    if os.path.exists(os.path.join(output_folder, 'download.mp4')):
        logger.info(f'Video already downloaded in {output_folder}')
        return output_folder
    
    resolution = resolution.replace('p', '')
    numeric_resolution = re.sub(r'[^0-9]', '', str(resolution)) or '1080'
    
    # 检查是否有webpage_url
    if 'webpage_url' not in info or not info.get('webpage_url'):
        logger.error('视频信息缺少webpage_url，无法下载')
        return None
    
    video_url = info['webpage_url']
    # 规范化URL，确保只下载单个视频
    video_url = _normalize_youtube_url(video_url)
    
    # 参考实现：使用多个格式候选，逐个尝试
    format_candidates = [
        f'bestvideo[height<={numeric_resolution}]+bestaudio/best[height<={numeric_resolution}]',
        'bestvideo+bestaudio/best',
        'best'
    ]
    
    # 检查 cookies.txt 文件（使用绝对路径）
    cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
    use_cookie = os.path.exists(cookie_file)
    if use_cookie:
        logger.info(f'download_single_video: 检测到 cookies.txt，路径: {cookie_file}')
        file_size = os.path.getsize(cookie_file)
        logger.info(f'download_single_video: cookies.txt 文件大小: {file_size} 字节')
    else:
        logger.warning(f'download_single_video: 未找到 cookies.txt，路径: {cookie_file}')

    last_error = None
    for selector in format_candidates:
        ydl_opts = {
            'format': selector,
            'outtmpl': os.path.join(folder_path, sanitized_uploader, f'{upload_date} {sanitized_title}', 'download'),
            'merge_output_format': 'mp4',
            'writeinfojson': True,
            'writethumbnail': True,
            'quiet': False,  # 显示详细错误
            'no_warnings': False,  # 显示警告信息
            'ignoreerrors': True,
            'noplaylist': True,  # 强制只下载单个视频
            'retries': 5,
            'fragment_retries': 10,
            'continuedl': True,
            'cookiefile': cookie_file if use_cookie else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],  # 尝试使用 Android 和 Web 客户端
                    'player_skip': ['webpage', 'configs'],  # 跳过某些检查
                }
            },
        }

        logger.debug(f'ydl_opts cookiefile配置: {ydl_opts.get("cookiefile")}')

        try:
            logger.debug(f'尝试使用格式下载: {selector}')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # 检查文件是否下载成功
            download_path = os.path.join(output_folder, 'download.mp4')
            if os.path.exists(download_path):
                logger.info(f'Video downloaded in {output_folder}')
                return output_folder
            else:
                # 尝试查找其他格式的文件
                for ext in ['.mp4', '.webm', '.mkv']:
                    alt_path = os.path.join(output_folder, f'download{ext}')
                    if os.path.exists(alt_path):
                        # 重命名为mp4
                        os.rename(alt_path, download_path)
                        logger.info(f'Video downloaded in {output_folder}')
                        return output_folder
                raise FileNotFoundError('下载的文件未找到')
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            if 'sign in' in error_str or 'bot' in error_str or 'cookies' in error_str:
                logger.error(f'下载视频失败: {info.get("title", "Unknown")}, YouTube要求Cookie验证')
                logger.error('请配置cookies.txt文件或使用浏览器Cookie')
                return None
            logger.warning(f'格式 {selector} 下载失败，尝试下一种格式: {e}')
            continue
    
    # 所有格式都失败
    logger.error(f'所有格式下载都失败: {info.get("title", "Unknown")}, 最后错误: {last_error}')
    return None

def download_videos(info_list, folder_path, resolution='1080p'):
    output_folder = None
    for info in info_list:
        if info is None:
            logger.warning('跳过空的视频信息')
            continue
        output_folder = download_single_video(info, folder_path, resolution)
        if output_folder is None:
            logger.warning(f'下载视频失败: {info.get("title", "Unknown") if info else "Unknown"}')
    return output_folder

def _normalize_youtube_url(url: str) -> str:
    """从YouTube URL中提取单个视频ID，忽略播放列表参数"""
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        query = parse_qs(parsed.query)
        if 'v' in query:
            # 提取视频ID，忽略list和index参数
            video_id = query['v'][0]
            return f'https://www.youtube.com/watch?v={video_id}'
        elif 'youtu.be' in parsed.netloc:
            # 短链接格式
            video_id = parsed.path.lstrip('/')
            return f'https://www.youtube.com/watch?v={video_id}'
    return url


def get_info_list_from_url(url, num_videos):
    if isinstance(url, str):
        url = [url]

    # 规范化URL，提取单个视频ID
    normalized_urls = []
    for u in url:
        normalized = _normalize_youtube_url(u)
        normalized_urls.append(normalized)
        if normalized != u:
            logger.info(f'规范化URL: {u} -> {normalized}')

    # Download JSON information first
    ydl_opts = {
        'dumpjson': True,
        'playlistend': num_videos,
        'ignoreerrors': True,
        'noplaylist': True,  # 强制只下载单个视频，忽略播放列表
        'quiet': False,  # 改为 False 显示详细错误
        'no_warnings': False,  # 改为 False 显示警告信息
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],  # 尝试使用 Android 和 Web 客户端
                'player_skip': ['webpage', 'configs'],  # 跳过某些检查
            }
        },
    }

    # 添加cookie支持（使用绝对路径）
    cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        logger.info(f'get_info_list_from_url: 使用 cookies.txt 进行 YouTube 验证，路径: {cookie_file}')
        # 检查文件大小
        file_size = os.path.getsize(cookie_file)
        logger.info(f'cookies.txt 文件大小: {file_size} 字节')

        # 读取并验证 cookie 文件格式
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]  # 读取前10行
                logger.info(f'cookies.txt 前3行内容:')
                for i, line in enumerate(lines[:3]):
                    # 显示制表符（\t）和换行符
                    display_line = repr(line[:100])
                    logger.info(f'  行{i+1}: {display_line}')

                # 统计有效的 cookie 行（非注释、非空行）
                valid_cookies = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                logger.info(f'cookies.txt 有效cookie行数: {len(valid_cookies)} (前10行中)')
        except Exception as e:
            logger.error(f'读取 cookies.txt 内容失败: {str(e)}')
    else:
        logger.warning(f'get_info_list_from_url: 未找到 cookies.txt，路径: {cookie_file}')

    # video_info_list = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for u in normalized_urls:
            try:
                result = ydl.extract_info(u, download=False)
                if result is None:
                    logger.warning(f'无法获取视频信息: {u}，可能需要Cookie验证')
                    continue

                # 由于使用了noplaylist=True，result应该是单个视频，不会是播放列表
                if result and isinstance(result, dict):
                    # 确保有必需的字段
                    if 'title' in result and 'webpage_url' in result:
                        yield result
                    else:
                        logger.warning(f'视频信息缺少必需字段: {u}')
                else:
                    logger.warning(f'获取的视频信息为空或格式错误: {u}')
            except Exception as e:
                error_str = str(e).lower()
                if 'sign in' in error_str or 'bot' in error_str or 'cookies' in error_str:
                    logger.error(f'获取视频信息失败: {u}, YouTube要求Cookie验证')
                else:
                    logger.error(f'获取视频信息失败: {u}, 错误: {e}')
                continue

    # return video_info_list

def download_from_url(url, folder_path, resolution='1080p', num_videos=5):
    resolution = resolution.replace('p', '')
    if isinstance(url, str):
        url = [url]

    # Download JSON information first
    ydl_opts = {
        # 'format': 'b',
        "None":"b",
        'dumpjson': True,
        'playlistend': num_videos,
        'ignoreerrors': True,
        'cookies-from-browser': 'chrome'
    }

    video_info_list = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for u in url:
            result = ydl.extract_info(u, download=False)
            # print(result)
       

            if 'entries' in result:
                # Playlist
                video_info_list.extend(result['entries'])
            else:
                # Single video
                video_info_list.append(result)
        
    # Now download videos with sanitized titles
    example_output_folder = download_videos(video_info_list, folder_path, resolution)
    if os.path.exists(os.path.join(example_output_folder, 'download.info.json')):
        download_info_json = json.load(open(os.path.join(example_output_folder, 'download.info.json'), 'r', encoding='utf-8'))
    return f"All videos have been downloaded under the {folder_path} folder", os.path.join(example_output_folder, 'download.mp4'), download_info_json

if __name__ == '__main__':
    # Example usage
    # Youtube Title: How to Install and Use yt-dlp [2024] [Quick and Easy!] [4 Minute Tutorial] [Windows 11]
    url = 'https://www.youtube.com/watch?v=5aYwU4nj5QA'
    # Bilibili Title 高清无字幕 | 英语听力 | Taylor Swift纽约大学2022届毕业典礼演讲 | Commencement Speech at NYU
    url = 'https://www.bilibili.com/video/BV1KZ4y1h7ke/'
    # Bilbili Title 奥巴马开学演讲，纯英文字幕
    url = 'https://www.bilibili.com/video/BV1Tt411P72Q/'
    # Playlist
    # Bilibili 【TED演讲/Ed合集】精选50篇-对应文稿第1-50篇【无字幕】
    # url = 'https://www.bilibili.com/video/BV1YQ4y1371P/'
    url = 'https://www.bilibili.com/video/BV1kr421M7vz/' # (英文无字幕) 阿里这小子在水城威尼斯发来问候
    folder_path = 'videos'
    os.makedirs(folder_path, exist_ok=True)
    download_from_url(url, folder_path)
