#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--aggregate', required=True)
    ap.add_argument('--out-md', default='docs/torino_table.md')
    args = ap.parse_args()

    data = json.loads(Path(args.aggregate).read_text(encoding='utf-8'))
    agg = data['aggregate']
    slots = agg['slots']

    lines = []
    lines.append('# Torino Slot Table')
    lines.append('')
    lines.append('| q | t | X | XY4 | BB1 | CONTOUR | dX | dXY4 | dBB1 | best |')
    lines.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|')
    for s in slots:
        lines.append(
            f"| {int(s['q'])} | {int(s['t'])} | {s['X']:.6f} | {s['XY4']:.6f} | {s['BB1']:.6f} | {s['CONTOUR']:.6f} | {s['dX']:+.6f} | {s['dXY4']:+.6f} | {s['dBB1']:+.6f} | {s['best']} |"
        )

    lines.append('')
    lines.append('## Aggregate')
    lines.append('')
    lines.append(f"- wins_vs_X: {agg['wins_vs_X']}/{agg['n_slots']}")
    lines.append(f"- wins_vs_XY4: {agg['wins_vs_XY4']}/{agg['n_slots']}")
    lines.append(f"- wins_vs_BB1: {agg['wins_vs_BB1']}/{agg['n_slots']}")
    lines.append(f"- mean_dX: {agg['mean_dX']:+.6f}")
    lines.append(f"- mean_dXY4: {agg['mean_dXY4']:+.6f}")
    lines.append(f"- mean_dBB1: {agg['mean_dBB1']:+.6f}")

    out_path = Path(args.out_md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(out_path)


if __name__ == '__main__':
    main()
