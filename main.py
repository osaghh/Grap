from flask import Flask, request, send_file, render_template_string, Response, stream_with_context, url_for
import yt_dlp
import os
import glob
import re
from urllib.parse import quote_plus, unquote_plus # Import for URL encoding/decoding

app = Flask(__name__)

def get_byte_range(request_headers):
    byte1 = 0
    byte2 = None
    if 'Range' in request_headers:
        m = re.search('bytes=(\\d+)-(\\d*)', request_headers['Range'])
        g = m.groups()
        byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])
    return byte1, byte2

INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD")


@app.route('/')
def home():
    return '''
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Download Video</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f2f2f2; }
                h2 { color: #333; }
                input[type=text] {
                    width: 100%;
                    padding: 12px;
                    margin-top: 8px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                button {
                    margin-top: 12px;
                    width: 100%;
                    padding: 12px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #45a049;
                }
                .message {
                    margin-top: 20px;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                .success {
                    background-color: #e0ffe0;
                    color: #006400;
                }
                .error {
                    background-color: #ffe0e0;
                    color: #a00000;
                }
            </style>
        </head>
        <body>
            <h2>Download Video 📹</h2>
            <form action="/download_and_serve" method="get">
                <input type="text" name="url" placeholder="Paste video link" required>
                <button type="submit">Download & Play</button>
            </form>
        </body>
        </html>
    '''

@app.route('/download_and_serve')
def download_and_serve():
    video_url = request.args.get('url')
    if not video_url:
        return "<div class='message error'>No video URL provided.</div>"

    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'verbose': True, # Keep True for debugging
        'no_warnings': True,
        'ignoreerrors': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'username': INSTAGRAM_USERNAME,
        'password': INSTAGRAM_PASSWORD,
    }

    if "instagram.com" in video_url and (not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD):
        return "<div class='message error'>Instagram login required. Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in Replit Secrets.</div>"

    try:
        print(f"Attempting to download video from: {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # THIS IS THE CRITICAL CHANGE:
            # We need to use a hook to get the actual final path yt-dlp saves to.
            # Define a list to store the final path.
            final_downloaded_file_list = []

            def download_hook(d):
                if d['status'] == 'finished':
                    final_downloaded_file_list.append(d['filepath'])

            ydl_opts['progress_hooks'] = [download_hook]

            info_dict = ydl.extract_info(video_url, download=True)
            if info_dict is None:
                print(f"yt-dlp returned None for URL: {video_url}")
                return f"<div class='message error'>Failed to retrieve video information. Check console for yt-dlp errors (e.g., login required, rate-limit).</div>"

            video_title = info_dict.get('title', 'Video')
            video_ext = info_dict.get('ext', 'mp4')

            # Get the actual final path from the hook, if available
            final_downloaded_file = None
            if final_downloaded_file_list:
                final_downloaded_file = final_downloaded_file_list[0]
                print(f"yt-dlp reported final file path via hook: {final_downloaded_file}")
            else:
                # Fallback if hook didn't catch it (shouldn't happen often for successful downloads)
                # Try to guess based on info_dict's ID or known patterns.
                # Or, simpler: look for the most recently modified mp4 in the download directory
                all_mp4s_in_dir = glob.glob(os.path.join(download_dir, f"*.{video_ext}"))
                if all_mp4s_in_dir:
                    all_mp4s_in_dir.sort(key=os.path.getmtime, reverse=True)
                    final_downloaded_file = all_mp4s_in_dir[0]
                    print(f"Fallback: Found recently modified file: {final_downloaded_file}")

            # --- Critical Check: Verify the file exists ---
            if not final_downloaded_file or not os.path.exists(final_downloaded_file):
                print(f"Error: Expected file {final_downloaded_file} does not exist after download process.")
                # Also print directory contents for debugging
                if os.path.exists(download_dir) and os.path.isdir(download_dir):
                    print(f"Contents of '{download_dir}': {os.listdir(download_dir)}")
                else:
                    print(f"'{download_dir}' directory does not exist.")
                return f"<div class='message error'>Error: Downloaded file path is invalid. File not found on server.</div>"
            # --- End Critical Check ---

            print(f"Video will be played from path: {final_downloaded_file}")

            encoded_filepath = quote_plus(final_downloaded_file)

            return render_template_string('''
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Playing Video</title>
                    <style>
                        body { font-family: Arial; padding: 20px; background: #f2f2f2; text-align: center; }
                        h2 { color: #333; }
                        video { max-width: 90%; height: auto; border: 1px solid #ccc; background-color: black; margin-top: 20px; }
                        .controls { margin-top: 20px; }
                        .controls a {
                            display: inline-block;
                            padding: 10px 20px;
                            margin: 0 5px;
                            background-color: #007BFF;
                            color: white;
                            text-decoration: none;
                            border-radius: 5px;
                            font-size: 16px;
                        }
                        .controls a:hover {
                            background-color: #0056b3;
                        }
                        .message {
                            margin-top: 20px;
                            padding: 10px;
                            border-radius: 5px;
                            font-weight: bold;
                        }
                        .success {
                            background-color: #e0ffe0;
                            color: #006400;
                        }
                        .error {
                            background-color: #ffe0e0;
                            color: #a00000;
                        }
                    </style>
                </head>
                <body>
                    <h2>Playing: {{ title }}</h2>
                    <video controls autoplay>
                        <source src="/play_video?filepath={{ encoded_filepath }}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="controls">
                        <a href="/">Download another video</a>
                        <a href="{{ url_for('play_video', filepath=original_filepath) }}" download="{{ title }}.mp4">Download Original File</a>
                    </div>
                </body>
                </html>
            ''', title=video_title, encoded_filepath=encoded_filepath, original_filepath=final_downloaded_file) # Pass both encoded and original filepath

    except Exception as e:
        print(f"Error during video download: {e}")
        return f"<div class='message error'>Error downloading video: {e}. Please try again or check the URL.</div>"

# The /play_video route remains the same as your previous correct version
@app.route('/play_video')
def play_video():
    filepath = request.args.get('filepath')
    print(f"Received request for play_video with filepath: {filepath}")

    if not filepath:
        print("Error: filepath parameter is missing.")
        return "<div class='message error'>Video file path is missing.</div>"

    decoded_filepath = unquote_plus(filepath)
    print(f"Decoded filepath: {decoded_filepath}")

    if not os.path.exists(decoded_filepath):
        print(f"Error: File does not exist at decoded path: {decoded_filepath}")
        download_dir = "downloads"
        if os.path.exists(download_dir) and os.path.isdir(download_dir):
            print(f"Contents of '{download_dir}': {os.listdir(download_dir)}")
        else:
            print(f"'{download_dir}' directory does not exist.")
        return "<div class='message error'>Video file not found on the server. It might not have downloaded correctly or the path is wrong.</div>"

    try:
        file_size = os.path.getsize(decoded_filepath)
        start_byte, end_byte = get_byte_range(request.headers)

        if end_byte is None:
            end_byte = file_size - 1

        length = end_byte - start_byte + 1

        if start_byte >= file_size or start_byte < 0 or end_byte >= file_size or end_byte < 0:
            print(f"Invalid byte range request: start={start_byte}, end={end_byte}, size={file_size}")
            return Response("Invalid Range", status=416, mimetype="text/plain")

        headers = {
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Content-Range': f'bytes {start_byte}-{end_byte}/{file_size}'
        }
        status_code = 206 if start_byte > 0 or end_byte < file_size - 1 else 200

        def generate_chunk():
            with open(decoded_filepath, 'rb') as f:
                f.seek(start_byte)
                remaining_bytes = length
                while remaining_bytes > 0:
                    chunk_size = min(remaining_bytes, 8192)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
                    remaining_bytes -= len(data)

        print(f"Serving video chunk: {start_byte}-{end_byte} from {decoded_filepath} (Status: {status_code})")
        return Response(stream_with_context(generate_chunk()), status=status_code, headers=headers)

    except Exception as e:
        print(f"Error serving video file from '{decoded_filepath}': {e}")
        return f"<div class='message error'>Error playing video: {e}</div>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
