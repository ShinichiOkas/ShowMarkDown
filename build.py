import subprocess
import sys
import os
import shutil
import tempfile

def main():
    # 仮想環境の python と pyinstaller のパスを取得
    if os.name == 'nt':
        pyinstaller_bin = os.path.join('.venv', 'Scripts', 'pyinstaller.exe')
    else:
        pyinstaller_bin = os.path.join('.venv', 'bin', 'pyinstaller')

    if not os.path.exists(pyinstaller_bin):
        print(f"Error: PyInstaller not found at {pyinstaller_bin}. Please install dependencies first.")
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
        pyinstaller_bin,
        '--onefile',
        '--clean',
        '-n', 'showmd',
        '--workpath', workpath,
        '--distpath', distpath,
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
