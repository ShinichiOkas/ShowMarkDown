import sys
import os

# Windows環境で、新規にアロケートされたコンソールウィンドウのみを非表示にするハック
if sys.platform == 'win32':
    try:
        import ctypes
        # 現在のコンソールを共有しているプロセスの数を取得
        process_list = (ctypes.c_ulong * 10)()
        num_processes = ctypes.windll.kernel32.GetConsoleProcessList(process_list, 10)
        
        # 共有しているプロセスが自分（とPyInstallerブートローダー）のみ（ダブルクリック/D&D起動など）の場合のみ非表示にする
        # CUIから起動した場合は、呼び出し元シェル(cmd/powershell)が加わるためプロセス数が3以上になります。
        if num_processes <= 2:
            whnd = ctypes.windll.kernel32.GetConsoleWindow()
            if whnd != 0:
                ctypes.windll.user32.ShowWindow(whnd, 0) # SW_HIDE = 0
    except Exception:
        pass

import time
import threading
import webbrowser
import markdown
import webview

def get_css():
    return """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 16px;
        line-height: 1.6;
        word-wrap: break-word;
        background-color: #ffffff;
        color: #24292e;
        padding: 30px;
        margin: 0;
    }
    .markdown-body {
        max-width: 900px;
        margin: 0 auto;
    }
    h1, h2, h3, h4, h5, h6 {
        margin-top: 24px;
        margin-bottom: 16px;
        font-weight: 600;
        line-height: 1.25;
    }
    h1 { font-size: 2em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
    h2 { font-size: 1.5em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
    h3 { font-size: 1.25em; }
    h4 { font-size: 1em; }
    h5 { font-size: 0.875em; }
    h6 { font-size: 0.85em; color: #6a737d; }
    p, blockquote, ul, ol, dl, table, pre {
        margin-top: 0;
        margin-bottom: 16px;
    }
    code {
        padding: 0.2em 0.4em;
        margin: 0;
        font-size: 85%;
        background-color: rgba(27,31,35,0.05);
        border-radius: 3px;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    }
    pre {
        padding: 16px;
        overflow: auto;
        font-size: 85%;
        line-height: 1.45;
        background-color: #f6f8fa;
        border-radius: 6px;
    }
    pre code {
        background-color: transparent;
        padding: 0;
        font-size: 100%;
        word-break: normal;
        white-space: pre;
    }
    blockquote {
        padding: 0 1em;
        color: #6a737d;
        border-left: 0.25em solid #dfe2e5;
    }
    /* テーブルスタイル */
    table {
        border-spacing: 0;
        border-collapse: collapse;
        display: block;
        width: 100%;
        overflow: auto;
        margin-top: 0;
        margin-bottom: 16px;
    }
    table th {
        font-weight: 600;
        background-color: #f6f8fa;
    }
    table th, table td {
        padding: 6px 13px;
        border: 1px solid #dfe2e5;
    }
    table tr {
        background-color: #ffffff;
        border-top: 1px solid #c6cbd1;
    }
    table tr:nth-child(2n) {
        background-color: #f6f8fa;
    }
    /* リストスタイル */
    ul, ol {
        padding-left: 2em;
    }
    li + li {
        margin-top: 0.25em;
    }
    /* リンク */
    a {
        color: #0366d6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    img {
        max-width: 100%;
        box-sizing: content-box;
        background-color: #ffffff;
    }
    /* 水平線 */
    hr {
        height: 0.25em;
        padding: 0;
        margin: 24px 0;
        background-color: #e1e4e6;
        border: 0;
    }
    """

def convert_md_to_html(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        text = f"# Error\n\nFailed to read file: {e}"

    # 拡張機能を有効化してHTML変換
    # tables: テーブルサポート
    # fenced_code: ```によるコードブロックサポート
    html_content = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code']
    )
    
    # CSSスタイルをインポートしたHTMLテンプレートを構築
    # JSで外部リンクのクリックをフックしてPython APIを呼び出す
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{{TITLE}} - showmd</title>
        <style>
            {{CSS}}
        </style>
    </head>
    <body>
        <div class="markdown-body">
            {{CONTENT}}
        </div>
        <script>
            document.addEventListener('click', function(e) {
                var target = e.target;
                while (target && target.tagName !== 'A') {
                    target = target.parentNode;
                }
                if (target && target.tagName === 'A') {
                    var href = target.getAttribute('href');
                    if (href && (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('mailto:') || href.startsWith('ftp:'))) {
                        e.preventDefault();
                        pywebview.api.open_external_link(href);
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    
    full_html = template.replace('{{TITLE}}', os.path.basename(filepath))\
                        .replace('{{CSS}}', get_css())\
                        .replace('{{CONTENT}}', html_content)
    return full_html

class Api:
    def open_external_link(self, url):
        webbrowser.open(url)

def watch_file(filepath, window):
    try:
        last_mtime = os.path.getmtime(filepath)
    except Exception:
        last_mtime = 0

    while True:
        time.sleep(0.5)
        try:
            current_mtime = os.path.getmtime(filepath)
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                new_html = convert_md_to_html(filepath)
                window.load_html(new_html)
        except Exception:
            pass

def main():
    if len(sys.argv) < 2:
        # 引数がない場合は、使い方のHTMLを表示する
        filepath = None
        initial_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>showmd - Usage</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    padding: 40px;
                    background-color: #ffffff;
                    color: #24292e;
                    text-align: center;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    border: 1px solid #e1e4e6;
                    border-radius: 6px;
                    padding: 30px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                }
                h1 { font-size: 1.8em; margin-bottom: 10px; color: #0366d6; }
                p { font-size: 1.1em; line-height: 1.5; color: #586069; }
                code {
                    background-color: #f6f8fa;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-family: monospace;
                    display: inline-block;
                    margin-top: 15px;
                    font-size: 1em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>showmd (Markdown Viewer)</h1>
                <p>このプログラムはコマンドラインからマークダウンファイルを指定して起動します。</p>
                <code>showmd.exe &lt;filename.md&gt;</code>
            </div>
        </body>
        </html>
        """
        title = "showmd - Usage"
    else:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            # ファイルが存在しないエラー
            initial_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>showmd - Error</title>
                <style>
                    body {{ font-family: sans-serif; padding: 40px; text-align: center; color: #d73a49; }}
                    .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #d73a49; border-radius: 6px; padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Error: File Not Found</h2>
                    <p>指定されたファイルが見つかりません:</p>
                    <p><strong>{filepath}</strong></p>
                </div>
            </body>
            </html>
            """
            title = "showmd - Error"
            filepath = None
        else:
            initial_html = convert_md_to_html(filepath)
            title = f"{os.path.basename(filepath)} - showmd"

    api = Api()
    window = webview.create_window(
        title=title,
        html=initial_html,
        js_api=api,
        width=800,
        height=600,
        min_size=(400, 300),
        text_select=True
    )

    def start_monitoring(win):
        if filepath:
            t = threading.Thread(target=watch_file, args=(filepath, win), daemon=True)
            t.start()

    webview.start(start_monitoring, window)

if __name__ == '__main__':
    main()
