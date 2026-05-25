import subprocess
import sys
import os
import shutil

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

    cmd = [
        pyinstaller_bin,
        '--onefile',
        '--clean',
        '-n', 'showmd',
    ]

    for ex in excludes:
        cmd.extend(['--exclude-module', ex])

    cmd.append('showmd.py')

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("Build successful!")
        exe_path = os.path.join('dist', 'showmd.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Generated EXE size: {size_mb:.2f} MB")
            
            # dist からカレントディレクトリにコピーする
            dest_path = os.path.join('.', 'showmd.exe')
            shutil.copy2(exe_path, dest_path)
            print(f"Copied to {dest_path}")
    else:
        print("Build failed.")
        sys.exit(result.returncode)

if __name__ == '__main__':
    main()
