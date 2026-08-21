#!/usr/bin/env python3
"""Generate an SVG of the Seidel dep-tree DAG for the talk slides.
Layout: longest-path layering, left→right columns, up to 3 rows.
Color: by declared status (ledger), per STATUS.md semantics."""
import json, ast, collections, html

d = json.load(open('runs/pretest/seidel/dep-tree.v3.json'))
nodes = {n['id']: n for n in d['nodes']}
for n in nodes.values():
    n['deps'] = ast.literal_eval(n['deps']) if isinstance(n['deps'], str) else n['deps']

# longest-path layering
layer = {}
def get_layer(nid):
    if nid in layer: return layer[nid]
    deps = nodes[nid]['deps']
    layer[nid] = 0 if not deps else 1 + max(get_layer(x) for x in deps)
    return layer[nid]
for nid in nodes: get_layer(nid)

by_layer = collections.defaultdict(list)
for nid, l in layer.items(): by_layer[l].append(nid)
for l in by_layer: by_layer[l].sort(key=lambda x: int(x[1:]))
maxL = max(by_layer); maxW = max(len(v) for v in by_layer.values())

# declared status: parse the machine-generated STATUS.md snapshot
declared = {}
for line in open('runs/pretest/seidel/STATUS.md'):
    p = line.split()
    if len(p) >= 4 and p[0].startswith('N') and p[0][1:].isdigit():
        declared[p[0]] = p[2]  # N00 0 FIXED FIXED —
STATUS_MAP = {  # unify wording
    'FIXED': 'FIXED', 'BLOCKED': 'BLOCKED', 'CONDITIONAL': 'CONDITIONAL',
    'CANDIDATE': 'CANDIDATE', 'PROVED': 'FIXED', 'IMPORTED': 'FIXED',
}
COLOR = {
    'FIXED': ('#2e6e4e', '#e7f1eb'),
    'CONDITIONAL': ('#9a6b1f', '#f7efdd'),
    'CANDIDATE': ('#14406b', '#e8eef6'),
    'BLOCKED': ('#b5432a', '#f8eae5'),
}

# geometry: columns left->right
NL, NW = maxL + 1, maxW
colw = 46.0
node_r = 15
H = 3 * 64 + 40          # 3 rows
W = NL * colw + 70
rowy = {0: H/2 - 64, 1: H/2, 2: H/2 + 64}

pos = {}
for l in range(NL):
    ids = by_layer[l]
    k = len(ids)
    for i, nid in enumerate(ids):
        row = {1: [0], 2: [0, 2], 3: [0, 1, 2]}[k][i]
        pos[nid] = (30 + l * colw, rowy[row])

def esc(s): return html.escape(s)

edges = []
for nid, n in nodes.items():
    for dep in n['deps']:
        edges.append((dep, nid))

special_path = {'N00','N01','N02'}  # source-gate chain highlight later if needed

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" style="width:100%;height:auto;font-family:inherit">']
# milestone bands P0..P7 are not derivable simply; draw layer ticks every 4
for dep, nid in edges:
    x1, y1 = pos[dep]; x2, y2 = pos[nid]
    hot = nid == 'N37' or dep == 'N37'
    col = '#b5432a' if hot else '#c5bfb2'
    w = '2' if hot else '1.1'
    op = '0.95' if hot else '0.55'
    out.append(f'<path d="M{x1+17:.1f},{y1:.1f} C{(x1+x2)/2+8:.1f},{y1:.1f} {(x1+x2)/2+8:.1f},{y2:.1f} {x2-17:.1f},{y2:.1f}" fill="none" stroke="{col}" stroke-width="{w}" opacity="{op}"/>')
for nid, (x, y) in pos.items():
    st = STATUS_MAP.get(declared[nid], 'BLOCKED')
    stroke, fill = COLOR[st]
    head = nid == 'N37'
    r = 19 if head else 15
    fs = 12.5 if head else 11
    fw = '800' if head else '600'
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{2.5 if head else 1.6}"/>')
    out.append(f'<text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" font-size="{fs}" font-weight="{fw}" fill="{stroke}">{nid}</text>')

out.append('</svg>')
svg = '\n'.join(out)
open('talks-20260821/dag.svg', 'w').write(svg)
print(f'nodes={len(nodes)} edges={len(edges)} layers={NL} maxwidth={NW} viewBox={W:.0f}x{H:.0f}')
print('status counts:', collections.Counter(STATUS_MAP.get(v,'?') for v in declared.values()))
