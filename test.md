# テスト用マークダウンファイル (showmd.exe)

このファイルは `showmd` の表示および自動更新機能（ホットリロード）の検証用ファイルです。
エディタでこのファイルを変更・保存すると、起動中の `showmd` の表示が自動的に即時更新されます。

---

## 📊 テーブル（表）のサポート

| 機能名 | ステータス | 依存関係 |
| :--- | :---: | :--- |
| **超軽量設計** | ✅ | 標準ライブラリ + `pywebview` / `markdown` |
| **テーブル表示** | ✅ | markdown.extensions.tables |
| **自動更新** | ✅ | ポーリング監視 (0.5秒間隔) |
| **外部リンク起動** | ✅ | JavaScript + python-webbrowser |

---

## 💻 コードの表示

インラインコード： `pip install pywebview markdown`

### コードブロック

```python
import webview

def main():
    # ウィンドウの作成と起動
    window = webview.create_window('showmd', 'https://pywebview.flowrl.com')
    webview.start()

if __name__ == '__main__':
    main()
```

---

## 🔗 外部リンクのテスト

以下のリンクをクリックすると、Windowsの標準（既定）ブラウザで開きます。

- [Google (HTTPS)](https://www.google.com)
- [pywebview 公式ドキュメント](https://pywebview.flowrl.com)

---

## 📝 リストのテスト

- 箇条書きレベル 1
  - 箇条書きレベル 2
    - 箇条書きレベル 3
- 通常の箇条書き
