import gradio as gr
from tools.step000_video_downloader import download_from_url
from tools.step010_demucs_vr import separate_all_audio_under_folder
from tools.step020_asr import transcribe_all_audio_under_folder
from tools.step030_translation import translate_all_transcript_under_folder
from tools.step040_tts import generate_all_wavs_under_folder
from tools.step050_synthesize_video import synthesize_all_video_under_folder
from tools.do_everything import do_everything
import threading
import queue
import time
from tools.utils import SUPPORT_VOICE

# 获取可用的TTS方法
def get_available_tts_methods():
    try:
        from tools.step040_tts import F5TTS_AVAILABLE, MINIMAX_AVAILABLE
        base_methods = ['xtts', 'cosyvoice', 'EdgeTTS']
        if F5TTS_AVAILABLE:
            base_methods.append('f5tts')
        if MINIMAX_AVAILABLE:
            base_methods.append('minimax')
        return base_methods
    except:
        return ['xtts', 'cosyvoice', 'EdgeTTS']

# 获取所有支持的语言（包含F5-TTS的语言）
def get_all_supported_languages():
    try:
        from tools.step040_tts import F5TTS_AVAILABLE
        base_langs = ['中文', 'English', '粤语', 'Japanese', 'Korean', 'Spanish', 'French']
        if F5TTS_AVAILABLE:
            # 添加F5-TTS额外支持的语言
            extra_langs = ['German', 'Italian', 'Portuguese', 'Polish', 'Turkish', 'Russian', 'Dutch', 'Czech', 'Arabic', 'Hungarian', 'Hindi']
            return base_langs + extra_langs
        return base_langs
    except:
        return ['中文', 'English', '粤语', 'Japanese', 'Korean', 'Spanish', 'French']

available_tts_methods = get_available_tts_methods()
all_supported_languages = get_all_supported_languages()

def do_everything_with_timeout(*args, timeout=300, **kwargs):
    """
    带超时的do_everything包装函数，避免界面卡死
    """
    result_queue = queue.Queue()
    exception_queue = queue.Queue()
    
    def target():
        try:
            result = do_everything(*args, **kwargs)
            result_queue.put(result)
        except Exception as e:
            exception_queue.put(e)
    
    # 启动线程
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    
    # 等待结果或超时
    thread.join(timeout)
    
    if thread.is_alive():
        # 超时情况
        return "处理超时，请检查系统资源或重试", None
    
    # 检查是否有异常
    if not exception_queue.empty():
        e = exception_queue.get()
        return f"处理失败: {str(e)}", None
    
    # 检查是否有结果
    if not result_queue.empty():
        return result_queue.get()
    else:
        return "处理完成但未返回结果", None

# 包装一键自动化函数以支持 Minimax voice_id
def do_everything_with_minimax(*args, **kwargs):
    """一键自动化包装函数，支持Minimax音色ID"""
    # 从参数中提取minimax_voice_id（倒数第二个参数）
    args_list = list(args)
    minimax_voice_id = args_list[-1] if len(args_list) > 0 else ''
    
    # 移除minimax_voice_id参数，保持原有参数数量
    args_without_voice_id = args_list[:-1]
    
    # 如果选择了minimax方法且提供了voice_id，添加到kwargs
    if len(args_without_voice_id) >= 15:  # 确保有足够的参数
        tts_method = args_without_voice_id[14]  # TTS方法参数位置
        if tts_method == 'minimax' and minimax_voice_id.strip():
            kwargs['voice_id'] = minimax_voice_id.strip()
    
    return do_everything_with_timeout(*args_without_voice_id, **kwargs)

# 一键自动化界面
full_auto_interface = gr.Interface(
    fn=do_everything_with_minimax,
    inputs=[
        gr.Textbox(label='视频输出文件夹', value='videos'),
        gr.Textbox(label='视频URL', placeholder='请输入Youtube或Bilibili的视频、播放列表或频道的URL', 
                   value='https://www.bilibili.com/video/BV1kr421M7vz/'),
        gr.Slider(minimum=1, maximum=100, step=1, label='下载视频数量', value=5),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='分辨率', value='1080p'),

        gr.Radio(['htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'hdemucs_mmi', 'mdx', 'mdx_extra', 'mdx_q', 'mdx_extra_q', 'SIG'], label='模型', value='htdemucs_ft'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='计算设备', value='auto'),
        gr.Slider(minimum=0, maximum=10, step=1, label='移位次数 Number of shifts', value=5),

        gr.Dropdown(['WhisperX', 'FunASR'], label='ASR模型选择', value='WhisperX'),
        gr.Radio(['large', 'medium', 'small', 'base', 'tiny'], label='WhisperX模型大小', value='large'),
        gr.Slider(minimum=1, maximum=128, step=1, label='批处理大小 Batch Size', value=32),
        gr.Checkbox(label='分离多个说话人', value=True),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='最小说话人数', value=None),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='最大说话人数', value=None),

        gr.Dropdown(['OpenAI', 'LLM', 'Google Translate', 'Bing Translate', 'Ernie'], label='翻译方式', value='LLM'),
        gr.Dropdown(['简体中文', '繁体中文', 'English', 'Cantonese', 'Japanese', 'Korean'], label='目标语言', value='简体中文'),

        gr.Dropdown(available_tts_methods, label='AI语音生成方法', value='xtts'),
        gr.Dropdown(all_supported_languages, label='目标语言', value='中文'),
        gr.Dropdown(SUPPORT_VOICE, value='zh-CN-XiaoxiaoNeural', label='EdgeTTS声音选择'),

        gr.Checkbox(label='添加字幕', value=True),
        gr.Slider(minimum=0.5, maximum=2, step=0.05, label='加速倍数', value=1.00),
        gr.Slider(minimum=1, maximum=60, step=1, label='帧率', value=30),
        gr.Audio(label='背景音乐', sources=['upload']),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='背景音乐音量', value=0.5),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='视频音量', value=1.0),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='分辨率', value='1080p'),

        gr.Slider(minimum=1, maximum=100, step=1, label='Max Workers', value=1),
        gr.Slider(minimum=1, maximum=10, step=1, label='Max Retries', value=3),
        
        # 新增 Minimax 音色ID 输入框
        gr.Textbox(
            label='Minimax音色ID (仅在选择minimax时使用)', 
            value='cobra_design_20250717_162427_683071',
            placeholder='如: cobra_design_20250717_162427_683071',
            info='仅当AI语音生成方法选择minimax时有效。默认: 都市白领音色'
        ),
    ],
    outputs=[gr.Text(label='合成状态'), gr.Video(label='合成视频样例结果')],
    allow_flagging='never',
)    

# 下载视频接口
download_interface = gr.Interface(
    fn=download_from_url,
    inputs=[
        gr.Textbox(label='视频URL', placeholder='请输入Youtube或Bilibili的视频、播放列表或频道的URL', 
                   value='https://www.bilibili.com/video/BV1kr421M7vz/'),
        gr.Textbox(label='视频输出文件夹', value='videos'),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='分辨率', value='1080p'),
        gr.Slider(minimum=1, maximum=100, step=1, label='下载视频数量', value=5),
        # gr.Checkbox(label='单个视频', value=False),
    ],
    outputs=[
        gr.Textbox(label='下载状态'), 
        gr.Video(label='示例视频'), 
        gr.Json(label='下载信息')
    ],
    allow_flagging='never',
)

# 人声分离接口
demucs_interface = gr.Interface(
    fn=separate_all_audio_under_folder,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Radio(['htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'hdemucs_mmi', 'mdx', 'mdx_extra', 'mdx_q', 'mdx_extra_q', 'SIG'], label='模型', value='htdemucs_ft'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='计算设备', value='auto'),
        gr.Checkbox(label='显示进度条', value=True),
        gr.Slider(minimum=0, maximum=10, step=1, label='移位次数 Number of shifts', value=5),
    ],
    outputs=[
        gr.Text(label='分离结果状态'), 
        gr.Audio(label='人声音频'), 
        gr.Audio(label='伴奏音频')
    ],
    allow_flagging='never',
)

# AI智能语音识别接口
asr_inference = gr.Interface(
    fn=transcribe_all_audio_under_folder,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Dropdown(['WhisperX', 'FunASR'], label='ASR模型选择', value='WhisperX'),
        gr.Radio(['large', 'medium', 'small', 'base', 'tiny'], label='WhisperX模型大小', value='large'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='计算设备', value='auto'),
        gr.Slider(minimum=1, maximum=128, step=1, label='批处理大小 Batch Size', value=32),
        gr.Checkbox(label='分离多个说话人', value=True),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='最小说话人数', value=None),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='最大说话人数', value=None),
    ],
    outputs=[
        gr.Text(label='语音识别状态'), 
        gr.Json(label='识别结果详情')
    ],
    allow_flagging='never',
)

# 翻译字幕接口
translation_interface = gr.Interface(
    fn=translate_all_transcript_under_folder,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Dropdown(['OpenAI', 'LLM', 'Google Translate', 'Bing Translate', 'Ernie'], label='翻译方式', value='LLM'),
        gr.Dropdown(['简体中文', '繁体中文', 'English', 'Cantonese', 'Japanese', 'Korean'], label='目标语言', value='简体中文'),
    ],
    outputs=[
        gr.Text(label='翻译状态'), 
        gr.Json(label='总结结果'), 
        gr.Json(label='翻译结果')
    ],
    allow_flagging='never',
)

# 包装函数以支持 Minimax voice_id 参数
def tts_with_voice_id(folder, method, target_language, edge_voice, minimax_voice_id):
    """TTS接口包装函数，支持Minimax音色ID参数"""
    kwargs = {}
    if method == 'minimax' and minimax_voice_id.strip():
        kwargs['voice_id'] = minimax_voice_id.strip()
    
    return generate_all_wavs_under_folder(
        root_folder=folder,
        method=method,
        target_language=target_language,
        voice=edge_voice,
        **kwargs
    )

# AI语音合成接口
tts_interface = gr.Interface(
    fn=tts_with_voice_id,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Dropdown(available_tts_methods, label='AI语音生成方法', value='xtts'),
        gr.Dropdown(all_supported_languages, label='目标语言', value='中文'),
        gr.Dropdown(SUPPORT_VOICE, value='zh-CN-XiaoxiaoNeural', label='EdgeTTS声音选择'),
        gr.Textbox(
            label='Minimax音色ID (仅在选择minimax时使用)', 
            value='cobra_design_20250717_162427_683071',
            placeholder='如: cobra_design_20250717_162427_683071 或您的自定义音色ID',
            info='Minimax专用音色ID。默认: cobra_design_20250717_162427_683071 (都市白领)，或使用您通过Minimax语音克隆创建的音色ID'
        ),
    ],
    outputs=[
        gr.Text(label='合成状态'), 
        gr.Audio(label='合成语音'), 
        gr.Audio(label='原始音频')
    ],
    allow_flagging='never',
)

# 视频合成接口
synthesize_video_interface = gr.Interface(
    fn=synthesize_all_video_under_folder,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Checkbox(label='添加字幕', value=True),
        gr.Slider(minimum=0.5, maximum=2, step=0.05, label='加速倍数', value=1.00),
        gr.Slider(minimum=1, maximum=60, step=1, label='帧率', value=30),
        gr.Audio(label='背景音乐', sources=['upload'], type='filepath'),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='背景音乐音量', value=0.5),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='视频音量', value=1.0),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='分辨率', value='1080p'),

    ],
    outputs=[
        gr.Text(label='合成状态'), 
        gr.Video(label='合成视频')
    ],
    allow_flagging='never',
)

linly_talker_interface = gr.Interface(
    fn=lambda: None,
    inputs=[
        gr.Textbox(label='视频文件夹', value='videos'),
        gr.Dropdown(['Wav2Lip', 'Wav2Lipv2','SadTalker'], label='AI配音方式', value='Wav2Lip'),
    ],      
    outputs=[
        gr.Markdown(value="施工中，请静候佳音 可参考 [https://github.com/Kedreamix/Linly-Talker](https://github.com/Kedreamix/Linly-Talker)"),
        gr.Text(label='合成状态'),
        gr.Video(label='合成视频')
    ],
)

my_theme = gr.themes.Soft()
# 应用程序界面
app = gr.TabbedInterface(
    theme=my_theme,
    interface_list=[
        full_auto_interface,
        download_interface,
        demucs_interface,
        asr_inference,
        translation_interface,
        tts_interface,
        synthesize_video_interface,
        linly_talker_interface
    ],
    tab_names=[
        '一键自动化 One-Click', 
        '自动下载视频 ', '人声分离', 'AI智能语音识别', '字幕翻译', 'AI语音合成', '视频合成',
        'Linly-Talker 对口型（开发中）'],
    title='智能视频多语言AI配音/翻译工具 - Linly-Dubbing'
)

if __name__ == '__main__':
    app.launch(
        server_name="127.0.0.1", 
        server_port=6006,
        share=True,
        inbrowser=True
    )