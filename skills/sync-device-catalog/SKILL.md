---
name: sync-device-catalog
description: 从产品 Excel 表校验 device_catalog 的 family_id 覆盖、purchase.require 轴合法性、external URL 正确性。
argument-hint: "<Excel 产品表路径>"
allowed-tools: Read, Edit, Glob, Grep, Bash
---

# Sync Device Catalog Skill

从 Seeed 产品 Excel 表交叉校验 `solutions/*/solution.yaml` 中 `device_catalog` 的正确性。

## 架构

产品数据（name / image / url / SKU）由 `purchase_profile` 运行时提供。
`device_catalog` 只引用 `family_id`，可选 `purchase.require` 约束轴值。

```
spec/product-family-manifest.json     ← 产品族定义（axis、sku_attrs、title）
       ↓
solution.yaml / device_catalog        ← family_id + purchase.require
       ↓
purchase_profile 服务                 ← 运行时提供 SKU / URL / image / name
```

三种条目：

| 类型 | 前缀 | 产品数据 |
|------|------|---------|
| 产品族 | 无 | purchase_profile |
| 外部 | `external_` | `product_url` 写在 device_catalog 里 |
| 通用 | `generic_` | 无 |

## 校验流程

### 1. Excel → 索引

```python
import openpyxl

wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
ws = wb.active
headers = [str(c.value).lower() for c in next(ws.iter_rows(min_row=1, max_row=1))]
sku_col = next(i for i, h in enumerate(headers) if 'sku' in h or 'mpn' in h)
name_col = next(i for i, h in enumerate(headers) if 'product name' in h)
url_col = next(i for i, h in enumerate(headers) if 'link' in h)

sku_map = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    sku = str(row[sku_col]).strip() if row[sku_col] is not None else ''
    name = str(row[name_col]).strip() if row[name_col] else ''
    url = str(row[url_col]).strip() if row[url_col] else ''
    if sku:
        sku_map[sku] = {'name': name, 'url': url}
```

### 2. 校验 external URL

```python
import yaml, os

for item in os.listdir('solutions'):
    sol_path = f'solutions/{item}/solution.yaml'
    if not os.path.exists(sol_path): continue
    with open(sol_path) as f:
        data = yaml.safe_load(f)
    for ref, entry in data['intro']['device_catalog'].items():
        if not ref.startswith('external_'): continue
        url = entry.get('product_url', '')
        if not any(url in info['url'] for info in sku_map.values()):
            print(f"URL not in Excel: {item}/{ref}: {url}")
```

### 3. 校验 family_id 和 purchase.require

```bash
uv run python scripts/ci/validate_product_families.py
```

此脚本检查：
- 每个 `device_catalog` key 是否在 `product-family-manifest.json` 中存在
- `purchase.require` 的轴名和值是否合法
- `purchase.require` 组合是否匹配至少一个 SKU

### 4. 推断 purchase.require（从 Excel 产品名）

当需要为某个条目补充 `purchase.require` 时，从 Excel 产品名推断：

```python
def infer_require(sku, family_id, sku_map, manifest):
    name = ' '.join(sku_map[sku]['name'].lower().split())
    family = manifest['families'][family_id]
    require = {}
    for axis, cfg in family['axes'].items():
        for val in cfg['values']:
            if val.replace('_', ' ') in name:
                require[axis] = [val]
                break
    return require if require else None
```

## 使用约束

- 需要 `openpyxl`、`pyyaml`、`ruamel.yaml`
- 修改后必须跑 `uv run python scripts/ci/validate_product_families.py`
- 只改 `purchase.require` 和 `external_` URL，不写产品数据到 device_catalog
- Excel 列头需含 `sku/mpn`、`Product Name`、`Product page link`