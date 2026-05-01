import time
import streamlit as st
import requests



def analyze_song_info(song_id:str) -> dict[str, str] | None:
    url = "https://api.bugpk.com/api/163_music"

    # level standard(标准音质), exhigh(极高音质), lossless(无损音质), hires(Hi-Res音质), jyeffect(高清环绕声), sky(沉浸环绕声), jymaster(超清母带)
    params = {
        "url": "",
        "ids": "",
        "id": song_id,
        "offset": "",
        "limit": "",
        "type": "url",
        "level": "standard",
        "s": ""
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"请求异常，状态码{response.status_code}")
        return None

    song_url = response.json().get("data", [])[0].get("url", "")
    if song_url:
        return song_url
    else:
        print(f"未获取到链接")
        return None


def search_results(words:str) -> list[dict] | None:
    response = requests.get(f"https://api.bugpk.com/api/163_music?type=search&s={words}&limit=20")
    if response.status_code != 200:
        print(f"请求异常，状态码{response.status_code}")
        return None

    data = response.json().get("data", []).get("songs", [])
    if len(data) == 0:
        print(f"No results found for {words}")
        return None

    else:
        songs_info = []
        for song_info in data:
            song_id = song_info.get("id", "")
            song_name = f'{song_info.get("artists", "")} - {song_info.get("name", "")}'

            songs_info.append({ "song_id": song_id,"song_name": song_name })
        return songs_info


def playing_sidebar(music_data: dict) -> None:
    with st.sidebar:
        st.title("网易音乐简易检索器")
        st.write("---")

        if st.button("重置页面", key="reset"):
            st.session_state.clear()
            st.rerun()

        st.write("---")

        if music_data:
            st.write("正在播放：")
            song_name = music_data["song_name"]
            st.write(song_name)
            # playing_status = st.toggle("循环播放")

            st.audio(music_data["song_url"], autoplay=True, loop= False)
        else:
            st.info("暂无音乐播放")


def style_streamlit():
    if "get_url_page" not in st.session_state:
        st.session_state["get_url_page"] = False
    if "get_search_page" not in st.session_state:
        st.session_state["get_search_page"] = False
    if "playing_data" not in st.session_state:
        st.session_state["playing_data"] = {}
    if "result" not in st.session_state:
        st.session_state["result"] = {}


    playing_sidebar(st.session_state["playing_data"])

    search_words = st.text_input("输入关键词：")

    if st.button("搜索", key="search"):
        st.session_state["result"] = {}
        if not search_words:
            st.error("输入关键词")
            time.sleep(1)
            return None

        if not st.session_state["result"]:
            result = search_results(search_words.strip())
        else:
            result = st.session_state["result"]

        if result:
            st.session_state["result"] = result
            st.session_state["get_search_page"] = True
        else:
            st.info("无搜索结果")
            return None

    st.info("侧边栏播放歌曲“更多选项”下载更快，有时限限制")

    if st.session_state["get_search_page"]:
        result = st.session_state["result"]
        for song in result:

            s_name = song["song_name"]
            s_id = song["song_id"]
            if not s_id:
                continue
            st.write("---")

            st.write(s_name)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("歌曲播放", key=f"url_{s_id}"):
                    url = analyze_song_info(s_id)
                    st.session_state["playing_data"] = {"song_name": s_name, "song_id" : s_id, "song_url": url}
                    st.rerun()

            with col2:
                if st.button("歌曲下载", key=f"download_{s_id}"):

                    # 如果要 下载的歌曲 和 当前播放歌曲 为同一个歌曲，无需重新获取获取链接
                    song_id = st.session_state["playing_data"].get("song_id", "")
                    if song_id == s_id:
                        url = st.session_state["playing_data"].get("song_url", "")

                    # 非同一歌曲需获取音频链接
                    else:
                        url = analyze_song_info(s_id)

                    if url:
                        with st.spinner("下载中，时间可能较长"):
                            response = requests.get(url)
                            st.download_button(
                                label="保存 音频",
                                data=response.content,
                                file_name=f"{s_name}.mp3",
                                mime="audio/mpeg"
                            )

    return None


def main_run():
    try:
        style_streamlit()
    except Exception as e:
        # st.error(e)
        st.error("脚本或接口异常")




if __name__ == '__main__':
    main_run()



