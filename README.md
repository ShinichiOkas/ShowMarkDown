# showmd (超軽量・単機能 Markdown Viewer)

`showmd` は、Windows環境で圧倒的に高速かつ軽量に動作することを目指して設計された、単機能のMarkdownビューアです。
Pythonの標準GUIライブラリである `tkinter` をベースとし、外部の巨大なGUIフレームワーク（PyQt, PySide, wxPython, Electronなど）を一切排除することで、実行ファイル（EXE）のサイズを極限まで小さくし、一瞬で起動するパフォーマンスを実現します。

---

## 🚀 特徴

- **超軽量・爆速起動**
  - Python標準の `tkinter` を使用し、外部依存を極限まで減らす（またはゼロにする）ことで、PyInstallerでビルドしたEXEファイルのサイズを最小化。
  - 起動にかかるオーバーヘッドを徹底的に排除し、CUIからストレスなく一瞬で立ち上がります。
- **極シンプルUI**
  - メニューバー、ステータスバー、ツールバーなどは一切存在しません。
  - ウィンドウ内には、Markdownが綺麗にレンダリングされた「表示エリア」と「スクロールバー」のみが配置されます。
- **コマンドライン特化**
  - `showmd.exe <ファイル名.md>` と引数を指定して起動するだけで、即座に対象ファイルを表示します。
  - ドラッグ＆ドロップや、「プログラムから開く」での起動にも対応予定です。

---

## 🛠 動作環境・設計アプローチ

### 技術スタック
- **言語**: Python 3.x
- **GUIライブラリ**: `pywebview`（Windows では OS 同梱の WebView2 を利用するため、GUIフレームワークを同梱しない）
- **パーサー**:
  - `Markdown` + `pymdown-extensions`（Pure Python）
  - 数式は `latex2mathml`（Pure Python）で MathML へ変換し、描画は WebView2 のネイティブ MathML に任せる
- **ビルドツール**: `PyInstaller` (EXE化)

いずれも Pure Python の軽量ライブラリのみで構成し、JavaScript ライブラリ（KaTeX / MathJax / highlight.js / Mermaid など）は一切同梱していません。

### 軽量化のためのビルド戦略
PyInstallerでEXE化する際、デフォルトでは不要なライブラリ（`tcl/tk` の不要ファイルや、未使用の標準モジュール）が同梱され、ファイルサイズが肥大化しがちです。
本プロジェクトでは、ビルドスクリプトや `.spec` ファイルをカスタマイズし、不要なインポートを徹底的に `exclude` することで、数MB〜10MB前後の超極小EXEファイルを目指します。

---

## 📂 ディレクトリ構成（予定）

```text
ShowMarkDown/
│
├── README.md           # 本ファイル
├── showmd.py           # メインソースコード（GUI・ファイル監視・編集/保存）
├── mdrender.py         # Markdown → HTML 変換層（拡張記法・数式・画像パス解決）
├── build.py            # 最適化されたPyInstallerビルド用スクリプト
├── test.md             # 表示確認用のサンプル（全対応記法を網羅）
├── sample-image.png    # test.md が参照する画像
└── docs/               # プロジェクトドキュメント（開発記録等）
```

---

## 💻 使い方（開発版 / EXE版）

### 1. 開発環境での実行
Pythonがインストールされている環境で、コマンドプロンプトやPowerShellから起動します。

```bash
python showmd.py sample.md
```

### 2. EXEファイルでの実行（Windows）
ビルド済みの `showmd.exe` を使用する場合：

```cmd
showmd.exe sample.md
```

---

## 📦 ビルド方法 (EXE化)

徹底的に最適化されたEXEファイルを生成するため、以下のコマンド（または専用のビルドスクリプト）を実行します。

```bash
# 最低限の依存関係のみを残してパッケージング
pyinstaller --onefile --noconsole --clean showmd.py
```
*(※不要なモジュールの除外オプションなどを盛り込んだビルドスクリプトを別途整備します)*

---

## 🎨 表示サポート

LLM が出力する Markdown をそのまま読めることを目標に、以下の記法へ対応しています。

### 基本

- [x] 見出し (`#` 〜 `######`)
- [x] 箇条書き・番号リスト（**2スペース字下げの入れ子**に対応）
- [x] 太字 (`**text**`)・斜体 (`*text*`)・打ち消し線 (`~~text~~`)
- [x] インラインコード (`` `code` ``)
- [x] コードブロック (```` ``` ````) — **リスト項目の中に置いても崩れません**
- [x] 水平線 (`---`)
- [x] リンク (`[text](url)`) — クリックで既定ブラウザ起動
- [x] 裸のURL (`https://...`) の自動リンク
- [x] テーブル（列の左/中央/右揃え対応）
- [x] 引用（ネスト可）
- [x] 改行の維持（GFM 相当）

### 拡張

- [x] タスクリスト (`- [ ]` / `- [x]`)
- [x] 脚注 (`[^1]`)
- [x] 定義リスト
- [x] 略語 (`*[MD]: Markdown`)
- [x] 目次 (`[TOC]`)
- [x] 属性リスト (`{: .class }`)
- [x] 生HTML（`<details>` / `<kbd>` / `<sub>` / `<sup>` など）
      — `<details>` と `<div>` の中身も Markdown として解釈されます

### 数式（LaTeX → MathML）

`$...$` `\(...\)` `$$...$$` `\[...\]` および ```` ```math ```` フェンスに対応します。

- `latex2mathml`（Pure Python）で **MathML** に変換し、WebView2 (Chromium) の
  ネイティブ MathML 描画に任せます。**JavaScript ライブラリを一切同梱しません**（KaTeX / MathJax 不使用）
- 完全オフラインで動作し、EXE サイズへの影響はごく小さい（約 +0.9MB）
- `latex2mathml` は数式が実際に現れるまで import しないため、数式のない文書の起動速度は落ちません
- コードブロック・インラインコードの中の `$` は数式として扱いません
- 通貨表記（`$5 から $10`）も数式にしません。リテラルの `$` は `\$` と書きます
- 解釈できない数式は、黙って消さずに元の LaTeX をそのまま表示します

### 画像

MD ファイルからの相対パスで指定できます（`![alt](img/foo.png)`）。

> **実装メモ**: `pywebview` の `load_html` は WebView2 の `NavigateToString` を呼ぶため、
> 文書の origin が `about:blank` になり `file://` の画像を一切読み込めません。
> そのため生成した HTML を一時ファイルへ書き出し、`file://` URL として開いています。
> 再描画は同じ一時ファイルを書き換えて `location.reload()` させます
> （同一 URL への `load_url` は WebView2 が再ナビゲートしません）。

## Appendix

- 2026年6月1日：編集機能を設けました
- 2026年7月27日：LaTeX数式・画像・GFM記法・脚注・目次などへ対応を拡大しました