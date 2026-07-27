---
name: showmd / pywebview + WebView2 の実測済み制約
description: load_html の origin 問題・load_url の再ナビゲート挙動・file:// URL のクエリ・PyInstaller の動的ロード検出漏れ。すべて実測で確定した事実
type: reference
maturity: draft
proposed_by: ai
confirmed_by: 師匠
created_at: 2026-07-28
verified_with: pywebview 6.2.1 / WebView2 (Chrome 150) / PyInstaller 6.20.0 / Windows 11
---

ShowMarkDown で実測して確定した、pywebview + WebView2 + PyInstaller の制約。
いずれもドキュメントや型シグネチャからは読み取れず、プローブでのみ判明した。

## 1. `load_html` では `file://` のサブリソースを読めない

pywebview の `Window.load_html` は edgechromium で `CoreWebView2.NavigateToString` を呼ぶ
（`webview/platforms/edgechromium.py`）。この文書の origin は **about:blank** になり、
Chromium は about:blank 文書からの `file://` サブリソース読み込みを**ブロック**する。

- 実測: `<img src="file:///.../probe.png">` → `naturalWidth: 0`
- つまり **ローカル画像は `load_html` のままでは絶対に表示できない**
- 併せて `NavigateToString` には文字列長 2MB 程度の上限がある

**対処（採用した方式）**: 生成HTMLを一時ファイルへ書き出し、`file://` URL として
`create_window(url=...)` で開く。origin が `file://` になり、`file://` 画像が読める。
`pywebview.api` は `file://` origin でも生存する（実測確認済み）。

なお `is_local_url()` は `file://` で始まるURLに False を返すため、
`load_url` を使っても pywebview の内蔵HTTPサーバは起動しない（＝軽いまま）。

## 2. 同一URLへの `load_url` は再ナビゲートせずハングする

一時ファイルを書き換えて同じ URL を `load_url` しても、WebView2 は
`Source` が同一のため再ナビゲートしない。pywebview 側は `events.loaded` を
`clear()` した後 `set()` されないまま残り、次の `evaluate_js` が15秒待って
`WebViewException('Main window failed to start')` を投げ、ウィンドウが閉じずハングする。

**対処（採用した方式）**: 一時ファイルを書き換えたうえで
`window.evaluate_js('location.reload()')`。`loaded` を clear しないので
`evaluate_js` も通り、再読込後も `pywebview.api` が生きる。

代替として「毎回別ファイル名で `load_url`」も動作するが、一時ファイルが増える。

## 3. `file://` URL にクエリ文字列を付けると空ページになる

キャッシュバスターとして `file:///C:/.../page.html?v=2` を開くと、
Windows ではファイルが解決できず**空のページ**になる（DOM が空）。使えない。

## 4. WebView2 は MathML Core をネイティブ描画する

`<math>` 要素はレイアウトボックスを持って正しく描画される（Chrome 150 で確認）。
KaTeX / MathJax を同梱せず、Python 側で MathML へ変換するだけで数式が出る。

## 5. PyInstaller は文字列名で動的ロードされる Markdown 拡張を検出できない

`markdown.Markdown(extensions=['pymdownx.superfences', ...])` のように
**文字列で指定した拡張**は静的解析に引っかからず、EXE に同梱されない。
実行時に `ModuleNotFoundError: No module named 'pymdownx'` で落ちる（実際に踏んだ）。

```
--collect-submodules pymdownx
--collect-submodules markdown.extensions
```

また `latex2mathml` は `unimathsymbols.txt`（216KB）を
`os.path.dirname(os.path.realpath(__file__))` から実行時に読むため、
`--collect-all latex2mathml` でデータファイルごと収集する必要がある。

## 6. 起動コストの実測値

| 項目 | 値 |
|---|---|
| `import markdown` | 約 60ms |
| `import latex2mathml.converter` | 約 94ms（数式が現れるまで遅延ロードして回避） |
| Markdown拡張10個の import 合計 | 約 11ms |
| EXE 起動 → ウィンドウ表示 | 約 1.4 秒 |

`latex2mathml` の import が突出して重い。`mdrender._get_converter()` で遅延させている。
