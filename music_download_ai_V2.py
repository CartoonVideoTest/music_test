from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import requests
import io
import traceback
from urllib.parse import quote

app = Flask(__name__)
CORS(app)  # 允许跨域请求


def analyze_song_info(song_id: str) -> dict | None:
    """获取歌曲播放链接"""
    try:
        url = "https://api.bugpk.com/api/163_music"

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

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        song_url = response.json().get("data", [])[0].get("url", "")
        if song_url:
            return {"song_url": song_url, "success": True}
        else:
            return {"success": False, "error": "未获取到链接"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "网络连接错误"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"请求异常: {str(e)}"}
    except (KeyError, IndexError, TypeError) as e:
        return {"success": False, "error": f"解析响应数据失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {str(e)}"}


def search_results(words: str) -> dict:
    """搜索歌曲"""
    try:
        response = requests.get(
            f"https://api.bugpk.com/api/163_music?type=search&s={words}&limit=20",
            timeout=30
        )
        response.raise_for_status()

        data = response.json().get("data", {}).get("songs", [])
        if len(data) == 0:
            return {"success": False, "error": "无搜索结果", "songs": []}

        songs_info = []
        for song_info in data:
            song_id = song_info.get("id", "")
            song_name = song_info.get("name", "")
            artists = song_info.get("artists", "")

            # 处理 artists 可能是列表或字符串的情况
            if isinstance(artists, list):
                artist_names = [a.get("name", "") for a in artists if isinstance(a, dict)]
                artist_str = "、".join(artist_names)
            else:
                artist_str = str(artists)

            display_name = f"{artist_str} - {song_name}" if artist_str else song_name

            songs_info.append({
                "song_id": str(song_id),
                "song_name": song_name,
                "artists": artist_str,
                "display_name": display_name
            })

        return {"success": True, "songs": songs_info}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "搜索请求超时", "songs": []}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "网络连接错误", "songs": []}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"搜索请求异常: {str(e)}", "songs": []}
    except (KeyError, TypeError) as e:
        return {"success": False, "error": f"解析搜索结果失败: {str(e)}", "songs": []}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {str(e)}", "songs": []}


@app.route('/')
def index():
    """返回前端页面"""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search():
    """搜索歌曲接口"""
    try:
        data = request.get_json()
        words = data.get('words', '').strip()

        if not words:
            return jsonify({"success": False, "error": "请输入搜索关键词"})

        result = search_results(words)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})


@app.route('/api/get_song_url', methods=['POST'])
def get_song_url():
    """获取歌曲播放链接接口"""
    try:
        data = request.get_json()
        song_id = data.get('song_id', '')

        if not song_id:
            return jsonify({"success": False, "error": "缺少歌曲ID"})

        result = analyze_song_info(song_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})


@app.route('/api/download', methods=['POST'])
def download_song():
    """下载歌曲接口"""
    try:
        data = request.get_json()
        song_url = data.get('song_url', '')
        song_name = data.get('song_name', 'song')

        if not song_url:
            return jsonify({"success": False, "error": "缺少音频链接"})

        # 下载音频文件
        response = requests.get(song_url, timeout=60)
        response.raise_for_status()

        # 创建文件流
        audio_data = io.BytesIO(response.content)

        # 安全处理文件名
        safe_filename = f"{song_name}.mp3"
        # 移除不安全的文件名字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in unsafe_chars:
            safe_filename = safe_filename.replace(char, '_')

        return send_file(
            audio_data,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=safe_filename
        )
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "下载超时，请重试"}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"下载失败: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)