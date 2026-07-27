"""Markdown -> HTML 変換層。

showmd.py（GUI層）から切り離してある。LLMが出力しがちなMD記法を広くカバーする:

- Python-Markdown 標準拡張: tables / fenced_code / footnotes / def_list / abbr /
  toc / attr_list / nl2br / sane_lists / md_in_html
- 独自拡張: 打ち消し線 (~~text~~) / タスクリスト ([ ] [x]) / 裸URLの自動リンク
- LaTeX数式: $$...$$ , \\[...\\] , \\(...\\) , $...$ , ```math フェンス を
  latex2mathml で MathML に変換する（JS不要・完全オフライン）
- 画像: 相対パスを file:// 絶対URLへ書き換える

数式は「Pythonの外部JSライブラリを持ち込まない」という本プロジェクトの方針に沿い、
WebView2(Chromium) がネイティブ対応する MathML Core で描画する。
"""

import html
import re
import xml.etree.ElementTree as etree
from pathlib import Path
from urllib.parse import unquote

import markdown
from markdown.extensions import Extension
from markdown.extensions.toc import slugify_unicode
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import AtomicString

# ---------------------------------------------------------------------------
# LaTeX -> MathML
# ---------------------------------------------------------------------------

_converter = None
_converter_loaded = False


def _get_converter():
    """latex2mathml は import に約90msかかる。数式が実際に現れるまで読み込まない。"""
    global _converter, _converter_loaded
    if not _converter_loaded:
        _converter_loaded = True
        try:
            from latex2mathml.converter import convert
            _converter = convert
        except Exception:  # latex2mathml 未導入でも本体は動かす
            _converter = None
    return _converter


def render_math(latex, display):
    """LaTeX文字列を MathML に変換する。失敗しても原文を失わない。"""
    source = latex.strip()
    if not source:
        return ''

    convert = _get_converter()
    if not convert:
        return '<code class="math-raw">%s</code>' % html.escape(source)

    try:
        mathml = convert(source, display='block' if display else 'inline')
    except Exception:
        # 解釈できない数式は元のLaTeXをそのまま見せる（黙って消さない）
        return '<code class="math-error" title="数式を解釈できませんでした">%s</code>' % html.escape(source)

    if display:
        return '<div class="math-block">%s</div>' % mathml
    return '<span class="math-inline">%s</span>' % mathml


# ```math / ```latex / ```tex フェンスブロック。
# fenced_code より先に走らせて、コードブロックとして処理されるのを防ぐ。
_MATH_FENCE_RE = re.compile(
    r'^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})[ ]*(?:math|latex|tex)[ ]*\n'
    r'(?P<body>.*?)'
    r'^(?P=indent)(?P=fence)[ ]*$',
    re.MULTILINE | re.DOTALL,
)


class MathFencePreprocessor(Preprocessor):
    """```math フェンスを MathML に変換して stash する。"""

    def run(self, lines):
        text = '\n'.join(lines)

        def repl(m):
            placeholder = self.md.htmlStash.store(render_math(m.group('body'), True))
            return '\n\n%s%s\n\n' % (m.group('indent'), placeholder)

        return _MATH_FENCE_RE.sub(repl, text).split('\n')


# インライン/ディスプレイ数式のスキャナ。
# 「インラインコードスパン」も同じ正規表現で拾い、コード内の $ を数式にしないための
# 通過枠として使う（先頭の code グループにマッチしたら何もせず素通しする）。
# 空行を跨いだ数式は認めない（閉じ忘れた $$ が文書の残り全部を飲み込むのを防ぐ）
_NO_BLANK_LINE = r'(?:(?!\n[ \t]*\n).)+?'

_MATH_SCAN_RE = re.compile(
    r'(?P<esc>\\[\\$])'                                        # \$ や \\ のエスケープ
    r'|(?P<code>(?<!`)(?P<ticks>`+)(?!`).+?(?<!`)(?P=ticks)(?!`))'  # `code`
    r'|(?P<dollars>\$\$(?P<dollars_body>' + _NO_BLANK_LINE + r')\$\$)'   # $$ ... $$
    r'|(?P<bracket>\\\[(?P<bracket_body>' + _NO_BLANK_LINE + r')\\\])'   # \[ ... \]
    r'|(?P<paren>\\\((?P<paren_body>' + _NO_BLANK_LINE + r')\\\))'       # \( ... \)
    r'|(?P<single>(?<![\\$\d])\$(?![\s$])(?P<single_body>[^$\n]*?[^\s\\$])\$(?!\d))',  # $ ... $
    re.DOTALL,
)

# 通貨表記（$1,200 のような数字だけの中身）は数式として扱わない
_CURRENCY_ONLY_RE = re.compile(r'^[\d,.\s]+$')


class MathInlinePreprocessor(Preprocessor):
    """$$...$$ / \\[...\\] / \\(...\\) / $...$ を MathML に変換して stash する。

    superfences(25) の後に走るため、コードフェンスの中身は既に stash 済みで安全。
    インラインコードスパンだけは自前でスキップする。
    """

    def run(self, lines):
        text = '\n'.join(lines)

        def repl(m):
            if m.group('code') is not None:
                return m.group(0)
            if m.group('esc') is not None:
                # Python-Markdown は $ をエスケープ対象に持たないので、\$ は自前で外す
                return '$' if m.group('esc') == r'\$' else m.group(0)

            if m.group('dollars') is not None:
                body, display = m.group('dollars_body'), True
            elif m.group('bracket') is not None:
                body, display = m.group('bracket_body'), True
            elif m.group('paren') is not None:
                body, display = m.group('paren_body'), False
            else:
                body, display = m.group('single_body'), False
                if _CURRENCY_ONLY_RE.match(body):
                    return m.group(0)

            placeholder = self.md.htmlStash.store(render_math(body, display))

            # ディスプレイ数式が単独行なら、独立したブロックとして出力させる
            if display and _is_own_line(text, m.start(), m.end()):
                return '\n\n%s\n\n' % placeholder
            return placeholder

        return _MATH_SCAN_RE.sub(repl, text).split('\n')


def _is_own_line(text, start, end):
    """マッチが（空白を除いて）その行を占有しているか。"""
    line_start = text.rfind('\n', 0, start) + 1
    line_end = text.find('\n', end)
    if line_end == -1:
        line_end = len(text)
    return not text[line_start:start].strip() and not text[end:line_end].strip()


# ---------------------------------------------------------------------------
# GFM 系の独自拡張
# ---------------------------------------------------------------------------

# LLM は <details> や <div align="center"> の中に素の Markdown を書いてくる。
# md_in_html は markdown 属性が無いと中身を生HTML扱いするので、自前で補う。
_MD_IN_HTML_RE = re.compile(
    r'<(?P<tag>details|div)\b(?![^>]*\bmarkdown\s*=)(?P<attrs>[^>]*)>',
    re.IGNORECASE,
)


class MarkdownInHtmlPreprocessor(Preprocessor):
    def run(self, lines):
        text = '\n'.join(lines)
        text = _MD_IN_HTML_RE.sub(
            lambda m: '<%s markdown="1"%s>' % (m.group('tag'), m.group('attrs')), text)
        return text.split('\n')


_DEL_RE = r'~~(?!\s)(.+?)(?<!\s)~~'


class DelInlineProcessor(InlineProcessor):
    """~~打ち消し線~~"""

    def handleMatch(self, m, data):
        el = etree.Element('del')
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


# 裸URLの自動リンク。末尾の句読点・閉じ括弧はURLから外す。
_BARE_LINK_RE = (
    r'(?<![\w>"\'=/])'
    r'((?:https?://|www\.)[^\s<>\[\]{}"\'`]*[^\s<>\[\]{}"\'`.,;:!?)\u3002\u3001])'
)


class BareLinkInlineProcessor(InlineProcessor):
    """http(s):// や www. で始まる裸のURLをリンクにする。"""

    def handleMatch(self, m, data):
        url = m.group(1)
        el = etree.Element('a')
        el.set('href', url if url.startswith('http') else 'http://' + url)
        # AtomicString にしないと、生成した <a> のテキストが再度インライン処理され
        # 同じパターンに無限に再マッチする
        el.text = AtomicString(url)
        return el, m.start(0), m.end(0)


_TASK_ITEM_RE = re.compile(r'^\[([ xX])\][ \t]+')


class TaskListTreeprocessor(Treeprocessor):
    """- [ ] / - [x] をチェックボックスに変換する。"""

    def run(self, root):
        for parent in root.iter():
            if parent.tag not in ('ul', 'ol'):
                continue

            found = False
            for li in parent:
                if li.tag != 'li':
                    continue
                if self._convert(li):
                    found = True

            if found:
                _add_class(parent, 'task-list')

    def _convert(self, li):
        # li 直下にテキストがある場合と、<p> でラップされている場合の両方に対応
        for target in (li, li[0] if len(li) and li[0].tag == 'p' else None):
            if target is None:
                continue
            m = _TASK_ITEM_RE.match(target.text or '')
            if not m:
                continue

            rest = (target.text or '')[m.end():]
            box = etree.Element('input')
            box.set('type', 'checkbox')
            box.set('disabled', 'disabled')
            if m.group(1).lower() == 'x':
                box.set('checked', 'checked')
            box.tail = rest

            target.text = ''
            target.insert(0, box)
            _add_class(li, 'task-list-item')
            return True
        return False


def _add_class(el, name):
    existing = el.get('class')
    el.set('class', '%s %s' % (existing, name) if existing else name)


class ShowmdExtension(Extension):
    """showmd 独自の拡張一式。"""

    def extendMarkdown(self, md):
        # fenced_code(25) より前に ```math を処理し、その後に一般の数式を処理する
        md.preprocessors.register(MathFencePreprocessor(md), 'showmd_math_fence', 26)
        md.preprocessors.register(MathInlinePreprocessor(md), 'showmd_math', 24)
        # md_in_html の html_block(20) より前、fenced_code(25) より後
        md.preprocessors.register(MarkdownInHtmlPreprocessor(md), 'showmd_md_in_html', 23)

        md.inlinePatterns.register(DelInlineProcessor(_DEL_RE, md), 'showmd_del', 65)
        # link(160) などが先に URL を消費した後に走らせる
        md.inlinePatterns.register(BareLinkInlineProcessor(_BARE_LINK_RE, md), 'showmd_bare_link', 8)

        # inline treeprocessor(20) の後
        md.treeprocessors.register(TaskListTreeprocessor(md), 'showmd_tasklist', 15)


_EXTENSIONS = [
    'tables',
    # 標準の fenced_code はリスト項目の中のコードフェンスを扱えない
    # （「1. 手順」→コードブロック がインラインコードに潰れる）ため superfences を使う
    'pymdownx.superfences',
    'footnotes',
    'def_list',
    'abbr',
    'toc',
    'attr_list',
    'nl2br',
    'sane_lists',
    'md_in_html',
    ShowmdExtension(),
]

_EXTENSION_CONFIGS = {
    'footnotes': {'BACKLINK_TEXT': '↩'},
    # 日本語見出しでも意味のあるアンカーIDになるよう Unicode を残す
    'toc': {'permalink': False, 'slugify': slugify_unicode},
}


# ---------------------------------------------------------------------------
# 画像の相対パス解決
# ---------------------------------------------------------------------------

_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)
_URL_SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:')
_WIN_DRIVE_RE = re.compile(r'^[a-zA-Z]:[\\/]')


def resolve_local_url(src, base_dir):
    """相対パスの画像を file:// 絶対URLに書き換える。

    load_html(NavigateToString) は origin が about:blank になり file:// を
    読み込めないため、showmd.py 側は一時HTMLファイルを load_url で開いている。
    """
    if base_dir is None:
        return src

    raw = html.unescape(src).strip()
    if not raw or raw.startswith('#') or raw.startswith('//'):
        return src
    # Windows のドライブレター (C:\...) をURLスキームと誤認しない
    if _URL_SCHEME_RE.match(raw) and not _WIN_DRIVE_RE.match(raw):
        return src

    try:
        # 絶対パスが渡された場合は Path の / 演算子が base_dir を捨てて絶対側を採る
        return (Path(base_dir) / unquote(raw)).resolve().as_uri()
    except Exception:
        return src


def rewrite_image_paths(html_text, base_dir):
    if base_dir is None:
        return html_text

    def repl(m):
        return '%s%s%s%s' % (m.group(1), m.group(2),
                             html.escape(resolve_local_url(m.group(3), base_dir), quote=True),
                             m.group(2))

    return _IMG_SRC_RE.sub(repl, html_text)


# ---------------------------------------------------------------------------
# 公開API
# ---------------------------------------------------------------------------

def render(text, base_dir=None):
    """Markdown テキストを HTML 断片に変換する。"""
    md = markdown.Markdown(
        extensions=_EXTENSIONS,
        extension_configs=_EXTENSION_CONFIGS,
        # LLM は入れ子リストを2スペース字下げで書くことが圧倒的に多い。
        # 既定の4だと入れ子にならず平列に潰れるため2にしている。
        tab_length=2,
    )
    body = md.convert(text)
    return rewrite_image_paths(body, base_dir)
