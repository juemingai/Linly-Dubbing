from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from urllib.parse import urlparse

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
    cookie_file = os.getenv('YTDLP_COOKIES_FILE', 'cookies.txt')
    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file

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

    return opts


def _build_format_candidates(resolution: str):
    return [
        f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]",
        'bestvideo+bestaudio/best',
        'best'
    ]


def _locate_download_file(folder_path: str):
    desired = os.path.join(folder_path, 'download.mp4')
    if os.path.exists(desired):
        return desired

    candidates = []
    for name in os.listdir(folder_path):
        if not name.startswith('download'):
            continue
        if name.endswith(('.info.json', '.json', '.jpg', '.png', '.webp')):
            continue
        if name.endswith('.part'):
            continue
        path = os.path.join(folder_path, name)
        if os.path.isfile(path):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(key=os.path.getmtime)
    latest = candidates[-1]
    if latest.endswith('.mp4'):
        os.replace(latest, desired)
    else:
        shutil.move(latest, desired)
    return desired


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

    output_folder = os.path.join(folder_path, uploader, f'{upload_date} {title}')
    os.makedirs(output_folder, exist_ok=True)

    if os.path.exists(os.path.join(output_folder, 'download.mp4')):
        logger.info(f'Video already downloaded in {output_folder}')
        return output_folder

    numeric_resolution = re.sub(r'[^0-9]', '', str(resolution)) or '1080'
    format_candidates = _build_format_candidates(numeric_resolution)

    base_opts = _common_ydl_opts(video_url, noplaylist=True)
    base_opts.update({
        'writeinfojson': True,
        'writethumbnail': True,
        'outtmpl': os.path.join(output_folder, 'download.%(ext)s')
    })

    last_error = None
    for selector in format_candidates:
        ydl_opts = dict(base_opts)
        ydl_opts['format'] = selector
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            downloaded = _locate_download_file(output_folder)
            if not downloaded:
                raise FileNotFoundError('未找到下载后的文件，请检查 yt-dlp 输出。')
            logger.info(f'Video downloaded in {output_folder} using format {selector}')
            return output_folder
        except Exception as exc:
            last_error = exc
            logger.warning(
                'yt-dlp 下载失败，尝试下一种格式',
                selector=selector,
                error=str(exc)
            )

    error_msg = str(last_error) if last_error else '未知原因'
    raise RuntimeError(
        '无法下载视频，请确认链接可访问并已配置 Cookies。'
        f' 最后错误: {error_msg}'
    )

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
                continue

        if not result:
            logger.warning('未从链接获取到任何视频信息', url=single_url)
            continue

        if 'entries' in result and result['entries'] is not None:
            for video_info in result['entries']:
                if video_info is None:
                    logger.warning('播放列表中的某些视频需要登录才能访问', url=single_url)
                    continue
                yield video_info
        else:
            yield result

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
