from __future__ import annotations

import mimetypes
import os
import re
import shutil
import tempfile
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from loguru import logger
import yt_dlp
from yt_dlp.utils import DownloadError
import json

DEFAULT_USER_AGENT = os.getenv(
    'YTDLP_USER_AGENT',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)


def _build_http_headers(url: str | None):
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }
    if not url:
        return headers

    parsed = urlparse(url)
    netloc = (parsed.netloc or '').lower()
    if 'bilibili.com' in netloc:
        headers['Referer'] = 'https://www.bilibili.com/'
        headers['Origin'] = 'https://www.bilibili.com'
    elif parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers.setdefault('Referer', f'{origin}/')
        headers.setdefault('Origin', origin)
    return headers


def _apply_cookie_options(opts: dict):
    """应用Cookie配置选项"""
    cookie_file = os.getenv('YTDLP_COOKIES_FILE', 'cookies.txt')
    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file
        logger.info(f'使用Cookie文件: {cookie_file}')
    elif cookie_file:
        logger.warning(f'Cookie文件不存在: {cookie_file}')

    browser = os.getenv('YTDLP_COOKIES_BROWSER')
    if browser:
        profile = os.getenv('YTDLP_COOKIES_PROFILE')
        keyring = os.getenv('YTDLP_COOKIES_KEYRING')
        container = os.getenv('YTDLP_COOKIES_CONTAINER')
        cookies_args = [browser]
        if profile or keyring or container:
            cookies_args.append(profile)
        if keyring or container:
            if len(cookies_args) < 2:
                cookies_args.append(None)
            cookies_args.append(keyring)
        if container:
            while len(cookies_args) < 3:
                cookies_args.append(None)
            cookies_args.append(container)
        opts['cookiesfrombrowser'] = tuple(cookies_args)
        logger.info(f'从浏览器提取Cookie: {browser}')

    return opts


def _build_format_candidates(resolution: str):
    return [
        f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]",
        'bestvideo+bestaudio/best',
        'best'
    ]


def _common_ydl_opts(url: str, noplaylist: bool = True):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': noplaylist,
        'retries': 5,
        'fragment_retries': 10,
        'continuedl': True,
        'merge_output_format': 'mp4',
        'http_headers': _build_http_headers(url),
        'geo_bypass': True
    }
    return _apply_cookie_options(opts)


def _extract_info(single_url: str, noplaylist: bool, playlistend: int | None = None):
    ydl_opts = _common_ydl_opts(single_url, noplaylist=noplaylist)
    ydl_opts['ignoreerrors'] = True
    if not noplaylist and playlistend:
        ydl_opts['playlistend'] = playlistend
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(single_url, download=False)


def _normalize_video_url(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if parsed.path in {'/watch', '/watch/'} and 'v' in query:
        normalized = parsed._replace(query=urlencode({'v': query['v']}))
        return urlunparse(normalized)
    if 'list' in query:
        query.pop('list', None)
        query.pop('index', None)
        normalized = parsed._replace(query=urlencode(query))
        return urlunparse(normalized)
    return url


def _placeholder_info(url: str):
    cleaned_url = _normalize_video_url(url)
    parsed = urlparse(cleaned_url)
    query = dict(parse_qsl(parsed.query))
    fallback_title = query.get('v') or parsed.path.strip('/').split('/')[-1] or 'download'
    return {
        'webpage_url': cleaned_url,
        'title': fallback_title,
        'uploader': 'UnknownUploader',
        'upload_date': datetime.utcnow().strftime('%Y%m%d')
    }


def _guess_extension(content_type: str | None, url: str) -> str:
    if content_type:
        mime = content_type.split(';')[0].strip()
        ext = mimetypes.guess_extension(mime)
        if ext:
            return ext
    suffix = os.path.splitext(url.split('?')[0])[1]
    return suffix or '.mp4'


def _validate_video_file(file_path: str) -> bool:
    """验证下载的文件是否是有效的视频文件"""
    if not os.path.exists(file_path):
        return False
    
    # 检查文件大小（至少应该大于1KB）
    if os.path.getsize(file_path) < 1024:
        return False
    
    # 检查文件扩展名
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp4', '.webm', '.mkv', '.flv', '.avi', '.mov', '.m4v']:
        # 如果扩展名不对，尝试检查文件头
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
                # 检查是否是HTML文件（通常以<!DOCTYPE或<html开头）
                if header.startswith(b'<!DOCTYPE') or header.startswith(b'<html') or header.startswith(b'<!doctype'):
                    logger.warning(f'下载的文件是HTML而不是视频: {file_path}')
                    return False
                # 检查是否是MP4文件（ftyp box）
                if b'ftyp' in header or b'moov' in header or b'mdat' in header:
                    return True
        except Exception as e:
            logger.warning(f'验证文件时出错: {e}')
            return False
    
    return True


def _direct_http_download(url: str, headers: dict):
    """直接HTTP下载（仅用于非YouTube/Bilibili的直接视频链接）"""
    parsed = urlparse(url)
    netloc = (parsed.netloc or '').lower()
    
    # YouTube和Bilibili不能直接HTTP下载
    if 'youtube.com' in netloc or 'youtu.be' in netloc or 'bilibili.com' in netloc:
        raise RuntimeError(
            'YouTube和Bilibili视频无法直接HTTP下载，需要配置Cookie。'
            '请设置环境变量 YTDLP_COOKIES_FILE 或 YTDLP_COOKIES_BROWSER。'
            '详情请参考: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
        )
    
    logger.info('使用直接下载尝试获取媒体', url=url)
    response = requests.get(url, stream=True, timeout=60, headers=headers)
    response.raise_for_status()
    temp_dir = tempfile.mkdtemp(prefix='yt_tmp_')
    ext = _guess_extension(response.headers.get('content-type'), url)
    file_path = os.path.join(temp_dir, f'download_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}{ext}')
    with open(file_path, 'wb') as fp:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                fp.write(chunk)
    
    # 验证下载的文件
    if not _validate_video_file(file_path):
        os.remove(file_path)
        raise RuntimeError(f'直接下载的文件无效或损坏: {url}')
    
    return file_path, temp_dir


def _pick_temp_file(temp_dir: str):
    candidates = []
    for name in os.listdir(temp_dir):
        if name.endswith(('.info.json', '.json', '.jpg', '.png', '.webp', '.part')):
            continue
        path = os.path.join(temp_dir, name)
        if os.path.isfile(path):
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=os.path.getmtime)
    return candidates[-1]


def _download_with_temp_dir(video_url: str, numeric_resolution: str):
    temp_dir = tempfile.mkdtemp(prefix='yt_tmp_')
    headers = _build_http_headers(video_url)
    format_candidates = _build_format_candidates(numeric_resolution)
    last_error = None
    cookie_required = False
    
    try:
        for selector in format_candidates:
            opts = _common_ydl_opts(video_url, noplaylist=True)
            opts.update({
                'format': selector,
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'add_metadata': True,
                'writethumbnail': False,
                'http_headers': headers
            })
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(video_url, download=True)
                downloaded = _pick_temp_file(temp_dir)
                if not downloaded:
                    raise FileNotFoundError('未找到下载的媒体文件')
                
                # 验证下载的文件
                if not _validate_video_file(downloaded):
                    raise RuntimeError('下载的文件无效或损坏')
                
                return downloaded, temp_dir
            except DownloadError as exc:
                error_str = str(exc).lower()
                if 'sign in' in error_str or 'bot' in error_str or 'cookies' in error_str:
                    cookie_required = True
                last_error = exc
                logger.warning('yt-dlp 下载失败，尝试下一种格式', selector=selector, error=str(exc))
                continue
            except Exception as exc:
                last_error = exc
                logger.warning('yt-dlp 下载失败，尝试下一种格式', selector=selector, error=str(exc))
                continue

        # 如果所有格式都失败，检查是否需要Cookie
        if cookie_required:
            cookie_file = os.getenv('YTDLP_COOKIES_FILE', 'cookies.txt')
            browser = os.getenv('YTDLP_COOKIES_BROWSER')
            error_msg = (
                'YouTube要求登录验证才能下载此视频。\n'
                '解决方案：\n'
                '1. 设置环境变量 YTDLP_COOKIES_FILE 指向Cookie文件路径\n'
                '   例如: export YTDLP_COOKIES_FILE="/path/to/cookies.txt"\n'
                '2. 或者设置 YTDLP_COOKIES_BROWSER 从浏览器提取Cookie\n'
                '   例如: export YTDLP_COOKIES_BROWSER="chrome"\n'
                '3. 导出Cookie的方法：\n'
                '   yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com/watch?v=xxxx"\n'
                f'当前配置: YTDLP_COOKIES_FILE={cookie_file}, YTDLP_COOKIES_BROWSER={browser}'
            )
            raise RuntimeError(error_msg)
        
        # 对于非YouTube/Bilibili，尝试直接下载
        parsed = urlparse(video_url)
        netloc = (parsed.netloc or '').lower()
        if 'youtube.com' not in netloc and 'youtu.be' not in netloc and 'bilibili.com' not in netloc:
            logger.info('所有格式下载失败，尝试直接下载', last_error=str(last_error) if last_error else None)
            return _direct_http_download(video_url, headers)
        else:
            raise RuntimeError(
                f'所有下载方式都失败。最后错误: {last_error}\n'
                '如果是YouTube/Bilibili视频，请配置Cookie。'
            )
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise exc

def sanitize_title(title):
    if title is None:
        title = ''
    title = str(title)
    title = re.sub(r'[^\w\u4e00-\u9fff \d_-]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title or 'Unknown'


def _ensure_metadata(info):
    if not info:
        raise ValueError('未获取到视频信息，请确认链接可访问并已配置 Cookies。')

    title = sanitize_title(info.get('title') or info.get('id') or 'download')
    uploader = sanitize_title(info.get('uploader') or 'UnknownUploader')

    upload_date = info.get('upload_date') or info.get('release_date')
    if not upload_date and info.get('timestamp'):
        upload_date = datetime.utcfromtimestamp(info['timestamp']).strftime('%Y%m%d')
    upload_date = str(upload_date or 'UnknownDate')

    return title, uploader, upload_date


def get_target_folder(info, folder_path):
    title, uploader, upload_date = _ensure_metadata(info)
    return os.path.join(folder_path, uploader, f'{upload_date} {title}')

def download_single_video(info, folder_path, resolution='1080p'):
    title, uploader, upload_date = _ensure_metadata(info)
    video_url = info.get('webpage_url') or info.get('url')
    if not video_url:
        raise ValueError('视频信息缺少 webpage_url，无法下载。')
    video_url = _normalize_video_url(video_url)

    output_folder = os.path.join(folder_path, uploader, f'{upload_date} {title}')
    os.makedirs(output_folder, exist_ok=True)

    download_path = os.path.join(output_folder, 'download.mp4')
    if os.path.exists(download_path):
        # 验证已存在的文件是否有效
        if _validate_video_file(download_path):
            logger.info(f'Video already downloaded in {output_folder}')
            return output_folder
        else:
            logger.warning(f'已存在的视频文件损坏，将重新下载: {download_path}')
            os.remove(download_path)

    numeric_resolution = re.sub(r'[^0-9]', '', str(resolution)) or '1080'
    try:
        temp_file, temp_dir = _download_with_temp_dir(video_url, numeric_resolution)
        
        # 再次验证下载的文件
        if not _validate_video_file(temp_file):
            raise RuntimeError('下载的文件验证失败，可能已损坏')
        
        final_path = os.path.join(output_folder, 'download.mp4')
        suffix = os.path.splitext(temp_file)[1] or '.mp4'
        if suffix != '.mp4':
            final_path = os.path.join(output_folder, f'download{suffix}')
        shutil.move(temp_file, final_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 最终验证
        if not _validate_video_file(final_path):
            raise RuntimeError('下载的文件验证失败')
        
        if final_path.endswith('.mp4'):
            return output_folder
        # rename non-mp4 into mp4 for downstream steps
        target_mp4 = os.path.join(output_folder, 'download.mp4')
        os.replace(final_path, target_mp4)
        return output_folder
    except Exception as exc:
        raise RuntimeError(
            '无法下载视频，请确认链接可访问并已配置 Cookies。'
            f' 最后错误: {exc}'
        ) from exc

def download_videos(info_list, folder_path, resolution='1080p'):
    output_folder = None
    for info in info_list:
        if info is None:
            logger.warning('跳过空的视频信息，请确认已配置 Cookies或者链接有效。')
            continue
        output_folder = download_single_video(info, folder_path, resolution)
    return output_folder

def get_info_list_from_url(url, num_videos):
    urls = [url] if isinstance(url, str) else url

    for single_url in urls:
        yielded = False
        result = None
        try:
            result = _extract_info(single_url, noplaylist=False, playlistend=num_videos)
        except DownloadError as exc:
            logger.warning(
                '获取播放列表信息失败，尝试单视频模式',
                url=single_url,
                error=str(exc)
            )
            try:
                result = _extract_info(single_url, noplaylist=True)
            except DownloadError as single_exc:
                logger.error(
                    '单视频模式仍无法获取信息，请检查Cookies或账号是否登录',
                    url=single_url,
                    error=str(single_exc)
                )
                result = None

        if result:
            if 'entries' in result and result['entries'] is not None:
                for video_info in result['entries']:
                    if video_info is None:
                        logger.warning('播放列表中的某些视频需要登录才能访问', url=single_url)
                        continue
                    yielded = True
                    yield video_info
            else:
                yielded = True
                yield result

        if not yielded:
            logger.warning('无法获取播放列表条目，改用单个视频链接继续下载', url=single_url)
            yield _placeholder_info(single_url)

    # return video_info_list

def download_from_url(url, folder_path, resolution='1080p', num_videos=5):
    info_list = list(get_info_list_from_url(url, num_videos))
    if not info_list:
        raise RuntimeError('未获取到可下载的视频，请检查链接或登录态。')

    example_output_folder = download_videos(info_list, folder_path, resolution)
    if not example_output_folder:
        raise RuntimeError('下载失败，未成功保存任何视频。')

    download_info_json = None
    info_json_path = os.path.join(example_output_folder, 'download.info.json')
    if info_json_path and os.path.exists(info_json_path):
        with open(info_json_path, 'r', encoding='utf-8') as fp:
            download_info_json = json.load(fp)
    return (
        f"All videos have been downloaded under the {folder_path} folder",
        os.path.join(example_output_folder, 'download.mp4') if example_output_folder else None,
        download_info_json
    )

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
