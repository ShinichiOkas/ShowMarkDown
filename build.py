import argparse
import subprocess
import sys
import os
import shutil
import tempfile

# --install: ビルドした exe を PATH の通った所へ置く。決定順:
#   --install-dir 引数 > 環境変数 AGENT_INSTALL_DIR > 既定 %USERPROFILE%\.local\bin (= ~/.local/bin)
# C:\bin などマシン固有の置き先はリポジトリの既定に焼き込まない(環境変数で各自が与える)。
# 既定 ~/.local/bin は移植性のある値(OSS 化・クロス PF でも破綻しない)。
def resolve_install_dir(install_dir_arg):
    if install_dir_arg:
        return install_dir_arg
    env = os.environ.get('AGENT_INSTALL_DIR')
    if env:
        return env
    return os.path.join(os.path.expanduser('~'), '.local', 'bin')


def main():
    parser = argparse.ArgumentParser(description='Build showmd.exe')
    parser.add_argument('--install', action='store_true',
                        help='built exe を PATH の通った所へ置く')
    parser.add_argument('--install-dir', default=None,
                        help='置き先(省略時: env AGENT_INSTALL_DIR > 既定 ~/.local/bin)')
    args = parser.parse_args()
    # 仮想環境の python のパスを取得
    # pyinstaller.exe（pip が生成するコンソールスクリプトのランチャー）はインストール時点の
    # python.exe の絶対パスを埋め込む。venv を OneDrive 配下など別パスで作成した後に
    # プロジェクトを移動すると、埋め込まれたパスが存在しなくなり
    # "Fatal error in launcher" で起動できなくなる。venv 本体の python.exe を
    # `-m PyInstaller` で呼べばこの問題を避けられる。
    if os.name == 'nt':
        python_bin = os.path.join('.venv', 'Scripts', 'python.exe')
    else:
        python_bin = os.path.join('.venv', 'bin', 'python')

    if not os.path.exists(python_bin):
        print(f"Error: Python venv not found at {python_bin}. Please install dependencies first.")
        sys.exit(1)

    print("Building showmd.exe...")

    # 不要な標準ライブラリのモジュールや、webviewで使用しないコンポーネントを除外する
    excludes = [
        'unittest', 'pdb', 'difflib', 'doctest',
        'sqlite3', 'pygments',  # markdownのコードハイライトで使われるが、今回は標準スタイルでいくので除外
    ]

    # OneDriveの同期競合による PermissionError を回避するため、
    # ビルド作業用ディレクトリと出力先をシステムのテンポラリフォルダに設定する
    temp_dir = tempfile.gettempdir()
    workpath = os.path.join(temp_dir, 'showmd_build')
    distpath = os.path.join(temp_dir, 'showmd_dist')

    # 以前の一時フォルダが残っていれば削除しておく
    for path in [workpath, distpath]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"Warning: Failed to clean old temp path {path}: {e}")

    cmd = [
        python_bin,
        '-m', 'PyInstaller',
        '--onefile',
        '--clean',
        '-n', 'showmd',
        '--workpath', workpath,
        '--distpath', distpath,
        # latex2mathml は unimathsymbols.txt をランタイムに読むため、
        # データファイルごと同梱する必要がある（--collect-all で一括収集）
        '--collect-all', 'latex2mathml',
        # Markdown拡張は文字列名で動的ロードされ PyInstaller が静的解析で見つけられない。
        # 明示的に収集しないと実行時に ModuleNotFoundError になる。
        '--collect-submodules', 'pymdownx',
        '--collect-submodules', 'markdown.extensions',
    ]

    for ex in excludes:
        cmd.extend(['--exclude-module', ex])

    cmd.append('showmd.py')

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("Build successful!")
        exe_path = os.path.join(distpath, 'showmd.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Generated EXE size: {size_mb:.2f} MB")
            
            # dist からカレントディレクトリにコピーする
            dest_path = os.path.join('.', 'showmd.exe')
            try:
                # すでに存在するEXEファイルがある場合は上書きコピー
                shutil.copy2(exe_path, dest_path)
                print(f"Copied to {dest_path}")
            except Exception as e:
                print(f"Error copying {exe_path} to {dest_path}: {e}")

            # --install: PATH の通った所へ置く(決定順は resolve_install_dir を参照)
            if args.install:
                install_dir = resolve_install_dir(args.install_dir)
                try:
                    os.makedirs(install_dir, exist_ok=True)
                    install_path = os.path.join(install_dir, 'showmd.exe')
                    shutil.copy2(exe_path, install_path)
                    print(f"Installed: {install_path}")
                    path_dirs = [d.rstrip(os.sep) for d in os.environ.get('PATH', '').split(os.pathsep)]
                    if install_dir.rstrip(os.sep) not in path_dirs:
                        print(f"WARN: {install_dir} is not on PATH (this process)")
                except Exception as e:
                    print(f"Error installing to {install_dir}: {e}")
    else:
        print("Build failed.")

    # ビルド完了後に一時フォルダをクリーンアップ
    for path in [workpath, distpath]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception:
                pass

    if result.returncode != 0:
        sys.exit(result.returncode)

if __name__ == '__main__':
    main()
