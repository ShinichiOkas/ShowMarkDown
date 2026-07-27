# テスト用マークダウンファイル (showmd.exe)

このファイルは `showmd` の表示および自動更新機能（ホットリロード）の検証用ファイルです。
エディタでこのファイルを変更・保存すると、起動中の `showmd` の表示が自動的に即時更新されます。

[TOC]

---

## 📊 テーブル（表）のサポート

| 機能名 | ステータス | 依存関係 |
| :--- | :---: | :--- |
| **超軽量設計** | ✅ | 標準ライブラリ + `pywebview` / `markdown` |
| **テーブル表示** | ✅ | markdown.extensions.tables |
| **自動更新** | ✅ | ポーリング監視 (0.5秒間隔) |
| **外部リンク起動** | ✅ | JavaScript + python-webbrowser |
| **数式表示** | ✅ | latex2mathml → MathML |

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

コードブロックの中の `$x$` や `\[y\]` は数式に変換されません。

### リスト項目の中のコードブロック

1. 依存関係をインストールする

   ```bash
   pip install -r requirements.txt
   ```

2. 起動する

   ```bash
   python showmd.py test.md
   ```

---

## 🧮 数式（LaTeX → MathML）

インライン数式は `$...$` または `\(...\)` で書きます。
質量とエネルギーの等価性は $E = mc^2$ で表され、\( \alpha + \beta = \gamma \) のようにも書けます。

ディスプレイ数式は `$$...$$`：

$$
\int_{0}^{\infty} e^{-x^{2}}\,dx = \frac{\sqrt{\pi}}{2}
$$

`\[...\]` 形式：

\[ \sum_{i=1}^{n} i = \frac{n(n+1)}{2} \]

` ```math ` フェンス形式：

```math
\begin{pmatrix} a & b \\ c & d \end{pmatrix}
\begin{pmatrix} x \\ y \end{pmatrix}
=
\begin{pmatrix} ax + by \\ cx + dy \end{pmatrix}
```

通貨表記は数式として扱われません（例：価格は $5 から $10 の間）。
`\$` と書けばリテラルの \$100 になります。

---

## 🖼 画像

MDファイルからの相対パスで指定できます。

![サンプル画像](sample-image.png)

---

## ✅ タスクリスト

- [x] Markdown のレンダリング
- [x] LaTeX 数式の MathML 変換
- [x] 相対パス画像の表示
- [ ] 今後の課題

---

## 📝 リストと装飾のテスト

- 箇条書きレベル 1
  - 箇条書きレベル 2
    - 箇条書きレベル 3
- 通常の箇条書き

**太字** / *斜体* / ~~打ち消し線~~ / `インラインコード` / H<sub>2</sub>O / x<sup>2</sup>

キー操作: <kbd>Ctrl</kbd> + <kbd>S</kbd> で保存

---

## 🔗 外部リンクのテスト

以下のリンクをクリックすると、Windowsの標準（既定）ブラウザで開きます。

- [Google (HTTPS)](https://www.google.com)
- [pywebview 公式ドキュメント](https://pywebview.flowrl.com)
- 裸のURLも自動リンクされます: https://github.com/

---

## 📚 脚注・定義リスト・略語

Markdown ビューアには脚注も書けます[^1]。

[^1]: 脚注はドキュメント末尾にまとめて表示されます。

MathML
:   数式を記述するためのマークアップ言語。WebView2 がネイティブ対応している。

*[MD]: Markdown

MD 記法の略語にはマウスオーバーで説明が出ます。

---

## 📦 折りたたみ（生HTML）

<details>
<summary>クリックで開く</summary>

中身も **Markdown** として解釈されます。

- リストも書けます
- 数式も書けます: $\sqrt{2}$

</details>

---

## 💬 引用

> 引用文です。
>
> > ネストした引用もできます。
