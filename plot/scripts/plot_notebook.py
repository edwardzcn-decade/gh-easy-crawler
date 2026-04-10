# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: gh-crawler
#     language: python
#     name: python3
# ---

# %%
# #!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from dateutil import parser
from datetime import timedelta
from pathlib import Path
from typing import cast
import re
from collections import Counter
from matplotlib.patches import Rectangle

# %%
# 论文绘图基础设置 / Paper plotting setup
import matplotlib as mpl
from matplotlib import font_manager

def make_font_props(*candidates: str) -> font_manager.FontProperties:
    """选择首个存在的字体文件 / Pick the first available font file."""
    for path in candidates:
        if Path(path).exists():
            return font_manager.FontProperties(fname=path)
    raise FileNotFoundError(f"None of the font files exist: {candidates}")


font_times = make_font_props(
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
)
font_cn = make_font_props(
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts/Deng.ttf",
    "/Applications/Microsoft Word.app/Contents/Resources/DFonts/Deng.ttf",
    "/Applications/Microsoft Excel.app/Contents/Resources/DFonts/Deng.ttf",
)

mpl.rcParams["font.family"] = [
    "Times New Roman",  # 英文优先 / Latin first
]
mpl.rcParams["axes.unicode_minus"] = False  # 负号正常 / Proper minus sign

# %%
# 统一样式参数 / Shared style knobs
SCATTER_SIZE_DEFAULT = 42
ALPHA_DEFAULT = 0.7
GRID_ALPHA = 0.30
GRID_LINESTYLE = "--"
BAR_WIDTH = 0.72
LINEWIDTH_DEFAULT = 1.8

FIG_SIZE_SMALL = (5.2, 3.4)
FIG_SIZE_MEDIUM = (7.0, 4.6)
FIG_SIZE_WIDE = (10.2, 4.8)

plt.rcParams.update(
    {
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.7,
        "lines.linewidth": LINEWIDTH_DEFAULT,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)
sns.set_theme(style="whitegrid", context="paper")


# %%
# 统一色板 / Unified palette
blue_colors = [
    "#0B3C8C",
    "#154FA6",
    "#1E63C0",
    "#2A78DA",
    "#3A8DF0",
    "#62A9F7",
    "#8BC3FB",
    "#B5DAFE",
    "#D7EBFF",
]
teal_colors = [
    "#005A55",
    "#00756E",
    "#009088",
    "#00ABA2",
    "#27C2B7",
    "#55D6CA",
    "#87E6DA",
    "#B6F2EA",
    "#DDFBF6",
]
green_colors = [
    "#0A4E1F",
    "#146A2D",
    "#20863B",
    "#2DA34A",
    "#52BB6A",
    "#7DD897",
    "#A7E8B8",
    "#CFF5D9",
    "#E8FDF0",
]
orange_colors = [
    "#7A3C00",
    "#9B5200",
    "#BC6800",
    "#D77F00",
    "#F19626",
    "#F7B86C",
    "#F9D3A2",
    "#FBE8CE",
    "#FEF6E8",
]
RED_COLOR_DEFAULT = "#d62728"
BLUE_COLOR_DEFAULT = blue_colors[3]
TEAL_COLOR_DEFAULT = teal_colors[3]
ORANGE_COLOR_DEFAULT = orange_colors[4]
PINK_COLOR_DEFAULT = "#C94C7D"
GRAY_COLOR_DEFAULT = "#B8B8B8"
EDGE_COLOR_DEFAULT = "#FFFFFF"


def apply_axis_style(ax, *, xlabel=None, ylabel=None, title=None, grid_axis="y"):
    """统一坐标轴外观 / Apply a compact paper style."""
    if title:
        ax.set_title(title, fontproperties=font_cn)
    if xlabel:
        ax.set_xlabel(xlabel, fontproperties=font_cn)
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=font_cn)
    axis_name = "both" if grid_axis == "both" else grid_axis
    ax.grid(
        grid_axis != "none",
        axis=axis_name,
        linestyle=GRID_LINESTYLE,
        alpha=GRID_ALPHA,
    )
    ax.set_axisbelow(True)


def annotate_bars(ax, *, fmt="{:.0f}", offset=0.6, font_prop=font_times):
    """柱顶标注 / Add compact value labels above bars."""
    for patch in ax.patches:
        height = patch.get_height()
        if height <= 0:
            continue
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            height + offset,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=9,
            fontproperties=font_prop,
        )


def save_figure(fig, script_dir: Path, filename: str):
    """统一保存参数 / Save with consistent output settings."""
    fig.savefig(script_dir / filename, dpi=300, bbox_inches="tight")


def save_table(df: pd.DataFrame, script_dir: Path, filename: str):
    """统一保存表格 / Save derived tables next to the notebook."""
    df.to_csv(script_dir / filename, index=False, encoding="utf-8-sig")


def style_chinese_ticks(ax, *, rotation=0, ha="center"):
    """中文刻度字体 / Apply Songti to tick labels."""
    for label in ax.get_xticklabels():
        label.set_fontproperties(font_cn)
        label.set_rotation(rotation)
        label.set_ha(ha)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font_cn)


def style_numeric_ticks(ax, *, axis="both"):
    """数字刻度字体 / Apply Times New Roman to numeric ticks."""
    if axis in {"x", "both"}:
        for label in ax.get_xticklabels():
            label.set_fontproperties(font_times)
    if axis in {"y", "both"}:
        for label in ax.get_yticklabels():
            label.set_fontproperties(font_times)

# %%
# 统一加载输入数据，避免重复读取同一 CSV
SCRIPT_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
if not (SCRIPT_DIR / "bug_csv_v2.csv").exists():
    SCRIPT_DIR = Path.cwd() / "plot" / "scripts"

BUG_OVERVIEW_CSV = SCRIPT_DIR / "bug_csv_v2.csv"
BUG_RESOLVED_V3_CSV = SCRIPT_DIR / "bug_resolved_csv_v3.csv"
BUG_RESOLVED_V4_CSV = SCRIPT_DIR / "bug_resolved_csv_v4.csv"

df_bug_overview = pd.read_csv(BUG_OVERVIEW_CSV)
df_bug_resolved_v3 = pd.read_csv(BUG_RESOLVED_V3_CSV)
df_bug_resolved_v4 = pd.read_csv(BUG_RESOLVED_V4_CSV)

# 图 5：评论次数与评论字数 / Fig. 5: comments vs chars
df_f5_copy = df_bug_overview.dropna(
    subset=["tool_total_comments_count", "tool_total_chars"]
).copy()
df_f5_copy["tool_total_comments_count"] = df_f5_copy[
    "tool_total_comments_count"
].astype(float)
df_f5_copy["tool_total_chars"] = df_f5_copy["tool_total_chars"].astype(float)

# %%
count_threshold = 30
chars_threshold = 20000
df_f5_copy_main = df_f5_copy[
    (df_f5_copy["tool_total_comments_count"] <= count_threshold)
    & (df_f5_copy["tool_total_chars"] <= chars_threshold)
]
df_f5_copy_outliers = df_f5_copy[
    (df_f5_copy["tool_total_comments_count"] > count_threshold)
    | (df_f5_copy["tool_total_chars"] > chars_threshold)
]

fig5, (ax5_1, ax5_2) = plt.subplots(1, 2, figsize=(11.2, 4.2))

sns.regplot(
    data=df_f5_copy,
    x="tool_total_comments_count",
    y="tool_total_chars",
    scatter_kws={"alpha": ALPHA_DEFAULT, "s": SCATTER_SIZE_DEFAULT},
    line_kws={"color": RED_COLOR_DEFAULT, "linewidth": 1.6},
    ax=ax5_1,
    color=BLUE_COLOR_DEFAULT,
)
apply_axis_style(
    ax5_1,
    xlabel="评论次数（个）",
    ylabel="评论字数（字符）",
    title="(a) 全部样本回归关系",
    grid_axis="both",
)
style_numeric_ticks(ax5_1)

ax5_2.scatter(
    x=df_f5_copy_main["tool_total_comments_count"],
    y=df_f5_copy_main["tool_total_chars"],
    s=SCATTER_SIZE_DEFAULT,
    alpha=ALPHA_DEFAULT,
    color=BLUE_COLOR_DEFAULT,
)
ax5_2.scatter(
    x=df_f5_copy_outliers["tool_total_comments_count"],
    y=df_f5_copy_outliers["tool_total_chars"],
    s=SCATTER_SIZE_DEFAULT,
    alpha=ALPHA_DEFAULT,
    color=PINK_COLOR_DEFAULT,
)

# 异常点标注 / Outlier labels
for _, row in df_f5_copy_outliers.iterrows():
    ax5_2.annotate(
        text=row["Bug编号"],
        xy=(row["tool_total_comments_count"], row["tool_total_chars"]),
        xytext=(-70, -18),
        textcoords="offset points",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
        arrowprops=dict(
            arrowstyle="->",
            color="gray",
            lw=1.2,
            alpha=0.8
        ),
    )

apply_axis_style(
    ax5_2,
    xlabel="评论次数（个）",
    ylabel="评论字数（字符）",
    title="(b) 主体分布与高值异常点",
    grid_axis="both",
)
style_numeric_ticks(ax5_2)

fig5.tight_layout()
plt.show()


# %%
# 图 1：触发位置分布 / Fig. 1: trigger locations


def split_multi_values(val, sep=r";"):
    """拆分多值字段 / Split multi-value cells."""
    if pd.isna(val):
        return []
    s = str(val)
    return [p.strip() for p in re.split(sep, s) if p.strip()]


def aggregate_components(df, column_names: list[str]) -> tuple[Counter, dict]:
    """汇总组件频次 / Aggregate component counts."""
    counter = Counter()

    for _, row in df.iterrows():
        merged = []
        for c in column_names:
            l = split_multi_values(row.get(c), sep=r"[;；,]")
            merged += l
        for item in merged:
            counter[item] += 1
    return (counter,dict(counter.most_common()))


counter_old, db_counts = aggregate_components(
    df_bug_resolved_v3, ["Source数据库类型", "Sink数据库类型"]
)
print(db_counts)

# %%
# 补充核心模块标签 / Add core-module labels
print(db_counts)

def addition_labels(df, column_names: list[str], target_strings: list[str]) -> tuple[Counter, dict]:
  """统计额外标签 / Count selected labels."""

  counter = Counter()
  for _, row in df.iterrows():
    merged = []
    for c in column_names:
      merged += split_multi_values(row.get(c, ""), sep=r"[;；,]")
    for t in target_strings:
      if t in merged:
        counter[t] += 1
  return (counter, dict(counter.most_common()))


counter_addition, db_counts_addition = addition_labels(
    df_bug_resolved_v3,
    ["tool_labels"],
    ["e2e-tests", "composer", "base", "common", "docs", "build", "cli"],
)  # Runtime 相关标签允许重复计数
print(db_counts_addition)
counter_old.update(counter_addition)
db_counts.update(db_counts_addition)
print(counter_old.most_common())
print(db_counts)

# %%
# 触发位置分类 / Trigger categories
source_set = {"MySQL", "PostgreSQL", "MongoDB", "SQL Server", "Oracle", "DB2", "OceanBase", "Vitness", "TiDB"}
sink_set = {"StarRocks", "Doris", "Kafka", "Paimon", "Iceberg", "Elasticsearch", "Fluss", "MaxCompute", "Values"}
core_processor_set = {"Runtime", "e2e-tests", "composer", "base", "common"}
other_set = {"docs", "build", "cli"}

db_counts_new = dict(counter_old.most_common())
items = list(db_counts_new.items())

def autopct_fmt(pct, allvals):
    """饼图标签 / Pie label formatter."""
    total = sum(allvals)
    count = int(round(pct / 100.0 * total))
    return f"{pct:.1f}%\n({count})"

reordered_items = []
for k, v in items:
    if k in source_set:
        reordered_items.append((k, v))

for k, v in items:
    if k in core_processor_set:
        reordered_items.append((k, v))

for k, v in items:
    if k in other_set:
        reordered_items.append((k, v))

for k, v in items:
    if k in sink_set:
        reordered_items.append((k, v))

for k, v in items:
    if (
        k not in source_set
        and k not in sink_set
        and k not in core_processor_set
        and k not in other_set
    ):
        print(k, v)
        raise ValueError("Unsupported type.")

reordered_labels = [x[0] for x in reordered_items]
reordered_values = [x[1] for x in reordered_items]
reordered_colors = []

for lab in reordered_labels:
    if lab in source_set:
        reordered_colors.append(BLUE_COLOR_DEFAULT)
    elif lab in sink_set:
        reordered_colors.append(TEAL_COLOR_DEFAULT)
    elif lab in core_processor_set:
        reordered_colors.append(ORANGE_COLOR_DEFAULT)
    elif lab in other_set:
        reordered_colors.append(GRAY_COLOR_DEFAULT)

reordered_explode = []
for lab in reordered_labels:
    if lab in core_processor_set:
        reordered_explode.append(0.08)
    else:
        reordered_explode.append(0.00)

fig1_2, ax1_2 = plt.subplots(figsize=(8.2, 6.3))

ax1_2.pie(
    reordered_values,
    labels=reordered_labels,
    colors=reordered_colors,
    explode=reordered_explode,
    startangle=60,
    autopct=lambda pct: autopct_fmt(pct, reordered_values),
    pctdistance=0.70,
    textprops={"fontsize": 10},
    wedgeprops={"linewidth": 0.8, "edgecolor": EDGE_COLOR_DEFAULT},
)
ax1_2.set_title("错误触发位置构成", fontproperties=font_cn)
fig1_2.tight_layout()
plt.show()

# %%
fig1_3, ax1_3 = plt.subplots(figsize=FIG_SIZE_WIDE)

# 分组收紧 / Tighter positions within each group
source_labels = [lab for lab in reordered_labels if lab in source_set]
core_labels = [lab for lab in reordered_labels if lab in core_processor_set]
other_labels = [lab for lab in reordered_labels if lab in other_set]
sink_labels = [lab for lab in reordered_labels if lab in sink_set]

grouped_labels = source_labels + core_labels + other_labels + sink_labels
grouped_values = [db_counts_new[lab] for lab in grouped_labels]
grouped_colors = [
    BLUE_COLOR_DEFAULT if lab in source_set
    else ORANGE_COLOR_DEFAULT if lab in core_processor_set
    else GRAY_COLOR_DEFAULT if lab in other_set
    else TEAL_COLOR_DEFAULT
    for lab in grouped_labels
]

group_sizes = [len(source_labels), len(core_labels) + len(other_labels), len(sink_labels)]
intra_gap = 0.82
inter_extra_gap = 0.58
x_positions = []
cursor = 0.0
for group_size in group_sizes:
    for idx in range(group_size):
        x_positions.append(cursor + idx * intra_gap)
    cursor = x_positions[-1] + intra_gap + inter_extra_gap
x_positions = np.array(x_positions)

ax1_3.bar(
    x_positions,
    grouped_values,
    color=grouped_colors,
    width=BAR_WIDTH,
    edgecolor=EDGE_COLOR_DEFAULT,
    linewidth=0.8,
)

ax1_3.set_xticks(x_positions)
ax1_3.set_xticklabels(grouped_labels, rotation=30, ha="center")
style_chinese_ticks(ax1_3, rotation=30, ha="center")
style_numeric_ticks(ax1_3, axis="y")

trans = ax1_3.get_xaxis_transform()

source_center = x_positions[: len(source_labels)].mean()
core_other_end = len(source_labels) + len(core_labels) + len(other_labels)
core_center = x_positions[len(source_labels):core_other_end].mean()
sink_center = x_positions[core_other_end:].mean()

ax1_3.text(source_center, -0.25, "源连接器", transform=trans, ha="center", va="top", fontsize=11, fontproperties=font_cn)
ax1_3.text(core_center, -0.25, "核心与工程支撑", transform=trans, ha="center", va="top", fontsize=11, fontproperties=font_cn)
ax1_3.text(sink_center, -0.25, "汇连接器", transform=trans, ha="center", va="top", fontsize=11, fontproperties=font_cn)

def draw_group_bracket(ax, x0, x1, y_axes=-0.28, tick=0.02, lw=1.2, color="gray"):
    """绘制分组括号 / Draw a group bracket under x-axis."""
    trans = ax.get_xaxis_transform()

    ax.plot([x0, x1], [y_axes, y_axes], transform=trans, lw=lw, color=color, clip_on=False)
    ax.plot([x0, x0], [y_axes, y_axes - tick], transform=trans, lw=lw, color=color, clip_on=False)
    ax.plot([x1, x1], [y_axes, y_axes - tick], transform=trans, lw=lw, color=color, clip_on=False)

draw_group_bracket(ax1_3, x_positions[0] - 0.35, x_positions[len(source_labels) - 1] + 0.35, y_axes=-0.22, tick=-0.02)
draw_group_bracket(
    ax1_3,
    x_positions[len(source_labels)] - 0.35,
    x_positions[core_other_end - 1] + 0.35,
    y_axes=-0.22,
    tick=-0.02,
)
draw_group_bracket(
    ax1_3,
    x_positions[core_other_end] - 0.35,
    x_positions[-1] + 0.35,
    y_axes=-0.22,
    tick=-0.02,
)

apply_axis_style(ax1_3, ylabel="触发数量（个）", title="CDC 错误触发位置分布", grid_axis="y")
ax1_3.grid(False, axis="x")
for x_pos, v in zip(x_positions, grouped_values):
    ax1_3.text(
        x_pos,
        v + max(grouped_values) * 0.001,
        str(v),
        ha="center",
        va="bottom",
        fontsize=9,
        fontproperties=font_times,
    )

fig1_3.tight_layout()
save_figure(fig1_3, SCRIPT_DIR, "fig_2_bug_trigger_locations.png")
plt.show()


# %%
# 修复周期时间标准化 / Normalize repair timestamps
def normalize_datetime_column(df, colname, utc=True):
    """标准化单个时间列 / Normalize one datetime-like column."""
    def parse_to_iso8601(val):
        if pd.isna(val):
            return None
        try:
            date_time = parser.parse(str(val))
            if utc:
                return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                return date_time.isoformat()
        except Exception:
            return val

    df[colname] = df[colname].apply(parse_to_iso8601)
    return df


def normalize_datetime_columns(df, cols: list[str]):
    """批量标准化时间列 / Normalize multiple datetime columns."""
    for col in cols:
        df = normalize_datetime_column(df, col)
    return df

df_2 = df_bug_resolved_v4.copy()

reformat_datetime_cols = [
    "首次报告时间",
    "确认修复时间",
    "tool_created_at",
    "tool_merged_at",
]

normalize_datetime_columns(df_2, cols=reformat_datetime_cols)


# %%
# 修复周期预处理 / Repair-cycle preprocessing
tolerance_days = 2.0
tolerance_seconds = tolerance_days * 86400.0
df_2_copy = df_2.dropna(subset=["tool_created_at", "tool_merged_at"]).copy()
# 使用矢量化时间转换 / Use vectorized datetime parsing
df_2_copy["t_report"] = pd.to_datetime(
    df_2_copy["首次报告时间"], errors="coerce", utc=True
)
df_2_copy["t_fix"] = pd.to_datetime(
    df_2_copy["确认修复时间"], errors="coerce", utc=True
)
df_2_copy["t_pr_created"] = pd.to_datetime(
    df_2_copy["tool_created_at"], errors="coerce", utc=True
)
df_2_copy["t_pr_merged"] = pd.to_datetime(
    df_2_copy["tool_merged_at"], errors="coerce", utc=True
)

df_2_copy["merge_fix_diff_seconds"] = (
    df_2_copy["t_fix"] - df_2_copy["t_pr_merged"]
).dt.total_seconds()
print("\n[超过 2 天差值的记录]:")

bad_merge = df_2_copy[df_2_copy["merge_fix_diff_seconds"].abs() > tolerance_seconds]
print(bad_merge[["Bug编号", "t_fix", "t_pr_merged", "merge_fix_diff_seconds"]])

df_2_copy["duration_total"] = df_2_copy["t_fix"] - df_2_copy["t_report"]
# 个别 PR 创建时间早于报告时间，因此截断为 0 / Clamp negative lead time
df_2_copy["duration_start"] = (df_2_copy["t_pr_created"] - df_2_copy["t_report"]).apply(
    lambda x: max(x, pd.Timedelta(0))
)
df_2_copy["duration_success"] = df_2_copy["t_fix"] - df_2_copy["t_pr_created"]

# 验证：总时长 = 启动阶段 + 合入阶段 / Validate duration decomposition
df_2_copy["check_sum"] = (
    df_2_copy["duration_start"] + df_2_copy["duration_success"]
) - df_2_copy["duration_total"]

print("\n[总 != 启动 + 成功 的记录] (理论应全为 0 ± ε):")
bad_sum = df_2_copy[
    df_2_copy["check_sum"].abs() > timedelta(seconds=1)
]
print(
    bad_sum[
        ["Bug编号", "duration_total", "duration_start", "duration_success", "check_sum"]
    ]
)

# 事后比对：重算时长 vs CSV 修复周期 / Compare recomputed duration with CSV
def parse_duration(s):
    """解析修复周期 / Parse strings like '4d 10:24:56'."""
    if pd.isna(s):
        return None
    try:
        s = str(s).lower().replace(" ", "")
        d, hms = s.split("d")
        h, m, sec = hms.split(":")
        return timedelta(days=int(d), hours=int(h), minutes=int(m), seconds=float(sec))
    except Exception:
        return None
df_2_copy["duration_total_csv"] = df_2_copy["修复周期"].apply(parse_duration)
df_2_copy["duration_diff_seconds"] = (
    df_2_copy["duration_total"] - df_2_copy["duration_total_csv"]
).dt.total_seconds()

print("\n[总修复时长 与 CSV 修复周期 差值超过 2 天 的记录]:")
bad_duration = df_2_copy[df_2_copy["duration_diff_seconds"].abs() > tolerance_seconds]
print(
    bad_duration[
        ["Bug编号", "duration_total", "duration_total_csv", "duration_diff_seconds"]
    ]
)

# %%
# 图 3：修复周期 CDF / Fig. 3: fixing-time CDF
cdf_days = (
    df_2_copy["duration_total_csv"]
    .dropna()
    .dt.total_seconds() / 86400.0
)
x = np.sort(cdf_days.to_numpy())
y = np.arange(1, len(x) + 1) / len(x)
fig_cdf_2, ax_cdf_2 = plt.subplots(figsize=FIG_SIZE_SMALL)
ax_cdf_2.step(x, y, where="post", linewidth=1.8, color=BLUE_COLOR_DEFAULT)
ax_cdf_2.set_xlim(left=0)
ax_cdf_2.set_ylim(0, 1)
apply_axis_style(
    ax_cdf_2,
    xlabel="报告至修复周期（天）",
    ylabel="CDF",
    title="修复周期累积分布",
    grid_axis="both",
)
style_numeric_ticks(ax_cdf_2)
fig_cdf_2.tight_layout()
save_figure(fig_cdf_2, SCRIPT_DIR, "fig_3_cdf_of_fixing_time.png")
plt.show()

# %%
# 图 2：修复周期与讨论文本量 / Fig. 2: repair duration vs text volume
df_2_copy["duration_total_days"] = df_2_copy["duration_total"].dt.total_seconds() / 86400.0
fig2_1, ax2_1 = plt.subplots(figsize=FIG_SIZE_MEDIUM)

df_2_special = df_2_copy[df_2_copy["duration_total_days"] > 100]
print(df_2_special[["Bug编号", "duration_total_days", "tool_total_chars"]])

ax2_1.scatter(
    x=df_2_copy["tool_total_chars"],
    y=df_2_copy["duration_total_days"],
    s=SCATTER_SIZE_DEFAULT,
    alpha=ALPHA_DEFAULT,
    color=BLUE_COLOR_DEFAULT,
)
apply_axis_style(
    ax2_1,
    xlabel="讨论文本量（字符）",
    ylabel="修复周期（天）",
    title="修复周期与文本量关系",
    grid_axis="both",
)
style_numeric_ticks(ax2_1)
fig2_1.tight_layout()
plt.show()

# %%
# 排序后观察趋势 / Sorted trend view
df_dual = df_2_copy[
    ["Bug编号", "tool_total_chars", "duration_total", "duration_start", "duration_success", "duration_total_days"]
].copy()

df_dual["duration_start_days"] = df_2_copy["duration_start"].dt.total_seconds() / 86400.0
df_dual = df_dual.sort_values("duration_total_days").reset_index(drop=True)

x = np.arange(len(df_dual))
fig2_2, ax2_2 = plt.subplots(figsize=FIG_SIZE_WIDE)

ax2_2.plot(
    x,
    df_dual["duration_start_days"],
    color=TEAL_COLOR_DEFAULT,
    linewidth=1.8,
    label="启动修复阶段（天）",
)
ax2_2.plot(
    x,
    df_dual["duration_total_days"],
    color=BLUE_COLOR_DEFAULT,
    linewidth=1.8,
    label="总修复周期（天）",
)
apply_axis_style(
    ax2_2,
    xlabel="按修复周期排序的 Bug 序号",
    ylabel="修复周期（天）",
    title="修复周期与文本量的排序趋势",
    grid_axis="y",
)
ax2_2.tick_params(axis="y", labelcolor=BLUE_COLOR_DEFAULT)
style_numeric_ticks(ax2_2)

ax2_2_copy = ax2_2.twinx()
ax2_2_copy.bar(
    x,
    df_dual["tool_total_chars"],
    color=ORANGE_COLOR_DEFAULT,
    alpha=0.40,
    width=0.85,
    label="讨论文本量（字符）",
)
ax2_2_copy.set_ylabel("讨论文本量（字符）", color=ORANGE_COLOR_DEFAULT, fontproperties=font_cn)
ax2_2_copy.tick_params(axis="y", labelcolor=ORANGE_COLOR_DEFAULT)
style_numeric_ticks(ax2_2_copy, axis="y")
ax2_2.legend(loc="upper left", prop=font_cn)
fig2_2.tight_layout()
plt.show()

# %%
# D 值难度模型 / D-score difficulty model
df_people = df_bug_resolved_v4.copy()
def parse_duration_to_hours(x):
    """将修复周期转成小时 / Convert repair duration strings to hours."""
    if pd.isna(x):
        return np.nan

    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)

    x = str(x).strip()
    if not x:
        return np.nan

    try:
        # 形如 '33d 18:45:46'
        if "d" in x:
            day_part, time_part = x.split("d", 1)
            days = int(day_part.strip())
            time_part = time_part.strip()

            if time_part:
                h, m, s = [int(i) for i in time_part.split(":")]
            else:
                h, m, s = 0, 0, 0

            return days * 24 + h + m / 60 + s / 3600

        # 形如 '18:45:46'
        if ":" in x:
            parts = x.split(":")
            if len(parts) == 3:
                h, m, s = [int(i) for i in parts]
                return h + m / 60 + s / 3600

        # 兜底：尝试直接转 float
        return float(x)

    except Exception:
        return np.nan

def derive_file_count(row):
    """推导修改文件数 / Derive changed-file counts."""
    if "tool_total_files_count" in row.index and pd.notna(row["tool_total_files_count"]):
        return float(row["tool_total_files_count"])

    if "tool_files_changed" in row.index and pd.notna(row["tool_files_changed"]):
        raw = str(row["tool_files_changed"]).strip()
        if raw == "":
            return np.nan

        for sep in [";", ",", "\n", "|"]:
            if sep in raw:
                parts = [p.strip() for p in raw.split(sep) if p.strip()]
                if len(parts) > 0:
                    return float(len(set(parts)))

        return 1.0

    return np.nan

def zscore(series):
    """标准化 / Z-score with population std."""
    mean_ = series.mean()
    std_ = series.std(ddof=0)
    if std_ == 0 or pd.isna(std_):
        return pd.Series([0] * len(series), index=series.index)
    return (series - mean_) / std_


def minmax_0_100(series):
    """线性映射到 0-100 / Map scores to 0-100."""
    s_min = series.min()
    s_max = series.max()
    if s_max == s_min:
        return pd.Series([50] * len(series), index=series.index)
    return (series - s_min) / (s_max - s_min) * 100

def grade_equal_width(d100):
    """按等宽区间分级 / Grade by equal-width bins."""
    bins = [-1e-9, 20, 40, 60, 80, 100 + 1e-9]
    labels = ["极低", "低", "中等", "高", "极高"]
    return pd.cut(d100, bins=bins, labels=labels, include_lowest=True, right=False)

# 构建 D 模型分析子表 / Build the D-model analysis table
df_tmp = df_people.copy()

# 统一字段命名 / Normalize column names
if "Bug编号" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'Bug编号' 列，请先核对文件。")

# 修复周期（小时） / Repair time in hours
if "修复周期" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 '修复周期' 列，请先核对文件。")

df_tmp["repair_hours"] = df_tmp["修复周期"].apply(parse_duration_to_hours)

# 评论次数 / Comment count
if "tool_total_comments_count" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'tool_total_comments_count' 列。")
df_tmp["comment_count"] = pd.to_numeric(df_tmp["tool_total_comments_count"], errors="coerce")

# 评论字数 / Comment chars
if "tool_total_chars" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'tool_total_chars' 列。")
df_tmp["comment_chars"] = pd.to_numeric(df_tmp["tool_total_chars"], errors="coerce")

# 修改文件数 / Files changed
df_tmp["files_changed_count"] = df_tmp.apply(derive_file_count, axis=1)

# 修改代码行数 / LOC changed
if "tool_loc_changed" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'tool_loc_changed' 列。")
df_tmp["loc_changed"] = pd.to_numeric(df_tmp["tool_loc_changed"], errors="coerce")

d_cols = [
    "Bug编号",
    "repair_hours",
    "comment_count",
    "comment_chars",
    "files_changed_count",
    "loc_changed",
]

df_d = df_tmp[d_cols].copy()


# 样本筛选 / Sample filtering

strict_discussion_filter = True

mask_complete = (
    df_d["repair_hours"].notna()
    & df_d["comment_count"].notna()
    & df_d["comment_chars"].notna()
    & df_d["files_changed_count"].notna()
    & df_d["loc_changed"].notna()
)

df_d = df_d[mask_complete].copy()

if strict_discussion_filter:
    df_d = df_d[~((df_d["comment_count"] == 0) & (df_d["comment_chars"] == 0))].copy()

df_d = df_d.reset_index(drop=True)

print("参与 D 值分析的样本数：", len(df_d))

# 计算 Z 值与 D 分数 / Compute Z-scores and D scores

df_d["Zr"] = zscore(df_d["repair_hours"])
df_d["Zc"] = zscore(df_d["comment_count"])
df_d["Zw"] = zscore(df_d["comment_chars"])
df_d["Zf"] = zscore(df_d["files_changed_count"])
df_d["Zl"] = zscore(df_d["loc_changed"])

# D 原始加权分数 / Weighted raw score
df_d["D_raw"] = (
    0.40 * df_d["Zr"]
    + 0.10 * df_d["Zc"]
    + 0.10 * df_d["Zw"]
    + 0.25 * df_d["Zf"]
    + 0.15 * df_d["Zl"]
)

# 参数开关 / Analysis switches
remove_known_bad_cases = True

bad_case_ids = ["FLINK-36763"]

remove_outliers = True

iqr_k = 1.5

# 步骤 A：先删除人工确认的异常样本 / Remove known bad cases first
if remove_known_bad_cases:
    before_n = len(df_d)
    bad_rows = df_d[df_d["Bug编号"].isin(bad_case_ids)].copy()

    df_d = df_d[~df_d["Bug编号"].isin(bad_case_ids)].copy().reset_index(drop=True)
    after_n = len(df_d)

    print("已启用人工指定异常样本删除")
    print(f"删除前样本数={before_n}, 删除后样本数={after_n}, 删除样本数={before_n - after_n}")

    if len(bad_rows) > 0:
        print("被强制删除的异常样本：")
        print(bad_rows[["Bug编号", "D_raw"]].to_string(index=False))
        save_table(bad_rows[["Bug编号", "D_raw"]], SCRIPT_DIR, "d_known_bad_cases_removed.csv")
        print("已保存：d_known_bad_cases_removed.csv")
    else:
        print("指定的异常样本未在当前分析样本中找到")
else:
    print("未启用人工指定异常样本删除")


# 步骤 B：可选执行 IQR 极端值过滤 / Optional IQR filtering
if remove_outliers:
    q1 = df_d["D_raw"].quantile(0.25)
    q3 = df_d["D_raw"].quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - iqr_k * iqr
    upper_bound = q3 + iqr_k * iqr

    before_n = len(df_d)
    outlier_mask = (df_d["D_raw"] < lower_bound) | (df_d["D_raw"] > upper_bound)
    outlier_rows = df_d.loc[outlier_mask, ["Bug编号", "D_raw"]].copy()

    df_d = df_d.loc[~outlier_mask].copy().reset_index(drop=True)
    after_n = len(df_d)

    print("已启用极端值过滤（IQR）")
    print(f"Q1={q1:.4f}, Q3={q3:.4f}, IQR={iqr:.4f}")
    print(f"下界={lower_bound:.4f}, 上界={upper_bound:.4f}")
    print(f"过滤前样本数={before_n}, 过滤后样本数={after_n}, 删除样本数={before_n - after_n}")

    if len(outlier_rows) > 0:
        print("被 IQR 删除的极端样本：")
        print(outlier_rows.sort_values("D_raw", ascending=False).to_string(index=False))
        save_table(outlier_rows, SCRIPT_DIR, "d_outliers_removed.csv")
        print("已保存：d_outliers_removed.csv")
    else:
        print("没有检测到 IQR 极端值")
else:
    print("未启用极端值过滤（IQR）")


# 在线性清洗后映射到 0-100 / Scale cleaned scores to 0-100
df_d["D_100"] = minmax_0_100(df_d["D_raw"])
df_d["难度等级"] = grade_equal_width(df_d["D_100"])

# 便于核对排序 / Sort for inspection
df_d = df_d.sort_values("D_100", ascending=True).reset_index(drop=True)

# 保存分析子表 / Save the analysis table
output_cols = [
    "Bug编号",
    "repair_hours",
    "comment_count",
    "comment_chars",
    "files_changed_count",
    "loc_changed",
    "Zr",
    "Zc",
    "Zw",
    "Zf",
    "Zl",
    "D_raw",
    "D_100",
    "难度等级",
]

save_table(df_d[output_cols], SCRIPT_DIR, "d_model_subtable.csv")
print("已保存：d_model_subtable.csv")

# %%
fig_d_hist, ax_d_hist = plt.subplots(figsize=(8, 4.8))
sns.histplot(
    data=df_d,
    x="D_100",
    bins=20,
    kde=False,
    ax=ax_d_hist,
    color=BLUE_COLOR_DEFAULT,
    edgecolor=EDGE_COLOR_DEFAULT,
)

# 分级边界线 / Grade boundaries
for x in [20, 40, 60, 80]:
    ax_d_hist.axvline(x=x, linestyle=GRID_LINESTYLE, linewidth=1, color="gray")

apply_axis_style(ax_d_hist, xlabel="D值（0-100）", ylabel="错误数量", title="修复难度得分分布", grid_axis="y")
style_numeric_ticks(ax_d_hist)
fig_d_hist.tight_layout()
save_figure(fig_d_hist, SCRIPT_DIR, "d_score_histogram.png")
plt.show()


# =========================================================
# 6. 可视化 2：难度分级计数柱状图
# =========================================================
grade_order = ["极低", "低", "中等", "高", "极高"]
grade_counts = df_d["难度等级"].value_counts().reindex(grade_order, fill_value=0)
x_labels = list(grade_counts.index)
y_values = grade_counts.to_numpy(dtype=float)

fig_grade_count, ax_grade_count = plt.subplots(figsize=(7.2, 4.8))
ax_grade_count.bar(
    x_labels,
    y_values,
    width=BAR_WIDTH,
    color=BLUE_COLOR_DEFAULT,
    edgecolor=EDGE_COLOR_DEFAULT,
    linewidth=0.8,
)
apply_axis_style(ax_grade_count, xlabel="难度等级", ylabel="错误数量", title="修复难度分级统计", grid_axis="y")
style_chinese_ticks(ax_grade_count)
style_numeric_ticks(ax_grade_count, axis="y")
annotate_bars(ax_grade_count, offset=0.5)
fig_grade_count.tight_layout()
save_figure(fig_grade_count, SCRIPT_DIR, "d_grade_counts.png")
plt.show()


# =========================================================
# 7. 可视化 3：难度分级占比柱状图
# =========================================================
grade_ratio = grade_counts / grade_counts.sum() * 100

x_labels = list(grade_ratio.index)
y_values = grade_ratio.to_numpy(dtype=float)
fig_grade_ratio, ax_grade_ratio = plt.subplots(figsize=(7.2, 4.8))
ax_grade_ratio.bar(
    x_labels,
    y_values,
    width=BAR_WIDTH,
    color=TEAL_COLOR_DEFAULT,
    edgecolor=EDGE_COLOR_DEFAULT,
    linewidth=0.8,
)
apply_axis_style(ax_grade_ratio, xlabel="难度等级", ylabel="占比（%）", title="修复难度分级占比", grid_axis="y")
style_chinese_ticks(ax_grade_ratio)
style_numeric_ticks(ax_grade_ratio, axis="y")
for patch, val in zip(ax_grade_ratio.patches, grade_ratio.values):
    rect = cast(Rectangle, patch)
    ax_grade_ratio.text(
        rect.get_x() + rect.get_width() / 2,
        rect.get_height() + 0.3,
        f"{val:.1f}%",
        ha="center",
        va="bottom",
        fontsize=9,
        fontproperties=font_times,
    )
fig_grade_ratio.tight_layout()
save_figure(fig_grade_ratio, SCRIPT_DIR, "d_grade_ratio.png")
plt.show()


# =========================================================
# 8. 输出分级统计表，方便核对
# =========================================================
summary = pd.DataFrame({
    "难度等级": grade_order,
    "错误数量": y_values,
    "占比(%)": np.round(y_values, 1)
})
print(summary)

save_table(summary, SCRIPT_DIR, "d_grade_summary.csv")
print("已保存：d_grade_summary.csv")


# %%
# 社区响应热力图 / Community-response heatmap
heatmap_df = df_people[[
    "tool_people_involved_count",
    "tool_total_comments_count",
    "tool_total_chars"
]].copy()

# 转成数值，非法值转 NaN / Numeric coercion
for col in heatmap_df.columns:
    heatmap_df[col] = pd.to_numeric(heatmap_df[col], errors="coerce")

heatmap_df = heatmap_df.dropna().copy()

print("用于热力图的样本数：", len(heatmap_df))

heatmap_df.columns = ["参与讨论人数", "评论次数", "评论字数"]

corr_matrix = heatmap_df.corr(method="pearson")
print(corr_matrix)

fig_heatmap, ax = plt.subplots(figsize=(5, 4))
ax = sns.heatmap(
    corr_matrix,
    annot=True,
    fmt=".3f",
    cmap=sns.diverging_palette(220, 25, as_cmap=True),
    vmin=0, vmax=1,
    square=True,
    linewidths=0.5,
    cbar=True,
    annot_kws={"size": 9, "fontproperties": font_times},
    ax=ax,
)
style_chinese_ticks(ax, rotation=45, ha="right")
fig_heatmap.tight_layout()
save_figure(fig_heatmap,SCRIPT_DIR, "fig_4_community_response_heatmap.png")
plt.show()
