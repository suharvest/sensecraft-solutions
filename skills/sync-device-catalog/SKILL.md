---
name: sync-device-catalog
description: 从产品 Excel 表校验 device_catalog 的 family_id、purchase.require 轴合法性、external URL 正确性。适用于 product-family 架构下的产品族匹配和外部链接校验。
argument-hint: "<Excel 产品表路径>"
allowed-tools: Read, Edit, Glob, Grep, Bash
---

# Sync Device Catalog Skill (product-family era)

从产品 Excel 表提取 SKU→产品信息，校验 `solutions/*/solution.yaml` 中的
`device_catalog` 在新 product-family 架构下的正确性。

## 架构背景

产品数据（name / image / product_url / SKU）已从 `device_catalog` 移到
`purchase_profile` 服务端。`device_catalog` 现在只引用 `family_id` + 可选的
`purchase.require`。

```
product-family-manifest.json          ← 产品族定义（axis、sku_attrs）
       ↓ 引用
solution.yaml / device_catalog        ← family_id + purchase.require
       ↓ 运行时
purchase_profile 服务                 ← 提供 SKU / URL / image / name
```

三种条目类型：

| 类型 | 前缀 | 示例 | 产品数据来源 |
|------|------|------|-------------|
| 产品族 | 无 | `recomputer_j40` | purchase_profile |
| 外部产品 | `external_` | `external_raspberry_pi` | device_catalog 内直接写 `product_url` |
| 通用设备 | `generic_` | `generic_hdmi_display` | 无 |

## 调用方式

```
/sync-device-catalog <excel_path>
```

## 校验步骤

### 1. 从 Excel 推断旧 SKU 对应的 purchase.require

```python
def infer_require(sku, family_id, sku_map, manifest):
    """从 Excel 产品名推断 purchase.require 轴值"""
    name = ' '.join(sku_map[sku].lower().split())  # 标准化空格
    family = manifest['families'][family_id]
    require = {}
    
    for axis, cfg in family['axes'].items():
        for val in cfg['values']:
            val_norm = val.replace('_', ' ')
            if val_norm in name:
                require[axis] = [val]
                break
    return require if require else None
```

### 2. 对比 old SKU → new purchase.require

```python
# 获取旧格式 (commit d4ecf11)
old_data = yaml.safe_load(subprocess.run(
    ['git', 'show', f'd4ecf11:{sol_path}'], capture_output=True, text=True
).stdout)
old_catalog = old_data['intro']['device_catalog']

# 对比
for old_ref, old_entry in old_catalog.items():
    old_sku = old_entry.get('sku', '')
    new_ref = ref_mapping[old_ref]  # old→new key 映射表
    new_entry = new_catalog[new_ref]
    new_require = new_entry.get('purchase', {}).get('require', {})
    inferred = infer_require(old_sku, new_ref, sku_map, manifest)
    
    if inferred and inferred != new_require:
        print(f"需要添加 purchase.require: {sol}/{new_ref}: {inferred}")
```

### 3. 校验 external URL

```python
for ref, entry in catalog.items():
    if not ref.startswith('external_'): continue
    url = entry.get('product_url', '')
    found = any(url in info['url'] for info in sku_map.values())
    if not found:
        print(f"URL_NOT_IN_EXCEL: {sol}/{ref}: {url}")
```

### 4. 校验 family_id 和 purchase.require 合法性

用 CI 脚本：

```bash
uv run python scripts/ci/validate_product_families.py
```

## old→new key 映射表

| old_ref | new_ref |
|---------|---------|
| `recomputer_j40`, `recomputer_j4012`, `recomputer_industrial_j4012`, `recomputer_super_j4012`, `recomputer_jetson` | `recomputer_j40` |
| `recomputer_j3010`, `recomputer_industrial_j3010` | `recomputer_j30` |
| `recomputer_j50`, `recomputer_j501`, `recomputer_j5011` | `recomputer_j50` |
| `recomputer_r1100`, `recomputer_r1125`, `recomputer_r` | `recomputer_r11` |
| `recomputer_r2135` | `recomputer_r21_industrial` |
| `r2000_hailo`, `recomputer_r2135_ai` | `recomputer_r21_industrial_ai` |
| `recamera` | `recamera_2002` |
| `so_arm101` | `so_arm` |
| `respeaker_xvf3800_circular_4`, `respeaker_mic` | `respeaker_flex` |
| `rebot_b601dm` | `rebot_arm_b601` |
| `orbbec_gemini2` | `external_orbbec_gemini2` |
| `lekiwi_kit` | `lekiwi` |
| `raspberry_pi` | `external_raspberry_pi` |
| `reachy_mini_wireless` | `reachy_mini` |
| `hdmi_display` | `generic_hdmi_display` |
| `bc01_beacon` | `external_bc03_beacon` |
| `t1000_tracker` | `sensecap_t1000_tracker` |
| `gateway_us915`, `gateway_eu868`, `gateway_as923` | `sensecap_m2_gateway` |

## 使用约束

- 需要 `openpyxl`、`pyyaml`、`ruamel.yaml`
- 修改后必须运行 `uv run python scripts/ci/validate_product_families.py`
- Excel 列头需含 `sku/mpn`、`Product Name`、`Product page link`、`product Img URL`
- 只修改 `purchase.require` 和 `external_` URL，不直接写产品数据到 device_catalog