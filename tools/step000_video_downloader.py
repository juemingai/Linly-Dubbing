import os
import re
from loguru import logger
import yt_dlp
import json

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
    
    # 检查是否有webpage_url
    if 'webpage_url' not in info or not info.get('webpage_url'):
        logger.error('视频信息缺少webpage_url，无法下载')
        return None
    
    ydl_opts = {
        # 'res': '1080',
        'format': f'bestvideo[ext=mp4][height<={resolution}]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'writeinfojson': True,
        'writethumbnail': True,
        'outtmpl': os.path.join(folder_path, sanitized_uploader, f'{upload_date} {sanitized_title}', 'download'),
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt' if os.path.exists("cookies.txt") else None,  # 得到cookies yt-dlp --cookies-from-browser chrome --cookies cookies.txt
        # 'cookiesfrombrowser': ('chrome', ), # 从chrome浏览器中获取cookie 
        # 'cookiesfrombrowser': ('firefox', 'default', None, 'Meta') # 从firefox浏览器中获取cookie
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([info['webpage_url']])
        logger.info(f'Video downloaded in {output_folder}')
        return output_folder
    except Exception as e:
        logger.error(f'下载视频失败: {info.get("title", "Unknown")}, 错误: {e}')
        if 'Sign in' in str(e) or 'bot' in str(e) or 'cookies' in str(e).lower():
            logger.error('YouTube要求Cookie验证，请配置cookies.txt文件或使用浏览器Cookie')
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

def get_info_list_from_url(url, num_videos):
    if isinstance(url, str):
        url = [url]

    # Download JSON information first
    ydl_opts = {
        # 'format': 'b',
        'None': "b",
        'dumpjson': True,
        'playlistend': num_videos,
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt' if os.path.exists("cookies.txt") else None,  # 添加Cookie支持
    }

    # video_info_list = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for u in url:
            try:
                result = ydl.extract_info(u, download=False)
                if result is None:
                    logger.warning(f'无法获取视频信息: {u}，可能需要Cookie验证')
                    continue
                
                if 'entries' in result and result['entries']:
                    # Playlist
                    for video_info in result['entries']:
                        if video_info is not None:  # 过滤None值
                            yield video_info
                        else:
                            logger.warning('播放列表中的某个视频信息为None，已跳过')
                elif result:
                    # Single video
                    yield result
                else:
                    logger.warning(f'获取的视频信息为空: {u}')
            except Exception as e:
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
