import requests
import re
from bs4 import BeautifulSoup
import streamlit as st
from typing import Dict, Optional, Tuple

# 常量定义
HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'cache-control': 'max-age=0',
    'dnt': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
}

# Cookie（建议从环境变量读取，不要硬编码）
COOKIE = 'name=lexopn; cf_clearance=npjNIquDW7QYNOeWmwKGgljnf_3QNNKDPJ.UTrjFnX4-1779535175-1.2.1.1-kKsDSIeRAWDOk3n0foKAleQeRe8q372f328_uINck0hTtPsfdwFM3MMHrSCzLa_vBMF0aLR5uEkbJQSzIFkvHBAhtIAJLoB_9fdKtk4N9zwqXWFNkFyKn4GFo2HpoijP9OpWTsetWQy5o2oW8ygKIk97Q1NFojoeDrusQ1MfkgEAYFtnvarjx9yu5IP5xqP7xdajVcrTvaxbMjp6cwop.AM9r3KfonATGfS5z1AB68upiu7I9VCIhGHAZALLmx.Kfxw1Z02Au1.V08bqHQJOy_R_ZivlHcjzljcql0lhIhARgt_aYQyZuUHvEwuc7ciYdqafPm1eozXrtmDKlBvLEw'

BASE_URL = 'https://www.gequhai.net'


def get_headers(referer: str = '') -> Dict:
    """获取请求头"""
    headers = HEADERS.copy()
    headers['cookie'] = COOKIE
    if referer:
        headers['referer'] = referer
    return headers


def search_music(word: str) -> Optional[Dict[str, str]]:
    """搜索音乐

    Args:
        word: 搜索关键词

    Returns:
        音乐字典 {歌曲名: 详情页URL}，失败返回None
    """
    if not word or not word.strip():
        return None

    try:
        response = requests.get(
            f'{BASE_URL}/s/{word.strip()}',
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        music_links = soup.select("div.col-8 > a.text-decoration-none")

        if not music_links:
            return {}

        music_dict = {}
        for link in music_links:
            # 清理歌曲名
            music_name = link.get_text(strip=True)
            music_url = f"{BASE_URL}{link.get('href', '')}"
            if music_name and music_url != BASE_URL:
                music_dict[music_name] = music_url

        return music_dict

    except requests.exceptions.Timeout:
        st.error("⏰ 请求超时，请稍后重试")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"🔍 搜索失败: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ 解析失败: {str(e)}")
        return None


def get_music_url(detail_url: str) -> Optional[bytes]:
    """从详情页获取音频文件

    Args:
        detail_url: 歌曲详情页URL

    Returns:
        音频文件二进制内容，失败返回None
    """
    if not detail_url:
        return None

    try:
        # 获取详情页
        response = requests.get(
            detail_url,
            headers=get_headers(referer=f'{BASE_URL}/s/'),
            timeout=10
        )
        response.raise_for_status()

        # 提取音频下载路径
        match = re.search(r"window\.mp3_url_download\s*=\s*'([^']+)';", response.text)
        if not match:
            st.error("🎵 未找到音频链接")
            return None

        audio_path = match.group(1)
        if not audio_path:
            return None

        # 下载音频文件
        audio_url = f"{BASE_URL}{audio_path}" if not audio_path.startswith('http') else audio_path
        audio_response = requests.get(
            audio_url,
            headers=get_headers(referer=detail_url),
            timeout=30
        )
        audio_response.raise_for_status()

        return audio_response.content

    except requests.exceptions.Timeout:
        st.error("⏰ 下载超时，请稍后重试")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"📥 获取音频失败: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ 处理失败: {str(e)}")
        return None


def init_session_state():
    """初始化session state变量"""
    defaults = {
        "search_music": False,
        "search_results": {},
        "playing": False,
        "playing_content": None,  # 改为 None，格式: (name, audio_bytes)
        "current_playing_name": None
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def display_search_results():
    """显示搜索结果"""
    if not st.session_state["search_results"]:
        st.info("🔍 未找到相关歌曲，请尝试其他关键词")
        return

    st.subheader(f"📋 搜索结果 ({len(st.session_state['search_results'])} 首)")

    for idx, (name, page_url) in enumerate(st.session_state["search_results"].items(), 1):
        # 使用容器美化每个歌曲项
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                # 高亮正在播放的歌曲
                if (st.session_state["playing"] and
                        st.session_state.get("current_playing_name") == name):
                    st.markdown(f"🎵 **{name}** (播放中)")
                else:
                    st.write(name)

            with col2:
                if st.button("▶️ 播放", key=f"play_{idx}"):
                    with st.spinner(f"加载中: {name}"):
                        audio_content = get_music_url(page_url)
                        if audio_content:
                            st.session_state["playing_content"] = (name, audio_content)
                            st.session_state["current_playing_name"] = name
                            st.session_state["playing"] = True
                            st.rerun()
                        else:
                            st.error(f"无法加载: {name}")

            with col3:
                # 下载按钮 - 修复嵌套button问题
                if st.button("💾 下载", key=f"download_bt_{idx}"):
                    with st.spinner(f"准备下载: {name}"):
                        audio_content = get_music_url(page_url)
                        if audio_content:
                            st.download_button(
                                label="保存音频",
                                data=audio_content,
                                file_name=f"{name}.mp3",
                                mime="audio/mpeg",
                                key=f"download_{idx}"
                            )
                        else:
                            st.error(f"无法下载: {name}")

            st.divider()


def main_run():
    """主运行函数"""
    # 初始化session state
    init_session_state()

    # 页面标题
    st.title("🎵 音乐搜索播放器")

    # 搜索区域
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            search_word = st.text_input(
                "搜索歌曲",
                placeholder="输入歌曲名或歌手名...",
                label_visibility="collapsed"
            )
        with col2:
            search_button = st.button("🔍 搜索", type="primary", use_container_width=True)

    # 处理搜索
    if search_button and search_word:
        st.session_state["search_music"] = True
        with st.spinner("🎵 搜索中，请稍候..."):
            results = search_music(search_word)
            if results is not None:
                st.session_state["search_results"] = results
                # 重置播放状态
                st.session_state["playing"] = False
                st.session_state["playing_content"] = None
                st.session_state["current_playing_name"] = None
                if not results:
                    st.warning("未找到相关歌曲")
            else:
                st.session_state["search_results"] = {}
                st.error("搜索失败，请稍后重试")

    # 显示正在播放
    if st.session_state["playing"] and st.session_state["playing_content"]:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"🎧 正在播放: {st.session_state['playing_content'][0]}")
        with col2:
            if st.button("⏹️ 停止", use_container_width=True):
                st.session_state["playing"] = False
                st.session_state["playing_content"] = None
                st.session_state["current_playing_name"] = None
                st.rerun()

        st.audio(
            st.session_state["playing_content"][1],
            autoplay=True,
            format="audio/mpeg"
        )

    # 显示搜索结果
    if st.session_state["search_music"] or st.session_state["search_results"]:
        st.divider()
        display_search_results()
    else:
        st.info("✨ 输入歌曲名称开始搜索")


# 页面配置
st.set_page_config(
    page_title="音乐搜索器",
    page_icon="🎵",
    layout="wide"
)

if __name__ == '__main__':
    main_run()