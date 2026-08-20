#!/usr/bin/env python3
"""闸门脚本回归测试（schedule.py / assemble.py / coverage_check.py / splice.py）

设计原则：
  - CLI 级集成：通过 subprocess 调真实脚本，断言真实退出码与输出——测的就是
    管线实际依赖的行为（含 exit code：I1 拒发=3，FAIL=1/2）。
  - 合成夹具：两节点小树 + 手写块/fragment，全部落临时目录，不碰真实运行数据。
  - 无第三方依赖：`python3 phase2-paper/tests/test_gates.py` 直接跑；
    兼容 pytest（函数均为 test_*，无 fixture）。

背景：2026-08-20 评估指出"闸门代码零测试"是最大工程缺口；本套件是缺口①的
落地（金样由夹具充当，负测试保证坏输入必须让门变红）。
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHED = os.path.join(ROOT, 'phase2-paper', 'scheduler', 'schedule.py')
ASM = os.path.join(ROOT, 'phase2-paper', 'tools', 'assemble.py')
COV = os.path.join(ROOT, 'phase2-paper', 'tools', 'coverage_check.py')
SPL = os.path.join(ROOT, 'phase2-paper', 'tools', 'splice.py')

PY = sys.executable or 'python3'


def run(script, *args):
    p = subprocess.run([PY, script, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ── 夹具 ──────────────────────────────────────────────────────────────

def make_tree(d, policy='manual', headline='N01'):
    tree = {
        'paper_id': 't', 'headline_node': headline, 'confirm_policy': policy,
        'nodes': [
            {'id': 'N00', 'title': 'leaf lemma', 'statement': '建立 X。',
             'completion_test': 'X 成立。', 'deps': []},
            {'id': 'N01', 'title': 'top theorem', 'statement': '由 X 建立 Y。',
             'completion_test': 'Y 成立。', 'deps': ['N00']},
        ],
        'allowed_dependencies': [
            {'id': 'D1', 'kind': 'theorem', 'statement': '外部标准事实。'}],
    }
    p = os.path.join(d, 'tree.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False)
    return p


def write_block(d, nid, state, cite=(), body_extra=''):
    cites = ' '.join(f'由 {c} 的结论：引用之。' for c in cite)
    text = (f"【正文】\n我们在此证明 {nid}。{cites} 计算得 $a+b$。\n{body_extra}\n"
            f"【结论】\n{nid} 的目标成立 ({state})。\n"
            f"【依赖与未决】\n- 引用：{' '.join(cite) or '无'}\n")
    p = os.path.join(d, nid + '.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(text)
    return p


def write_frag(d, nid, body):
    p = os.path.join(d, nid + '.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(f'【块正文】\n{body}\n')
    return p


def write_json(d, name, obj):
    p = os.path.join(d, name)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
    return p


def instr(nodes=('N00', 'N01')):
    return {'meta': {'title': 'T', 'language': 'English', 'docclass': 'amsart'},
            'numbering': {'newtheorems': ['theorem', 'lemma']},
            'sections': [{'id': 'P0', 'title': 'Sec', 'nodes': list(nodes)}]}


# ── schedule.py ───────────────────────────────────────────────────────

def test_validate_pass():
    with tempfile.TemporaryDirectory() as d:
        rc, out = run(SCHED, 'validate', make_tree(d))
        assert rc == 0, out
        assert 'PASS' in out and 'ERROR' not in out, out


def test_validate_cycle():
    with tempfile.TemporaryDirectory() as d:
        p = make_tree(d)
        t = json.load(open(p, encoding='utf-8'))
        t['nodes'][0]['deps'] = ['N01']          # N00 <-> N01 成环
        json.dump(t, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        rc, out = run(SCHED, 'validate', p)
        assert rc == 1 and '有环' in out, out


def test_validate_dangling_dep():
    with tempfile.TemporaryDirectory() as d:
        p = make_tree(d)
        t = json.load(open(p, encoding='utf-8'))
        t['nodes'][1]['deps'] = ['NXX']
        json.dump(t, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        rc, out = run(SCHED, 'validate', p)
        assert rc == 1 and '不存在' in out, out


def test_taskbook_i1_refuses_with_exit_3():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        rc, out = run(SCHED, 'taskbook', tree, '--blocks', b, '--node', 'N01')
        assert rc == 3 and '拒发' in out, out


def test_taskbook_embeds_predecessor_conclusion():
    """I3：任务书的【前置结论】必须来自前置块真实落盘的【结论】原文。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'FIXED')
        rc, out = run(SCHED, 'taskbook', tree, '--blocks', b, '--node', 'N01')
        assert rc == 0, out
        assert '由 N00' in out and 'N00 的目标成立' in out, out


def test_status_i5_violation():
    """列了前置却绕开重推：N01 声明 deps=[N00] 但正文不提 N00。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'FIXED')
        write_block(b, 'N01', 'CONDITIONAL')      # 不引用 N00
        rc, out = run(SCHED, 'status', tree, '--blocks', b)
        assert rc == 0 and 'I5 违规' in out and 'N01' in out, out


def test_status_i3_violation():
    """前置未落盘却声称已证：N01 落盘称 PROVED-IN-PROJECT，N00 不存在。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N01', 'PROVED-IN-PROJECT', cite=('N00',))  # 引用空气
        rc, out = run(SCHED, 'status', tree, '--blocks', b)
        assert rc == 0 and 'I3 违规' in out, out


def test_status_i2_downgrade_propagation():
    """有效状态 = worst(自己, 前置)：N00 BLOCKED ⇒ N01 CONDITIONAL 降为 BLOCKED。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'BLOCKED')
        write_block(b, 'N01', 'CONDITIONAL', cite=('N00',))
        rc, out = run(SCHED, 'status', tree, '--blocks', b)
        assert rc == 0 and '降级' in out, out
        row = [ln for ln in out.splitlines() if ln.startswith('N01')][0]
        assert 'BLOCKED' in row, row


def test_status_empty_blocks_dir_must_not_crash():
    """回归：空 blocks 目录曾触发 NameError（bad 未定义）。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        rc, out = run(SCHED, 'status', tree, '--blocks', b)
        assert rc == 0, out
        assert 'NOT-LANDED' in out and '尚未闭合' in out, out


def test_next_frontier_and_gate_strictness():
    """I1 拒发 + I4 取严：policy=yolo 也不改高污染节点的 manual 档。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d, policy='yolo')
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'FIXED')
        rc, out = run(SCHED, 'next', tree, '--blocks', b)
        assert rc == 0 and 'N01' in out and 'I1' in out, out
        # 空目录：批 = L0 {N00}，N00 污染 1/2 ≥ 50% ⇒ manual（policy yolo 不得放宽）
        empty = os.path.join(d, 'empty'); os.makedirs(empty, exist_ok=True)
        rc, out = run(SCHED, 'next', tree, '--blocks', empty)
        assert rc == 0 and 'MANUAL' in out, out


# ── assemble.py ───────────────────────────────────────────────────────

FRAG_N00 = (r'\begin{lemma}\label{lem:N00} X holds. \end{lemma}'
            '\n' r'Proof of $x$.' )
FRAG_N01 = (r'\begin{equation}\label{eq:N01-x} y = x \end{equation}'
            '\n' r'By \ref{lem:N00} and \eqref{eq:N01-x}.')


def test_assemble_ok():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        ip = write_json(d, 'instr.json', instr())
        tex = os.path.join(d, 'paper.tex')
        rep = os.path.join(d, 'rep.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert body.count('\\newtheorem') == 2          # preamble 单源
        assert '\\label{sec:P0}' in body and 'lem:N00' in body
        assert json.load(open(rep, encoding='utf-8'))['ok'] is True


def test_assemble_rejects_topology_violation():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        ip = write_json(d, 'instr.json', instr(nodes=('N01', 'N00')))  # 反序
        rc, out = run(ASM, ip, fd, tree, os.path.join(d, 'p.tex'))
        assert rc == 1 and '节序违反' in out, out


def test_assemble_rejects_missing_fragment():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)                 # N01 缺文件
        ip = write_json(d, 'instr.json', instr())
        rc, out = run(ASM, ip, fd, tree, os.path.join(d, 'p.tex'))
        assert rc == 1 and '无 fragment' in out, out


def test_assemble_rejects_extra_fragment():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        ip = write_json(d, 'instr.json', instr(nodes=('N00',)))       # 少列 N01
        rc, out = run(ASM, ip, fd, tree, os.path.join(d, 'p.tex'))
        assert rc == 1 and '未列' in out, out


def test_assemble_rejects_unresolved_ref():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', r'See \ref{lem:NZZ}.')    # 悬空角标
        ip = write_json(d, 'instr.json', instr())
        rc, out = run(ASM, ip, fd, tree, os.path.join(d, 'p.tex'))
        assert rc == 1 and '角标未闭合' in out, out


def test_assemble_strips_stray_preamble():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', '\\newtheorem{theorem}{Theorem}\n' + FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        ip = write_json(d, 'instr.json', instr())
        tex = os.path.join(d, 'paper.tex')
        rep = os.path.join(d, 'rep.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0 and '剥除' in out, out
        body = open(tex, encoding='utf-8').read()
        assert body.count('\\newtheorem') == 2          # stray 已剥，preamble 单源
        assert json.load(open(rep, encoding='utf-8'))['dropped_preamble']['N00']


def test_assemble_applies_legacy_xref():
    """修复回归：xrefs 字段此前被组装器静默丢弃。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', 'By the conclusion of N00 we proceed to the main claim.')
        i = instr()
        i['xrefs'] = [{'at': 'N01', 'ref': 'N00', 'macro': '\\ref{lem:N00}'}]
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert 'conclusion of Lemma~\\ref{lem:N00}' in body
        r = json.load(open(rep, encoding='utf-8'))
        assert len(r['xrefs']['applied']) == 1 and not r['xrefs']['skipped']


def test_assemble_xref_find_protocol_requires_unique():
    """新协议（find/replace）：find 出现 2 次 → 报错拒换（不许盲换）。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', 'Use the conclusion of N00 here. Again the conclusion of N00 there.')
        i = instr()
        i['xrefs'] = [{'at': 'N01', 'find': 'the conclusion of N00',
                       'replace': 'the conclusion of Lemma~\\ref{lem:N00}'}]
        ip = write_json(d, 'instr.json', i)
        rc, out = run(ASM, ip, fd, tree, os.path.join(d, 'p.tex'))
        assert rc == 1 and 'find 短语出现 2 次' in out, out


def test_assemble_xref_unknown_prefix_skips_with_warning():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01 + '\nBy the conclusion of N00 we proceed.')
        i = instr()
        i['xrefs'] = [{'at': 'N01', 'ref': 'N00', 'macro': '\\ref{xxx:N00-weird}'}]
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0 and '前缀无法映射' in out, out
        r = json.load(open(rep, encoding='utf-8'))
        assert len(r['xrefs']['skipped']) == 1


def test_assemble_resolves_nref():
    """splicer v0.4 语义宏：有映射渲染 ref，无映射降级文本＋告警。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', 'Compare with \\Nref{N00} and \\Nref{N02}.')
        i = instr()
        i['labels'] = {'N00': 'lem:N00'}
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert 'Lemma~\\ref{lem:N00}' in body and '\\texttt{N02}' in body
        assert json.load(open(rep, encoding='utf-8'))['nrefs'] == {'resolved': 1, 'unresolved': 1}


def test_assemble_renders_bibliography():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        i = instr()
        i['bibliography'] = [
            {'key': 'D4', 'text': 'Ganatra--Pardon--Shende, arXiv:1809.03427, Theorem 1.20.'},
            {'key': 'D6', 'text': 'Jeffs--Yao--Zhao, arXiv:2307.08180.'}]
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert '\\begin{thebibliography}{99}' in body and '\\bibitem{D4}' in body
        assert json.load(open(rep, encoding='utf-8'))['bibliography']['entries'] == 2


def test_assemble_renders_intro_conclusion_text():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', FRAG_N01)
        i = instr()
        i['intro_text'] = 'This is the intro prose.'
        i['conclusion_text'] = '\\section*{Conclusion}\nThis is the conclusion prose.'
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex')
        rc, out = run(ASM, ip, fd, tree, tex)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert 'This is the intro prose.' in body and 'INTRO-TODO' not in body
        assert '\\section*{Conclusion}' in body and 'CONCL-TODO' not in body


def test_assemble_moves_deps_remarks_to_appendix():
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00 +
                   '\n\\begin{remark}\\label{rem:N00-deps}Invoke N01 stuff.\\end{remark}')
        write_frag(fd, 'N01', FRAG_N01)
        i = instr()
        i['deps_appendix'] = True
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert '\\section*{Dependency and Open-Item Ledger}' in body
        assert body.index('sec:deps-ledger') > body.index('sec:P0}')          # 附录在正文后
        assert 'rem:N00-deps' in body.split('sec:deps-ledger')[1]             # remark 只在附录
        r = json.load(open(rep, encoding='utf-8'))
        assert r['deps_appendix']['moved'] == ['N00']


def test_assemble_xref_bare_candidate_guarded_against_nref():
    r"""回归（v3 组装事故）：xref 裸 NXX 候选不得碰 \Nref{NXX} 内部子串。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', 'By the conclusion of \\Nref{N00} we proceed.')
        i = instr()
        i['labels'] = {'N00': 'lem:N00'}
        i['xrefs'] = [{'at': 'N01', 'ref': 'N00', 'macro': '\\ref{lem:N00}'}]
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert '\\Nref{Theorem' not in body and '\\Nref{Lemma' not in body   # 无双重包裹
        assert 'of Lemma~\\ref{lem:N00} we proceed' in body                    # \Nref 正常解析
        r = json.load(open(rep, encoding='utf-8'))
        assert len(r['xrefs']['skipped']) == 1     # 裸候选被守卫拦下→跳过


def test_assemble_nref_wrap_wraps_raw_mentions():
    """nref_wrap：存量 v0.3 裸提及机械包裹；label 内 NXX 不误包。"""
    with tempfile.TemporaryDirectory() as d:
        tree = make_tree(d)
        fd = os.path.join(d, 'frag'); os.makedirs(fd)
        write_frag(fd, 'N00', FRAG_N00)
        write_frag(fd, 'N01', 'By the conclusion of N00 and the N00 model in \\ref{lem:N00}.')
        i = instr()
        i['nref_wrap'] = True
        i['labels'] = {'N00': 'lem:N00'}
        ip = write_json(d, 'instr.json', i)
        tex = os.path.join(d, 'p.tex'); rep = os.path.join(d, 'r.json')
        rc, out = run(ASM, ip, fd, tree, tex, '--report', rep)
        assert rc == 0, out
        body = open(tex, encoding='utf-8').read()
        assert body.count('Lemma~\\ref{lem:N00}') == 2        # 两处均解析
        r = json.load(open(rep, encoding='utf-8'))
        assert r['nref_wrap']['wrapped'] == 2 and r['nrefs']['resolved'] == 2


# ── coverage_check.py ─────────────────────────────────────────────────

def cov_files(d, in_body, out_body):
    """夹具：结论段固定无状态词，状态标注由调用方放进正文——保证输入/输出计数对称。"""
    src = os.path.join(d, 'blk.md')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(f'【正文】\n{in_body}\n【结论】\n结论句。\n【依赖与未决】\n无\n')
    out = os.path.join(d, 'frag.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f'【块正文】\n{out_body}\n')
    return src, out


def test_coverage_pass():
    with tempfile.TemporaryDirectory() as d:
        body = r'证明 $x+y$ 与 \[ z = w \] 以及 \begin{lemma} L \end{lemma} 结论 (BLOCKED)。'
        src, out = cov_files(d, body, body + '\n' + '加长但不压缩 ' * 30)
        rc, _ = run(COV, 'segment', out, src)
        assert rc == 0


def test_coverage_catches_compression():
    """7 页事故的机械复刻：内容被摘要 ⇒ 必须红。"""
    with tempfile.TemporaryDirectory() as d:
        body = ('证明细节 ' * 200) + r' $x$ \[ y \] \begin{lemma} L \end{lemma} (BLOCKED)'
        src, out = cov_files(d, body, '摘要：结论成立 (BLOCKED)。')
        rc, o = run(COV, 'segment', out, src)
        assert rc == 1 and '长度比' in o, o


def test_coverage_catches_formula_drop():
    with tempfile.TemporaryDirectory() as d:
        body = r'$a$ $b$ \[ c \] \begin{lemma} L \end{lemma} (BLOCKED)'
        src, out = cov_files(d, body, r'$a$ \[ c \] \begin{lemma} L \end{lemma} (BLOCKED)'
                             + ' 补足长度的文字 ' * 40)
        rc, o = run(COV, 'segment', out, src)
        assert rc == 1 and 'inline_math 计数下降' in o, o


def test_coverage_paren_delimiter_regression():
    r"""N27 盲区回归：\(x+y\) 与 $x+y$ 等价计数；纯数字 \(5\) 豁免。"""
    with tempfile.TemporaryDirectory() as d:
        src_body = r'\(x+y\) \(u-v\) \(5\) (BLOCKED)'
        out_body = r'$x+y$ $u-v$ 5 (BLOCKED)' + ' 等价改写说明文字 ' * 10
        src, out = cov_files(d, src_body, out_body)
        rc, o = run(COV, 'segment', out, src)
        assert rc == 0, o                    # 2=2，纯数字不计


def test_coverage_status_variant_counting():
    """词表无关状态计数：丢 [STATUS: PROVED-IN-PROJECT] 变体必须红。"""
    with tempfile.TemporaryDirectory() as d:
        src_body = ('论证 ' * 80) + ' [STATUS: PROVED-IN-PROJECT]'
        out_body = ('论证 ' * 80)
        src, out = cov_files(d, src_body, out_body)
        rc, o = run(COV, 'segment', out, src)
        assert rc == 1 and 'six_state_tags 计数下降' in o, o


def test_coverage_allow_count_drop_flag():
    with tempfile.TemporaryDirectory() as d:
        body = r'$a$ $b$ (BLOCKED)'
        src, out = cov_files(d, body, r'$a$ (BLOCKED)' + ' 补长度 ' * 40)
        rc, o = run(COV, 'segment', out, src, '--allow-count-drop')
        assert rc == 0 and '豁免' in o, o


# ── splice.py（splice-v1 拼接链仍在库，防回归）────────────────────────

def make_sp_spec():
    return {'paper_id': 't', 'title': 'T', 'headline_block': 'N01',
            'conventions': {}, 'allowed_dependencies': [],
            'blocks': [{'id': 'N00', 'title': 'a', 'objective': 'o', 'completion_test': 'c',
                        'deps': [], 'allowed': []},
                       {'id': 'N01', 'title': 'b', 'objective': 'o', 'completion_test': 'c',
                        'deps': ['N00'], 'allowed': []}]}


def test_splice_ok_and_dup_warning():
    with tempfile.TemporaryDirectory() as d:
        sp = write_json(d, 'spec.json', make_sp_spec())
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        dup = '这是一句足够长的重复句用于跨块重复检测机制回归测试目的而写下的句子。' * 2
        write_block(b, 'N00', 'FIXED', body_extra=dup)
        write_block(b, 'N01', 'CONDITIONAL', cite=('N00',), body_extra=dup)
        rc, out = run(SPL, sp, b, os.path.join(d, 'a.md'), os.path.join(d, 'r.json'))
        assert rc == 0 and '跨块重复长句' in out, out


def test_splice_missing_block_fatal():
    with tempfile.TemporaryDirectory() as d:
        sp = write_json(d, 'spec.json', make_sp_spec())
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'FIXED')                   # N01 缺
        rc, out = run(SPL, sp, b, os.path.join(d, 'a.md'), os.path.join(d, 'r.json'))
        assert rc == 2 and '缺少块输出' in out, out


def test_splice_rejects_non_topological_order():
    with tempfile.TemporaryDirectory() as d:
        spec = make_sp_spec()
        spec['blocks'].reverse()                          # N01 在前
        sp = write_json(d, 'spec.json', spec)
        b = os.path.join(d, 'blocks'); os.makedirs(b)
        write_block(b, 'N00', 'FIXED')
        write_block(b, 'N01', 'CONDITIONAL', cite=('N00',))
        rc, out = run(SPL, sp, b, os.path.join(d, 'a.md'), os.path.join(d, 'r.json'))
        assert rc == 1 and '非拓扑序' in out, out


# ── paper_lint.py（S5/G3a 论文级自洽）────────────────────────────────

LINT = os.path.join(ROOT, 'phase2-paper', 'tools', 'paper_lint.py')


def lint_tex(d, body, name='p.tex'):
    p = os.path.join(d, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(body)
    return p


def test_lint_clean_paper_passes():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, '\\begin{lemma}\\label{lem:a} $x$ holds. \\end{lemma}\n'
                       'By \\ref{lem:a} and \\cite{D4} \\cite{D5}. [STATUS: BLOCKED]\n'
                       '\\begin{thebibliography}{9}\\bibitem{D4} A. \\bibitem{D5} B.\n'
                       '\\end{thebibliography}\n')
        rc, out = run(LINT, p)
        assert rc == 0, out


def test_lint_catches_duplicate_label():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, '\\label{eq:x}a\\label{eq:x}b\n')
        rc, out = run(LINT, p)
        assert rc == 1 and 'E1 label 重复' in out, out


def test_lint_catches_broken_ref():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, 'see \\ref{eq:ghost}.\n')
        rc, out = run(LINT, p)
        assert rc == 1 and 'E2' in out, out


def test_lint_catches_cite_without_bibitem():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, 'as in \\cite{D9}.\n')
        rc, out = run(LINT, p)
        assert rc == 1 and 'E3' in out, out


def test_lint_catches_unbalanced_env_and_dollars():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, '\\begin{lemma} $x \n')   # lemma 不闭合 + $ 奇数
        rc, out = run(LINT, p)
        assert rc == 1 and 'E4' in out and 'E5' in out, out


def test_lint_catches_double_wrapped_nref():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, 'see \\Nref{Lemma~\\ref{lem:a}}.\n')
        rc, out = run(LINT, p)
        assert rc == 1 and 'E6' in out and '双重包裹' in out, out


def test_lint_catches_stale_intro_counts():
    """E7（2026-08-21 实锤事故的闸门化）：引言统计 vs 全文 [STATUS:] 对账。"""
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, 'The ledger contains $5$ $\\mathrm{BLOCKED}$ entries '
                        'and $2$ $\\mathrm{FIXED}$ entries.\n'
                        '[STATUS: BLOCKED] [STATUS: BLOCKED] [STATUS: BLOCKED] [STATUS: FIXED]\n')
        rc, out = run(LINT, p)
        assert rc == 1 and 'E7' in out, out
        assert '声称 BLOCKED 5，实际' in out and '声称 FIXED 2，实际' in out, out


def test_lint_warns_on_uncited_bibitem_and_unused_eq_labels():
    with tempfile.TemporaryDirectory() as d:
        p = lint_tex(d, '\\begin{equation}\\label{eq:nobody} x \\end{equation}\n'
                        '\\begin{thebibliography}{9}\\bibitem{D4} A.\\end{thebibliography}\n')
        rc, out = run(LINT, p)
        assert rc == 0, out                      # 仅 warning
        assert 'W1' in out and 'W2' in out and 'W5' in out, out


# ── runner ────────────────────────────────────────────────────────────

def main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith('test_') and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  PASS  {name}')
        except AssertionError as e:
            failed += 1
            print(f'  FAIL  {name}\n        {e}')
        except Exception as e:                            # noqa: BLE001
            failed += 1
            print(f'  ERROR {name}\n        {type(e).__name__}: {e}')
    print(f'\n{len(tests) - failed}/{len(tests)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
