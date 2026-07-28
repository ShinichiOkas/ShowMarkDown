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

import atexit
import html
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

import webview

import mdrender

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
    /* 編集モード関連のスタイル */
    .edit-btn {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background-color: #0366d6;
        color: #ffffff;
        border: none;
        box-shadow: 0 4px 12px rgba(3, 102, 214, 0.3);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 1000;
        outline: none;
    }
    .edit-btn:hover {
        background-color: #0255b3;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(3, 102, 214, 0.4);
    }
    .edit-btn:active {
        transform: translateY(0);
    }
    .edit-btn svg {
        width: 24px;
        height: 24px;
        fill: currentColor;
        transition: transform 0.25s ease;
    }
    .edit-btn.view-mode-active {
        background-color: #28a745;
        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
    }
    .edit-btn.view-mode-active:hover {
        background-color: #218838;
        box-shadow: 0 6px 16px rgba(40, 167, 69, 0.4);
    }
    
    #editor-container {
        display: none;
        max-width: 900px;
        margin: 0 auto;
        animation: fadeIn 0.2s ease-out;
    }
    #editor {
        width: 100%;
        /* CSS zoom は vh を補正しないが、引いている 120px は補正される。
           そのまま書くと拡大時にエディタが画面からはみ出すため --zoom で割り戻す。 */
        height: calc(100vh / var(--zoom, 1) - 120px);
        min-height: calc(400px / var(--zoom, 1));
        padding: 20px;
        box-sizing: border-box;
        border: 1px solid #dfe2e5;
        border-radius: 8px;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
        font-size: 15px;
        line-height: 1.6;
        color: #24292e;
        background-color: #fafbfc;
        resize: none;
        outline: none;
        transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
    }
    #editor:focus {
        border-color: #0366d6;
        background-color: #ffffff;
        box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.15);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    body.editing-active {
        overflow: hidden;
    }

    /* ===== 数式 (MathML) ===== */
    math {
        font-size: 1.08em;
    }
    .math-block {
        margin: 16px 0;
        text-align: center;
        overflow-x: auto;
        overflow-y: hidden;
    }
    .math-block math {
        font-size: 1.15em;
    }
    .math-inline {
        white-space: nowrap;
    }
    /* 解釈できなかった数式は原文をそのまま見せる */
    .math-error {
        background-color: #ffeef0;
        color: #d73a49;
        border: 1px solid #fdaeb7;
    }
    .math-raw {
        background-color: #fff5b1;
    }

    /* ===== タスクリスト ===== */
    ul.task-list {
        padding-left: 1.2em;
    }
    li.task-list-item {
        list-style: none;
    }
    li.task-list-item > input[type="checkbox"] {
        margin: 0 0.4em 0 -1.2em;
        vertical-align: middle;
    }

    /* ===== 打ち消し線 ===== */
    del {
        color: #6a737d;
    }

    /* ===== 定義リスト ===== */
    dl dt {
        font-weight: 600;
        margin-top: 16px;
    }
    dl dd {
        margin-left: 2em;
        margin-bottom: 8px;
    }

    /* ===== 略語 ===== */
    abbr[title] {
        border-bottom: 1px dotted #6a737d;
        text-decoration: none;
        cursor: help;
    }

    /* ===== 脚注 ===== */
    .footnote {
        font-size: 0.875em;
        color: #6a737d;
        margin-top: 32px;
    }
    .footnote hr {
        height: 1px;
        background-color: #eaecef;
        margin: 16px 0;
    }
    sup[id^="fnref"] a {
        text-decoration: none;
    }

    /* ===== 目次 ([TOC]) ===== */
    .toc {
        background-color: #f6f8fa;
        border: 1px solid #eaecef;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }
    .toc ul {
        margin: 0;
        padding-left: 1.4em;
    }
    .toc > ul {
        padding-left: 1em;
    }

    /* ===== 生HTML でよく使われる要素 ===== */
    details {
        border: 1px solid #eaecef;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 16px;
    }
    details > summary {
        cursor: pointer;
        font-weight: 600;
        margin: -8px -12px;
        padding: 8px 12px;
    }
    details[open] > summary {
        border-bottom: 1px solid #eaecef;
        margin-bottom: 8px;
    }
    kbd {
        display: inline-block;
        padding: 3px 5px;
        font-size: 0.8em;
        font-family: "SFMono-Regular", Consolas, monospace;
        line-height: 1;
        color: #24292e;
        background-color: #fafbfc;
        border: 1px solid #d1d5da;
        border-bottom-color: #c6cbd1;
        border-radius: 3px;
        box-shadow: inset 0 -1px 0 #c6cbd1;
    }
    sub, sup {
        font-size: 0.75em;
        line-height: 0;
    }
    mark {
        background-color: #fff5b1;
    }
    """

def convert_md_to_html(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        text = f"# Error\n\nFailed to read file: {e}"

    raw_markdown_escaped = html.escape(text)

    # 画像の相対パスは、MDファイルのあるフォルダを基準に file:// 絶対URLへ解決する
    base_dir = os.path.dirname(os.path.abspath(filepath))
    html_content = mdrender.render(text, base_dir)

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
        <script>
            // 表示倍率（Ctrl+ホイール / Ctrl+プラス・マイナス / Ctrl+0）
            //
            // WebView2 のネイティブズームは AreBrowserAcceleratorKeysEnabled が
            // デバッグ時のみ有効なため効かない。CSS zoom で自前に実装する。
            //
            // 倍率は localStorage に持つ。保存・ファイル自動更新のたびに
            // location.reload() で再描画するため、持たないと毎回100%に戻ってしまう。
            // body より先に適用したいので head で実行する（ちらつき防止）。
            (function() {
                var STEPS = [0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5, 3];
                var DEFAULT_INDEX = 5;   // STEPS[5] === 1
                var KEY = 'showmd-zoom';

                function stored() {
                    try {
                        var v = parseFloat(localStorage.getItem(KEY));
                        return isFinite(v) && v > 0 ? v : 1;
                    } catch (e) {
                        return 1;
                    }
                }

                function nearestIndex(z) {
                    var best = DEFAULT_INDEX, diff = Infinity;
                    for (var i = 0; i < STEPS.length; i++) {
                        var d = Math.abs(STEPS[i] - z);
                        if (d < diff) { diff = d; best = i; }
                    }
                    return best;
                }

                function apply(z) {
                    document.documentElement.style.zoom = (z === 1) ? '' : String(z);
                    // vh を使う要素（エディタ）がズームを割り戻せるように公開する
                    document.documentElement.style.setProperty('--zoom', String(z));
                    try { localStorage.setItem(KEY, String(z)); } catch (e) {}
                }

                function step(delta) {
                    var i = nearestIndex(stored()) + delta;
                    apply(STEPS[Math.max(0, Math.min(STEPS.length - 1, i))]);
                }

                // 復元（reload をまたいで倍率を維持する）
                apply(stored());

                document.addEventListener('wheel', function(e) {
                    if (!e.ctrlKey) return;
                    e.preventDefault();
                    step(e.deltaY < 0 ? 1 : -1);
                }, { passive: false });

                document.addEventListener('keydown', function(e) {
                    if (!(e.ctrlKey || e.metaKey)) return;
                    if (e.key === '0') {
                        e.preventDefault();
                        apply(1);
                    } else if (e.key === '+' || e.key === '=') {
                        e.preventDefault();
                        step(1);
                    } else if (e.key === '-') {
                        e.preventDefault();
                        step(-1);
                    }
                });
            })();
        </script>
    </head>
    <body>
        <div id="view-container" class="markdown-body">
            {{CONTENT}}
        </div>
        <div id="editor-container">
            <textarea id="editor" placeholder="Markdownを記述してください..."></textarea>
        </div>
        
        <textarea id="raw-markdown" style="display:none;">{{RAW_MARKDOWN}}</textarea>
        
        <button id="mode-toggle" class="edit-btn" title="Edit Markdown">
            <!-- 鉛筆アイコン -->
            <svg id="icon-edit" viewBox="0 0 24 24">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
            <!-- チェックマークアイコン（保存してビュー） -->
            <svg id="icon-save" viewBox="0 0 24 24" style="display:none;">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
        </button>

        <script>
            // 外部リンククリックの処理
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

            // 編集モードトグル処理
            (function() {
                var modeToggle = document.getElementById('mode-toggle');
                var viewContainer = document.getElementById('view-container');
                var editorContainer = document.getElementById('editor-container');
                var editor = document.getElementById('editor');
                var rawMarkdown = document.getElementById('raw-markdown');
                var iconEdit = document.getElementById('icon-edit');
                var iconSave = document.getElementById('icon-save');
                
                var isEditing = false;
                
                modeToggle.addEventListener('click', function() {
                    if (!isEditing) {
                        // 編集モードに入る
                        isEditing = true;
                        document.body.classList.add('editing-active');
                        viewContainer.style.display = 'none';
                        editorContainer.style.display = 'block';
                        
                        // 生テキストをセット
                        editor.value = rawMarkdown.value;
                        editor.focus();
                        
                        // ボタン状態の変更
                        modeToggle.classList.add('view-mode-active');
                        modeToggle.title = "Save & View";
                        iconEdit.style.display = 'none';
                        iconSave.style.display = 'block';
                        
                        // Python側に通知
                        pywebview.api.set_editing(true);
                    } else {
                        // ビューモードに戻る（自動セーブ）
                        var newContent = editor.value;
                        
                        // 保存ボタンをローディング状態にする
                        modeToggle.style.opacity = '0.5';
                        modeToggle.disabled = true;
                        
                        pywebview.api.save_content(newContent).then(function(success) {
                            if (!success) {
                                alert('ファイルの保存中にエラーが発生しました。');
                                modeToggle.style.opacity = '1';
                                modeToggle.disabled = false;
                            }
                        }).catch(function(err) {
                            console.error(err);
                            modeToggle.style.opacity = '1';
                            modeToggle.disabled = false;
                            alert('ファイルの保存中にエラーが発生しました。');
                        });
                    }
                });
                
                // Ctrl+S ショートカットもエディタ内でサポート
                editor.addEventListener('keydown', function(e) {
                    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                        e.preventDefault();
                        if (!modeToggle.disabled) {
                            modeToggle.click();
                        }
                    }
                });
            })();
        </script>
    </body>
    </html>
    """
    
    full_html = template.replace('{{TITLE}}', os.path.basename(filepath))\
                        .replace('{{CSS}}', get_css())\
                        .replace('{{CONTENT}}', html_content)\
                        .replace('{{RAW_MARKDOWN}}', raw_markdown_escaped)
    return full_html

# ---------------------------------------------------------------------------
# ページの受け渡し
#
# pywebview の load_html は WebView2 の NavigateToString を呼ぶため、文書の origin が
# about:blank になり file:// のサブリソース（ローカル画像）を一切読み込めない。
# そこで生成したHTMLを一時ファイルに書き出し、file:// URL として開く。
# 再描画は同じ一時ファイルを書き換えたうえで location.reload() させる
# （同一URLへの load_url は WebView2 が再ナビゲートせず、loaded イベントが復帰しない）。
# ---------------------------------------------------------------------------

_page_path = None


def _page_file():
    global _page_path
    if _page_path is None:
        fd, _page_path = tempfile.mkstemp(prefix='showmd_', suffix='.html')
        os.close(fd)
        atexit.register(_cleanup_page_file)
    return _page_path


def _cleanup_page_file():
    if _page_path:
        try:
            os.remove(_page_path)
        except Exception:
            pass


def write_page(html_text):
    """HTMLを一時ファイルへ書き出し、その file:// URL を返す。"""
    path = _page_file()
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_text)
    return Path(path).as_uri()


def reload_page(window):
    try:
        window.evaluate_js('location.reload()')
    except Exception:
        pass


class Api:
    def __init__(self, filepath=None):
        self._filepath = filepath
        self._window = None
        self._is_editing = False
        # ファイル監視スレッドと共有する。保存直後の二重リロードを防ぐ
        self._last_mtime = None

    def set_window(self, window):
        self._window = window

    def open_external_link(self, url):
        webbrowser.open(url)

    def set_editing(self, is_editing):
        self._is_editing = is_editing

    def save_content(self, content):
        if not self._filepath:
            return False
        try:
            with open(self._filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # 自動セーブしたら即座に再レンダリングしてビューに反映
            if self._window:
                self._is_editing = False
                write_page(convert_md_to_html(self._filepath))
                try:
                    self._last_mtime = os.path.getmtime(self._filepath)
                except Exception:
                    pass

                # 再読み込みによって現在のJavaScript実行コンテキストが破棄される前に、
                # save_contentの戻り値処理(JS Promiseの解決)を正常に完了させるため、
                # 別スレッドから僅かな遅延を入れて非同期でリロードします。
                def update_ui():
                    time.sleep(0.05)
                    if self._window:
                        reload_page(self._window)

                threading.Thread(target=update_ui, daemon=True).start()
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False


def watch_file(filepath, window, api):
    try:
        api._last_mtime = os.path.getmtime(filepath)
    except Exception:
        api._last_mtime = 0

    while True:
        time.sleep(0.5)
        if api._is_editing:
            continue
        try:
            current_mtime = os.path.getmtime(filepath)
            if current_mtime != api._last_mtime:
                api._last_mtime = current_mtime
                write_page(convert_md_to_html(filepath))
                reload_page(window)
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

    api = Api(filepath)
    window = webview.create_window(
        title=title,
        url=write_page(initial_html),
        js_api=api,
        width=800,
        height=600,
        min_size=(400, 300),
        text_select=True
    )
    api.set_window(window)

    def start_monitoring(win):
        if filepath:
            t = threading.Thread(target=watch_file, args=(filepath, win, api), daemon=True)
            t.start()

    webview.start(start_monitoring, window)

if __name__ == '__main__':
    main()
