# Synaptix Explainer — Template Quick Index

Prefer loading the single template file (`references/<template>.md`) to save tokens.

- **`title`** (`references/title.md`): `{"subtitle"?: <=100, "icon"?: icon}`
- **`bar-chart`** (`references/bar-chart.md`): `{"items": 2..8 x {"label": <=18, "value": num>=0, "unit"?: <=10}, "y_label"?: <=32}`
- **`line-chart`** (`references/line-chart.md`): `{"series": 1..3 x {"name": <=24, "points": 3..12 x {"x": <=10, "y": num}}, "y_label"?: <=32}`
- **`donut-chart`** (`references/donut-chart.md`): `{"items": 2..6 x {"label": <=20, "value": num>0}, "center_label"?: <=24}`
- **`comparison`** (`references/comparison.md`): `{"columns": 2..3 x {"title": <=28, "points": 2..5 x <=60, "icon"?: icon}, "verdict"?: <=80}`
- **`process`** (`references/process.md`): `{"steps": 3..6 x {"title": <=28, "detail"?: <=80, "icon"?: icon}}`
- **`cycle`** (`references/cycle.md`): `{"stages": 3..6 x {"title": <=28, "detail"?: <=80}, "center"?: <=28}`
- **`timeline`** (`references/timeline.md`): `{"events": 3..7 x {"when": <=12, "title": <=28, "detail"?: <=70}}`
- **`hub`** (`references/hub.md`): `{"center": {"title": <=28, "detail"?: <=80}, "spokes": 3..6 x {"title": <=28, "detail"?: <=80, "icon"?: icon}}`
- **`recap`** (`references/recap.md`): `{"points": 2..5 x {"title": <=36, "detail"?: <=90}}`
