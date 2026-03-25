import os
import re
from loguru import logger
import yt_dlp
import json
from urllib.parse import urlparse, parse_qs

def _ensure_deno_in_path():
    """确保 deno 在 PATH 中，供 yt-dlp 解 YouTube n-challenge"""
    import shutil
    if shutil.which('deno'):
        return
    candidate_dirs = [
        os.path.expanduser('~/.deno/bin'),
        '/usr/local/bin',
        '/usr/bin',
        '/opt/conda/bin',
        os.path.expanduser('~/bin'),
    ]
    for d in candidate_dirs:
        if os.path.exists(os.path.join(d, 'deno')):
            os.environ['PATH'] = d + ':' + os.environ.get('PATH', '')
            logger.info(f'已将 deno 路径注入 PATH: {d}/deno')
            return
    logger.warning('未找到 deno，n-challenge 解密可能失败；请确认 deno 已安装')


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
    
    import shutil
    import tempfile
    import glob

    # 确保 deno 在 PATH 中
    _ensure_deno_in_path()

    cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
    use_cookie = os.path.exists(cookie_file)
    temp_cookie_path = None

    if use_cookie:
        temp_cookie = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_cookie_path = temp_cookie.name
        temp_cookie.close()
        shutil.copy(cookie_file, temp_cookie_path)
        logger.info(f'download_single_video: 使用 cookies.txt（{os.path.getsize(cookie_file)} 字节）')
    else:
        logger.warning(f'download_single_video: 未找到 cookies.txt')

    last_error = None
    for selector in format_candidates:
        ydl_opts = {
            'format': selector,
            'outtmpl': os.path.join(folder_path, sanitized_uploader, f'{upload_date} {sanitized_title}', 'download'),
            'merge_output_format': 'mp4',
            'writeinfojson': True,
            'writethumbnail': True,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'noplaylist': True,
            'retries': 5,
            'fragment_retries': 10,
            'continuedl': True,
            'cookiefile': temp_cookie_path if use_cookie else None,
            'remote_components': ['ejs:github'],  # 从 GitHub 下载最新 n-challenge solver
        }
        try:
            logger.info(f'尝试格式: {selector}')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            download_path = os.path.join(output_folder, 'download.mp4')
            if os.path.exists(download_path):
                logger.info(f'下载成功: {output_folder}')
                if temp_cookie_path and os.path.exists(temp_cookie_path):
                    os.remove(temp_cookie_path)
                return output_folder

            possible_files = glob.glob(os.path.join(output_folder, 'download*'))
            video_files = [f for f in possible_files if not f.endswith(('.info.json', '.webp', '.jpg', '.png'))]
            if video_files:
                source_file = video_files[0]
                if source_file != download_path:
                    os.rename(source_file, download_path)
                logger.info(f'下载成功: {output_folder}')
                if temp_cookie_path and os.path.exists(temp_cookie_path):
                    os.remove(temp_cookie_path)
                return output_folder

            logger.warning(f'格式 {selector} 未找到视频文件，尝试下一格式')
        except Exception as e:
            last_error = e
            logger.warning(f'格式 {selector} 失败: {e}，尝试下一格式')

    if temp_cookie_path and os.path.exists(temp_cookie_path):
        os.remove(temp_cookie_path)
    logger.error(f'所有格式下载失败: {info.get("title", "Unknown")}，最后错误: {last_error}')
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
    import shutil
    import tempfile

    # 确保 deno 在 PATH 中（CLI 能用 deno 解 n-challenge，Python 进程 PATH 可能不同）
    _ensure_deno_in_path()

    if isinstance(url, str):
        url = [url]

    normalized_urls = []
    for u in url:
        normalized = _normalize_youtube_url(u)
        normalized_urls.append(normalized)
        if normalized != u:
            logger.info(f'规范化URL: {u} -> {normalized}')

    try:
        logger.info(f'yt-dlp 版本: {yt_dlp.version.__version__}')
    except Exception as e:
        logger.warning(f'无法获取 yt-dlp 版本: {str(e)}')

    cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
    temp_cookie_path = None

    ydl_opts = {
        'playlistend': num_videos,
        'ignoreerrors': True,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'remote_components': ['ejs:github'],  # 从 GitHub 下载最新 n-challenge solver
    }

    if os.path.exists(cookie_file):
        temp_cookie = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_cookie_path = temp_cookie.name
        temp_cookie.close()
        shutil.copy(cookie_file, temp_cookie_path)
        ydl_opts['cookiefile'] = temp_cookie_path
        logger.info(f'使用 cookies.txt（{os.path.getsize(cookie_file)} 字节）')
    else:
        logger.warning(f'未找到 cookies.txt，路径: {cookie_file}')

    logger.info(f'ydl_opts: {ydl_opts}')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for u in normalized_urls:
                try:
                    result = ydl.extract_info(u, download=False)
                    if result is None:
                        logger.warning(f'无法获取视频信息: {u}')
                        continue
                    if isinstance(result, dict) and result.get('title') and result.get('webpage_url'):
                        yield result
                    else:
                        logger.warning(f'视频信息格式异常: {u}')
                except Exception as e:
                    logger.error(f'获取视频信息失败: {u}, 错误: {e}')
    finally:
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)

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
