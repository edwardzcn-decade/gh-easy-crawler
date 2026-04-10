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
from datetime import timedelta,timezone

# %%
# front setting
import matplotlib as mpl
from matplotlib import font_manager
font_times = font_manager.FontProperties(fname="/System/Library/Fonts/Supplemental/Times New Roman.ttf")
font_song = font_manager.FontProperties(fname="/System/Library/Fonts/Supplemental/Songti.ttc")

mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = [
    "Times New Roman",  # 英文 / 数字优先
    "SimSun",           # 中文回退
]

mpl.rcParams["axes.unicode_minus"] = False  # 负号正常显示

# %%
# Basic setting
SCATTERP_SIZE_DEFAULT = 50
ALPHA_DEFAULT = 0.7
# ---- Global style knobs (safe to tweak) ----
plt.rcParams.update({
    "figure.dpi": 160,
    "savefig.dpi": 160,
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})


# %%
# Colors
blue_colors = [
    "#0B3C8C",  # Navy Blue（深海军蓝）
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
    "#005A55",  # Deep Teal
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
    "#0A4E1F",  # Forest Green / Deep Forest Green
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
    "#7A3C00",  # Burnt Orange
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
BLUE_COLOR_ORIGINAL = "#1f77b4"
BLUE_COLOR_DEFAULT = blue_colors[3]
TEAL_COLOR_DEFAULT = teal_colors[3]
ORANGE_COLOR_DEFAULT = orange_colors[4]
PINK_COLOR_DEFAULT = "#f700ff"
GRAY_COLOR_DEFAULT = "#cccccc"

# %%
# Read data from bug_csv_v2.csv (without added source/sink connector information)
df = pd.read_csv("bug_csv_v2.csv")

# Finding 5: Comment Count vs Comment Chars
# Fig 5
df_f5_copy = df.dropna(subset=["tool_total_comments_count", "tool_total_chars"]).copy()
df_f5_copy["tool_total_comments_count"] = df_f5_copy[
    "tool_total_comments_count"
].astype(float)
df_f5_copy["tool_total_chars"] = df_f5_copy["tool_total_chars"].astype(float)

# %%
fig5_1, ax5_1 = plt.subplots(figsize=(7, 5))
# linear regression line and its confidence interval (95% confidence band).
# y = β0 + β1 * x
sns.regplot(
    data=df_f5_copy,
    x="tool_total_comments_count",
    y="tool_total_chars",
    scatter_kws={"alpha": 0.7, "s": SCATTERP_SIZE_DEFAULT},
    line_kws={"color": RED_COLOR_DEFAULT},
    ax=ax5_1,
    color=BLUE_COLOR_DEFAULT,
)
ax5_1.set_title("Comment Count vs Comment Chars", fontsize=14)
ax5_1.set_xlabel("Number of of Comments")
ax5_1.set_ylabel("Comment Size (Characters)")
ax5_1.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()

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
fig5_2, ax5_2 = plt.subplots(figsize=(7,5))
# Main
ax5_2.scatter(
    x=df_f5_copy_main["tool_total_comments_count"],
    y=df_f5_copy_main["tool_total_chars"],
    s=SCATTERP_SIZE_DEFAULT,
    alpha=0.7,
    color=BLUE_COLOR_DEFAULT,
)
ax5_2.scatter(
    x=df_f5_copy_outliers["tool_total_comments_count"],
    y=df_f5_copy_outliers["tool_total_chars"],
    s=SCATTERP_SIZE_DEFAULT,
    alpha=0.7,
    color=PINK_COLOR_DEFAULT,
)
# Annotation + annotation arrowprops
for i, row in df_f5_copy_outliers.iterrows():
  ax5_2.annotate(
    text=row["Bug编号"],
    xy=(
            row["tool_total_comments_count"],
            row["tool_total_chars"]
        ),                     # ← outlier 点坐标
        xytext=(-80, -20),       # ← 标签相对偏移（像素）
        textcoords='offset points',
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
        arrowprops=dict(
            arrowstyle="->",
            color="gray",
            lw=1.2,
            alpha=0.8
        )
  )

# Purple
# sns.scatterplot(
#     data=df_f5_copy_outliers,
#     x="tool_total_comments_count",
#     y="tool_total_chars",
#     color="#f700ff",
#     s=SCATTERP_SIZE_DEFAULT*1.5,
#     alpha=0.7,
#     ax=ax5_2,
#     ="Outliers"
# )
# ax5_2.set_title("Finding 5: Comment Count vs Comment Chars", fontsize=14)
ax5_2.set_title("Finding 5: Comment Count vs Comment Chars")
ax5_2.set_xlabel("Number of of Comments")
ax5_2.set_ylabel("Comment Size (Characters)")
ax5_2.grid(True, linestyle="--", alpha=0.6)
# ax5_2.legend()
plt.show()


fig5_3, ax5_3 = plt.subplots(figsize=(7, 5))
sns.regplot(
    data=df_f5_copy_main,
    x="tool_total_comments_count",
    y="tool_total_chars",
    scatter_kws={"alpha": 0.7, "s": SCATTERP_SIZE_DEFAULT},
    line_kws={"color": "#d62728"},
    ax=ax5_3,
    color= BLUE_COLOR_DEFAULT,
)

# ax5_3.set_title("Finding 5: Comment Count vs Comment Chars", fontsize=14)
ax5_3.set_title("Finding 5: Comment Count vs Comment Chars")
ax5_3.set_xlabel("Number of of Comments")
ax5_3.set_ylabel("Comment Size (Characters)")
ax5_3.grid(True, linestyle="--", alpha=0.6)


plt.tight_layout()
plt.show()


# %%
# Finding 1: Distribution of CDC
import pandas as pd
import re
from collections import Counter


def split_multi_values(val, sep=r";"):
    """Split fields like 'MySQL; PostgreSQL' into ['MySQL', 'PostgreSQL']."""
    if pd.isna(val):
        return []
    s = str(val)
    return [p.strip() for p in re.split(sep, s) if p.strip()]


def aggregate_components(df, column_names: list[str]) -> tuple[Counter, dict]:
    """Aggregate multi columns and return frequency dict."""
    counter = Counter()

    for _, row in df.iterrows():
        merged = []
        for c in column_names:
            l = split_multi_values(row.get(c), sep=r"[;；,]")
            merged += l
        for item in merged:
            counter[item] += 1
    return (counter,dict(counter.most_common()))


df = pd.read_csv("bug_resolved_csv_v3.csv")
counter_old, db_counts = aggregate_components(df, ["Source数据库类型", "Sink数据库类型"])
print(db_counts)

# %%
# Resolve core processor
print(db_counts)

def addition_labels(df, column_names: list[str], target_strings: list[str]) -> tuple[Counter, dict]:
  """Add counter for spectial strings in the specified columns."""

  counter = Counter()
  for _, row in df.iterrows():
    merged = []
    for c in column_names:
      merged += split_multi_values(row.get(c, ""), sep=r"[;；,]")
    for t in target_strings:
      if t in merged:
        counter[t] += 1
  return (counter, dict(counter.most_common()))


counter_addition, db_counts_addition = addition_labels(df, ["tool_labels"], ["e2e-tests","composer", "base", "common", "docs","build","cli"]) # double count for runtime
print(db_counts_addition)
counter_old.update(counter_addition)
db_counts.update(db_counts_addition)
print(counter_old.most_common())
print(db_counts)

# %%
# Finding 1: Distribution of CDC
# Fig 1:
source_set = {"MySQL", "PostgreSQL", "MongoDB", "SQL Server", "Oracle", "DB2", "OceanBase", "Vitness", "TiDB"}
sink_set = {"StarRocks", "Doris", "Kafka", "Paimon", "Iceberg", "Elasticsearch", "Fluss", "MaxCompute", "Values"}
core_processor_set = {"Runtime", "e2e-tests","composer", "base", "common"} # care Runtime case
other_set = {"docs","build","cli"}

db_counts_new = dict(counter_old.most_common())

labels = list(db_counts_new.keys())
values = list(db_counts_new.values())

# --------------------------
# 2. Distribute colors（Source = Blue Family，Sink = Teal Family）
# --------------------------
colors = []
blue_idx = 0
orange_idx = 0
teal_idx = 0
# only one color
for lab in labels:
    if lab in source_set:
        colors.append(blue_colors[blue_idx % len(blue_colors)])
        blue_idx += 1
        # colors.append(BLUE_COLOR_DEFAULT)
    elif lab in core_processor_set:
        colors.append(orange_colors[orange_idx % len(orange_colors)])
        orange_idx += 1
        # colors.append(ORANGE_COLOR_DEFAULT)
    elif lab in other_set:
        colors.append(GRAY_COLOR_DEFAULT)
    else:
        colors.append(teal_colors[teal_idx % len(teal_colors)])
        teal_idx += 1
        # colors.append(TEAL_COLOR_DEFAULT)

# --------------------------
# 3. Percentage format
# --------------------------
def autopct_fmt(pct, allvals):
    total = sum(allvals)
    count = int(round(pct/100.0 * total))
    return f"{pct:.1f}%\n({count})"

# --------------------------
# 4. Plot Pie
# --------------------------
fig1_1, ax1_1 = plt.subplots(figsize=(8, 7))

ax1_1.pie(
    values,
    labels=labels,
    colors=colors,
    startangle=150,
    autopct=lambda pct: autopct_fmt(pct, values),
    pctdistance=0.70,
    textprops={"fontsize": 10}
)

ax1_1.set_title("Database Type Breakdown (Source + Sink)", fontsize=14)
fig1_1.tight_layout()

plt.show()

# %%
items = list(db_counts_new.items())
# Re-order as Source -> -> Core Processor -> Other -> Sink

reordered_items = []
for k, v in items:
  if k in source_set:
    reordered_items.append((k,v))

for k, v in items:
   if k in core_processor_set:
     reordered_items.append((k,v))

for k, v in items:
   if k in other_set:
     reordered_items.append((k,v))

for k, v in items:
  if k in sink_set:
    reordered_items.append((k,v))


for k, v in items:
    if (k not in source_set) and (k not in sink_set) and (k not in core_processor_set) and (k not in other_set):
        print(k,v)
        raise ValueError("Unsupported type.")

# Re-order colors
reordered_labels = [x[0] for x in reordered_items]
print(reordered_labels)
reordered_values = [x[1] for x in reordered_items]
print(reordered_values)
reordered_colors = []

reordered_blue_idx = 0
reordered_teal_idx = 0
reirdered_orange_idx = 0

for lab in reordered_labels:
  if lab in source_set:
    # reordered_colors.append(blue_colors[reordered_blue_idx])
    # reordered_blue_idx+=1
    reordered_colors.append(BLUE_COLOR_DEFAULT)
  elif lab in sink_set:
    # reordered_colors.append(teal_colors[reordered_teal_idx])
    # reordered_teal_idx+=1
    reordered_colors.append(TEAL_COLOR_DEFAULT)
  elif lab in core_processor_set:
    # reordered_colors.append(orange_colors[reirdered_orange_idx])
    # reirdered_orange_idx += 1
    reordered_colors.append(ORANGE_COLOR_DEFAULT)
  elif lab in other_set:
    reordered_colors.append(GRAY_COLOR_DEFAULT)

# Re-order explode
reordered_explode = []

for lab in reordered_labels:
    # if lab in source_set:
    #     reordered_explode.append(0.09)
    # elif lab in sink_set:
    #     reordered_explode.append(0.12)
    if lab in core_processor_set:
        reordered_explode.append(0.18)
    elif lab in other_set:
       reordered_explode.append(0.00)
    else:
        reordered_explode.append(0.00)

fig1_2, ax1_2 = plt.subplots(figsize=(8, 7))

ax1_2.pie(
    reordered_values,
    labels=reordered_labels,
    colors=reordered_colors,
    explode=reordered_explode,
    startangle=60,
    autopct=lambda pct: autopct_fmt(pct, values),
    pctdistance=0.70,
    textprops={"fontsize": 10},
    # wedgeprops={"linewidth": 1.0, "edgecolor": "white"},
)

ax1_2.set_title("Bug Trigger Places Breakdown (Pie Chart)", fontsize=14)
fig1_2.tight_layout()
plt.show()

# %%
fig1_3, ax1_3 = plt.subplots(figsize=(10,6))
# We reuse: reordered_labels, reordered_values, reordered_colors

# X-axis positions
x_positions = np.arange(len(reordered_labels))

# Draw bars
ax1_3.bar(
    x_positions,
    reordered_values,
    color=reordered_colors,
    # edgecolor="gray",
    linewidth=0.8
)

# axvline
ax1_3.axvline(6.5, linestyle='--', color='gray')
ax1_3.axvline(14.5, linestyle='--', color='gray')

# Labeling
ax1_3.set_xticks(x_positions)
ax1_3.set_xticklabels(reordered_labels, rotation=45, ha="right")

# Group labeling
trans = ax1_3.get_xaxis_transform()

ax1_3.text(3, -0.25, "源连接器", transform=trans, ha="center", va="top", fontsize=12, fontproperties=font_song)
ax1_3.text(10.5, -0.25, "核心执行器", transform=trans, ha="center", va="top", fontsize=12, fontproperties=font_song)
ax1_3.text(18.5, -0.25, "汇连接器", transform=trans, ha="center", va="top", fontsize=12, fontproperties=font_song)

# annotate
def draw_group_bracket(ax, x0, x1, y_axes=-0.28, tick=0.02, lw=1.2, color="gray"):
    """
    x0, x1: 数据坐标（你的 bar 的 x index）
    y_axes: 轴坐标（0 是 x 轴位置，负数是轴下方）
    tick:   端点向下的长度（轴坐标单位）
    """
    trans = ax.get_xaxis_transform()  # x用数据坐标，y用轴坐标

    # horizontal line
    ax.plot([x0, x1], [y_axes, y_axes], transform=trans, lw=lw, color=color, clip_on=False)
    # left downward tick
    ax.plot([x0, x0], [y_axes, y_axes - tick], transform=trans, lw=lw, color=color, clip_on=False)
    # right downward tick
    ax.plot([x1, x1], [y_axes, y_axes - tick], transform=trans, lw=lw, color=color, clip_on=False)
# ax1_3.annotate(
#     text="",
#     xy=( 2.4, -0.25), xytext=(-0.4, -0.25),
#     xycoords=trans,
#     textcoords=trans,
#     arrowprops=dict(arrowstyle="-[", lw=1)
# )
# Source: 0..6
draw_group_bracket(ax1_3, 0,  6, y_axes=-0.22, tick=-0.02)
draw_group_bracket(ax1_3, 7, 14, y_axes=-0.22, tick=-0.02)
draw_group_bracket(ax1_3, 15, 22, y_axes=-0.22, tick=-0.02)

ax1_3.set_ylabel("触发数量（个）", fontsize=12, fontproperties=font_song)
# ax1_3.set_title("变更捕获工具故障触发位置", fontsize=14, fontproperties=font_song)


# Adding numeric annotations on top of bars
for i, v in enumerate(reordered_values):
    ax1_3.text(i, v + max(reordered_values)*0.015,
             str(v),
             ha="center", va="bottom", fontsize=10)

fig1_3.tight_layout()
fig1_3.savefig("fig_2_bug_trigger_locations.png", dpi=300, bbox_inches="tight")
plt.show()


# %%
# Finding 2: Relationship between content/comment chars and fixed time

## Normalize time in ISO8601 format
def normalize_datetime_column(df, colname, utc=True):
    """
    Normalize any datetime-like column into strict ISO 8601 format.
    Parameters:
        df (pd.DataFrame)
        colname (str): column name to normalize
        utc (bool): convert to UTC with Z suffix
    Returns:
        pd.DataFrame (modified in-place)
    """
    def parse_to_iso8601(val):
        if pd.isna(val):
            return None
        try:
            date_time = parser.parse(str(val))
            if utc:
                # date_time = date_time.tz("Asia/Shanghai", nonexistent='shift_forward', ambiguous='NaT').tz_convert("UTC")
                return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                return date_time.isoformat()
        except Exception:
            # fallback: return as original to inspect later
            return val
    # # TODO error parse
    # def parse_to_datetime64(val):
    #     return parser.parse(str(val))

    df[colname] = df[colname].apply(parse_to_iso8601)
    # df[colname] = df[colname].apply(parse_to_datetime64)
    return df


def normalize_datetime_columns(df, cols: list[str]):
    """
    Normalize multiple datetime columns to ISO 8601 UTC Z format.
    Parameters:
        df (pd.DataFrame)
        cols (list[str]): list of column names
    Returns:
        pd.DataFrame
    """
    for col in cols:
        df = normalize_datetime_column(df, col)
    return df

df_2 = pd.read_csv("bug_resolved_csv_v4.csv")

reformat_datetime_cols = [
    "首次报告时间",
    "确认修复时间",
    "tool_created_at",
    "tool_merged_at",
]

normalize_datetime_columns(df_2, cols=reformat_datetime_cols)


# %%
tolerance_days = 2.0
tolerance_seconds = tolerance_days * 86400.0
df_2_copy = df_2.dropna(subset=["tool_created_at", "tool_merged_at"]).copy()
# 138 (full information resolved) to 154 (resolved)

## Per row operation is too slow
# df_2_copy["确认修复时间"] = df_2_copy["确认修复时间"].apply(lambda x: parser.parse(x))
# df_2_copy["tool_merged_at"] = df_2_copy["tool_merged_at"].apply(lambda x: parser.parse(x))

## Faster way use datetime transform
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
# TODO: some pr create even earlier than report, try fix
df_2_copy["duration_start"] = (df_2_copy["t_pr_created"] - df_2_copy["t_report"]).apply(
    lambda x: max(x, pd.Timedelta(0))
)
df_2_copy["duration_success"] = df_2_copy["t_fix"] - df_2_copy["t_pr_created"]

# ==========================================================
# C) 验证：总 = 启动 + 成功
# ==========================================================

df_2_copy["check_sum"] = (
    df_2_copy["duration_start"] + df_2_copy["duration_success"]
) - df_2_copy["duration_total"]

print("\n[总 != 启动 + 成功 的记录] (理论应全为 0 ± ε):")
bad_sum = df_2_copy[
    df_2_copy["check_sum"].abs() > timedelta(seconds=1)
]  # 允许 1 秒浮动
print(
    bad_sum[
        ["Bug编号", "duration_total", "duration_start", "duration_success", "check_sum"]
    ]
)


# ==========================================================
# D) 事后比对：总修复时长 vs CSV 中 "修复周期"
#    （误差 ≤ 2 天）
# ==========================================================
# 解析表格中的 “修复周期” 为 timedelta
def parse_duration(s):
    # 格式类似 "4d 10:24:56"
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
# df_2_copy.duration_total
# df_2_copy.duration_total_csv
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
# Fig CDF

fig_cdf, ax_cdf = plt.subplots(figsize=(5,3))
cdf_days = (
    df_2_copy["duration_total_csv"]
    .dropna()
    .dt.total_seconds() / 86400.0
)
x = np.sort(cdf_days.to_numpy())
y = np.arange(1, len(x) + 1) / len(x)
ax_cdf.step(x, y, where="post", linewidth=1.8, color=BLUE_COLOR_DEFAULT)
ax_cdf.set_xlim(left=0)
ax_cdf.set_ylim(0, 1)
ax_cdf.set_xlabel("Report-to-Fix Time (days)")
ax_cdf.set_ylabel("CDF")
ax_cdf.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()

fig_cdf_2, ax_cdf_2 = plt.subplots(figsize=(5,3))
ax_cdf_2.step(x, y, where="post", linewidth=1.8, color=BLUE_COLOR_DEFAULT)
ax_cdf_2.set_xlim(left=0)
ax_cdf_2.set_ylim(0,1)
ax_cdf_2.set_xlabel("报告至修复周期（天）", fontproperties=font_song)
ax_cdf_2.set_ylabel("CDF")
ax_cdf_2.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
fig_cdf_2.savefig("fig_3_cdf_of_fixing_time.png", dpi=300, bbox_inches="tight")

plt.show()

# %%
df_people = pd.read_csv("bug_resolved_csv_v4.csv")

people = (
  df_people["tool_people_involved_count"]
    .dropna()
    .astype(int)
)
people_counts = (
  people
  .value_counts()
  .sort_index()
)
# people_counts

fig_people, ax_people = plt.subplots(figsize=(5,3))
ax_people.bar(
  people_counts.index.to_numpy(),
  people_counts.values,
  width=0.8,
  color=BLUE_COLOR_DEFAULT,
  linewidth=0.8
)
ax_people.set_xlabel("参与讨论人数（个）", fontproperties=font_song)
ax_people.set_ylabel("Bug 数量（个）", fontproperties=font_song)
ax_people.set_ylim(0,80)

ax_people.set_xticks(people_counts.index.to_numpy())
ax_people.tick_params(axis="both", labelsize=11)

# Adding numeric annotations on top of bars
for xi, yi in zip(people_counts.index.to_numpy(), people_counts.values):
    ax_people.text(xi, yi, str(yi),
            ha="center", va="bottom", fontsize=10)

# # grid（只开 y 轴，论文常见）
# ax_people.grid(axis="y", linestyle="--", linewidth=0.8, alpha=0.6)
# ax_people.grid(axis="x", visible=False)

ax_people.axhline(
    y=40,
    linestyle="--",
    linewidth=0.8,
    color="gray",
    alpha=0.6
)

fig_people.tight_layout()
plt.show()

# %%
df = pd.read_csv("bug_resolved_csv_v4.csv")

# 1) 取 comments count（注意你表里还有一个 tool_total_comments_count.1，别搞混）
comments = (
    df["tool_total_comments_count"]
    .dropna()
    .astype(int)
)

# 2) 分箱（论文更友好：头部保留，尾部合并）
# 0,1,2,3,4,5,6-10,11-20,>20
bins = [-0.5, 5.5, 10.5, 15.5, 20.5, np.inf]
labels = ["0-5", "6-10", "11–15","16-20", ">20"]

comments_binned = pd.cut(comments, bins=bins, labels=labels)
comments_counts = comments_binned.value_counts().reindex(labels).fillna(0).astype(int)

# 3) 画图
fig_cmt, ax_cmt = plt.subplots(figsize=(5, 3))

x_labels = comments_counts.index.tolist()
x_pos = np.arange(len(x_labels))
y_vals = comments_counts.values

ax_cmt.bar(
    x_pos,
    y_vals,
    width=0.8,
    color=BLUE_COLOR_DEFAULT,
    linewidth=0.8
)

ax_cmt.set_xlabel("讨论轮次（个）", fontproperties=font_song)
ax_cmt.set_ylabel("Bug 数量（个）", fontproperties=font_song)
ax_cmt.set_ylim(0, max(80, y_vals.max() + 5))

ax_cmt.set_xticks(x_pos)
ax_cmt.set_xticklabels(x_labels)
ax_cmt.tick_params(axis="both", labelsize=11)

# 数值标注
for xi, yi in zip(x_pos, y_vals):
    if yi > 0:
        ax_cmt.text(xi, yi, str(yi), ha="center", va="bottom", fontsize=10)

# 只画 y=40 参考线
ax_cmt.axhline(y=40, linestyle="--", linewidth=0.8, color="gray", alpha=0.6)

fig_cmt.tight_layout()
plt.show()

# %%
# Finding 2: Relationship between content/comment chars and fixed time
# Fig 2
df_2_copy["duration_total_days"] = df_2_copy["duration_total"].dt.total_seconds() / 86400.0
# --- Plot ---
fig2_1, ax2_1 = plt.subplots(figsize=(7, 5))

df_2_spectial = df_2_copy[
  (df_2_copy["duration_total_days"] > 100)
]
print(df_2_spectial["Bug编号"])
print(df_2_spectial["duration_total_days"])
print(df_2_spectial["tool_total_chars"])

## Linear regression
# sns.regplot(
#     data=df_2_copy,
#     x="duration_total_days",
#     y="tool_total_chars",
#     scatter_kws={"alpha": 0.7, "s": SCATTERP_SIZE_DEFAULT},
#     line_kws={"color": RED_COLOR_DEFAULT, "linewidth": 2.0},
#     color=BLUE_COLOR_DEFAULT,
#     ax=ax2_1
# )
ax2_1.scatter(
    x=df_2_copy["tool_total_chars"],
    y=df_2_copy["duration_total_days"],
    s=SCATTERP_SIZE_DEFAULT,
    alpha=0.7,
    color=BLUE_COLOR_DEFAULT,
)

## Just scat

ax2_1.set_title("Repair Duration vs Total Text Volume", fontsize=14)
ax2_1.set_xlabel("Text Volume (chars)")
ax2_1.set_ylabel("Repair Duration (days)")
ax2_1.grid(True, linestyle="--", alpha=0.6)

plt.tight_layout()
plt.show()

# %%
fig2_3,ax2_3 = plt.subplots(figsize=(7,5))

df_2_copy['tmp_div'] =df_2_copy["tool_total_chars"]/df_2_copy["duration_total_days"]
print(df_2_copy['tmp_div'])

ax2_3.scatter(
    x=df_2_copy["tool_total_chars"],
    y=df_2_copy["tmp_div"],
    s=SCATTERP_SIZE_DEFAULT,
    alpha=0.7,
    color=BLUE_COLOR_DEFAULT,
)

## Just scat

ax2_3.set_title("Repair Destiny vs Total Text Volume", fontsize=14)
ax2_3.set_xlabel("Text Volume (chars)")
ax2_3.set_ylabel("Text Volume/Repair Duration (c/days)")
ax2_3.grid(True, linestyle="--", alpha=0.6)

plt.tight_layout()
plt.show()

# %%
# plt.figure(figsize=(8, 6))

# hb = plt.hexbin(
#     df_2_copy["duration_total_days"],
#     df_2_copy["tool_total_chars"],
#     gridsize=40,
#     cmap="Blues",
#     mincnt=1
# )

# plt.colorbar(hb, label="Count")
# plt.xlabel("Repair Duration (days)")
# plt.ylabel("Text Volume (chars)")
# plt.title("2D Density Heatmap: Duration vs Text Volume")

# plt.tight_layout()
# plt.show()

# %%
# =============================
# 1. 准备数据（排序）
# =============================
df_dual = df_2_copy[
    ["Bug编号", "tool_total_chars", "duration_total","duration_start","duration_success", "duration_total_days"]
].copy()

df_dual["duration_start_days"] = df_2_copy["duration_start"].dt.total_seconds() / 86400.0

# 修复时长转换为天
# df_dual["duration_total_days"] = df_dual["duration_total"].dt.total_seconds() / 86400.0

# 按修复时长排序
df_dual = df_dual.sort_values("duration_total_days").reset_index(drop=True)

x = np.arange(len(df_dual))  # bug index after sorting

# =============================
# 2. 创建图
# =============================
fig2_2, ax2_2 = plt.subplots(figsize=(11, 5))

# ---- 左轴（修复时间折线） ----
ax2_2.plot(
    x,
    df_dual["duration_total_days"],
    color=BLUE_COLOR_DEFAULT,  # 蓝色（你的 blue palette 第3色）
    linewidth=2.0,
    label="Repair Duration (days)",
)

# ---- 左轴 额外（显示启动修复时间）
ax2_2.plot(
  x,
  df_dual["duration_start_days"],
  color=TEAL_COLOR_DEFAULT,
  linewidth=2.0,
  label="Start Pull Request (days)"
)

ax2_2.legend()
ax2_2.set_xlabel("Bug Index (sorted by repair duration)")
ax2_2.set_ylabel("Repair Duration (days)", color=BLUE_COLOR_DEFAULT)
ax2_2.tick_params(axis="y", labelcolor=BLUE_COLOR_DEFAULT)
ax2_2.grid(True, linestyle="--", alpha=0.5)

# ---- 右轴（文本量柱状） ----
ax2_2_copy = ax2_2.twinx()

ax2_2_copy.bar(
    x,
    df_dual["tool_total_chars"],
    color=ORANGE_COLOR_DEFAULT,
    alpha=0.5,
    label="Text Volume (chars)",
)

ax2_2_copy.set_ylabel("Text Volume (chars)", color=ORANGE_COLOR_DEFAULT)
ax2_2_copy.tick_params(axis="y", labelcolor=ORANGE_COLOR_DEFAULT)

# =============================
# 3. 标题与布局
# =============================
plt.title("Dual-Axis Chart: Repair Duration vs Text Volume", fontsize=14)
fig2_2.tight_layout()
plt.show()

# %%
# df_dual1 = df_2_copy[[
#     "Bug编号",
#     "duration_total",
#     "duration_total_days",
#     "tool_total_chars"
# ]].copy()

# # df_dual1["duration_total_days"] = df_dual1["duration_total"].dt.total_seconds() / 86400.0

# # 排序（趋势更清晰）
# df_dual1 = df_dual1.sort_values("duration_total_days").reset_index(drop=True)
# x = np.arange(len(df_dual1))

# # Colors
# COLOR_BAR = BLUE_COLOR_DEFAULT   # 蓝色（柱状）
# COLOR_LINE = TEAL_COLOR_DEFAULT  # 青绿色（折线）

# # =============================
# # 图形
# # =============================
# fig, ax2_3 = plt.subplots(figsize=(12, 6))

# # 左轴：柱状图（修复总时长）
# ax2_3.bar(
#     x,
#     df_dual1["duration_total_days"],
#     color=COLOR_BAR,
#     alpha=0.7,
#     label="Repair Duration (days)"
# )
# ax2_3.set_ylabel("Repair Duration (days)", color=COLOR_BAR)
# ax2_3.tick_params(axis="y", labelcolor=COLOR_BAR)
# ax2_3.set_xlabel("Bug Index (sorted by repair duration)")
# ax2_3.grid(True, linestyle="--", alpha=0.5)

# # 右轴：折线图（文本量）
# ax2_3_copy = ax2_3.twinx()
# ax2_3_copy.plot(
#     x,
#     df_dual1["tool_total_chars"],
#     color=COLOR_LINE,
#     linewidth=2.0,
#     label="Text Volume (chars)"
# )
# ax2_3_copy.set_ylabel("Text Volume (chars)", color=COLOR_LINE)
# ax2_3_copy.tick_params(axis="y", labelcolor=COLOR_LINE)

# # 图例组合
# h1, l1 = ax2_3.get_legend_handles_labels()
# h2, l2 = ax2_3_copy.get_legend_handles_labels()
# ax2_3.legend(h1 + h2, l1 + l2, loc="upper left")

# plt.title("Dual-Axis Chart (Bar: Repair Duration | Line: Text Volume)", fontsize=15)
# plt.tight_layout()
# plt.show()

# %%
# D值难度模型绘图
df_people = pd.read_csv("bug_resolved_csv_v4.csv")
def parse_duration_to_hours(x):
    """
    将修复周期字符串转换为小时数。
    支持：
    - '33d 18:45:46'
    - '18:45:46'
    - 数值（默认直接返回）
    """
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
    """
    优先使用 tool_total_files_count；
    若缺失，则尝试由 tool_files_changed 推导。
    """
    # 方案 1：直接用总文件数
    if "tool_total_files_count" in row.index and pd.notna(row["tool_total_files_count"]):
        return float(row["tool_total_files_count"])

    # 方案 2：从文件列表推导
    if "tool_files_changed" in row.index and pd.notna(row["tool_files_changed"]):
        raw = str(row["tool_files_changed"]).strip()
        if raw == "":
            return np.nan

        # 常见分隔符兼容
        for sep in [";", ",", "\n", "|"]:
            if sep in raw:
                parts = [p.strip() for p in raw.split(sep) if p.strip()]
                if len(parts) > 0:
                    return float(len(set(parts)))

        # 只有一个文件路径
        return 1.0

    return np.nan

def zscore(series):
    """
    标准化，使用总体标准差(ddof=0)，与很多工程脚本更一致。
    """
    mean_ = series.mean()
    std_ = series.std(ddof=0)
    if std_ == 0 or pd.isna(std_):
        return pd.Series([0] * len(series), index=series.index)
    return (series - mean_) / std_


def minmax_0_100(series):
    """
    线性映射到 0-100。
    """
    s_min = series.min()
    s_max = series.max()
    if s_max == s_min:
        return pd.Series([50] * len(series), index=series.index)
    return (series - s_min) / (s_max - s_min) * 100

def grade_equal_width(d100):
    """
    按论文中最常见的等宽区间分级：
    [0,20), [20,40), [40,60), [60,80), [80,100]
    """
    bins = [-1e-9, 20, 40, 60, 80, 100 + 1e-9]
    labels = ["极低", "低", "中等", "高", "极高"]
    return pd.cut(d100, bins=bins, labels=labels, include_lowest=True, right=False)

# =========================================================
# 1. 构建 D 模型分析子表
# =========================================================
df_tmp = df_people.copy()

# --- 1.1 统一字段命名（按你的论文习惯） ---
# Bug ID
if "Bug编号" not in df.columns:
    raise ValueError("CSV 中缺少 'Bug编号' 列，请先核对文件。")

# 修复周期（小时）
if "修复周期" not in df.columns:
    raise ValueError("CSV 中缺少 '修复周期' 列，请先核对文件。")

df_tmp["repair_hours"] = df_tmp["修复周期"].apply(parse_duration_to_hours)

# 评论次数
if "tool_total_comments_count" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'tool_total_comments_count' 列。")
df_tmp["comment_count"] = pd.to_numeric(df_tmp["tool_total_comments_count"], errors="coerce")

# 评论字数
if "tool_total_chars" not in df_tmp.columns:
    raise ValueError("CSV 中缺少 'tool_total_chars' 列。")
df_tmp["comment_chars"] = pd.to_numeric(df_tmp["tool_total_chars"], errors="coerce")

# 修改文件数
df_tmp["files_changed_count"] = df_tmp.apply(derive_file_count, axis=1)

# 修改代码行数
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


# =========================================================
# 2. 样本筛选
# =========================================================
# 规则：
# A. 五个指标都不为空
# B. 可选：去掉 comment_count=0 且 comment_chars=0 的样本
#
# 这一步是你当前论文里最可能导致 136 样本的地方。
# 如果你想保留更宽松口径，只删掉完整性缺失样本，把 strict_discussion_filter=False 即可。

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

# =========================================================
# 3. 计算 Z 值、D_raw、D_100、等级
# =========================================================
# 你的论文里如果写的是 Zr/Zc/Zw/Zf/Zl，就这样命名：
# Zr: 修复周期（repair）
# Zc: 评论次数（comments）
# Zw: 评论字数（words/chars）
# Zf: 修改文件数（files）
# Zl: 修改代码行数（loc）

df_d["Zr"] = zscore(df_d["repair_hours"])
df_d["Zc"] = zscore(df_d["comment_count"])
df_d["Zw"] = zscore(df_d["comment_chars"])
df_d["Zf"] = zscore(df_d["files_changed_count"])
df_d["Zl"] = zscore(df_d["loc_changed"])

# D 原始加权分数
df_d["D_raw"] = (
    0.40 * df_d["Zr"]
    + 0.10 * df_d["Zc"]
    + 0.10 * df_d["Zw"]
    + 0.25 * df_d["Zf"]
    + 0.15 * df_d["Zl"]
)

# =========================================================
# 参数开关
# =========================================================

# 是否强制删除已知异常样本
remove_known_bad_cases = True

# 需要强制删除的异常样本 ID
bad_case_ids = ["FLINK-36763"]

# 是否删除 D_raw 极端值（IQR）
remove_outliers = True

# IQR 系数，常用 1.5
iqr_k = 1.5

# =========================================================
# 步骤 A：先按人工指定列表，强制删除已知异常样本
# 说明：
# 这里用于处理像 FLINK-36763 这种已经确认统计值异常、
# 不应参与正式分析的样本。
# 无论后面是否做 IQR，都会先执行这一步。
# =========================================================
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
        bad_rows[["Bug编号", "D_raw"]].to_csv(
            "d_known_bad_cases_removed.csv",
            index=False,
            encoding="utf-8-sig"
        )
        print("已保存：d_known_bad_cases_removed.csv")
    else:
        print("指定的异常样本未在当前分析样本中找到")
else:
    print("未启用人工指定异常样本删除")


# =========================================================
# 步骤 B：可选执行 IQR 极端值过滤
# 说明：
# 这一阶段是在“已经剔除已知异常样本”之后，
# 再对剩余样本按 D_raw 分布自动识别极端值。
# 这样可以比较：
# A. 只删已知异常样本
# B. 删已知异常样本 + 再做 IQR 稳健性分析
# =========================================================
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
        outlier_rows.to_csv("d_outliers_removed.csv", index=False, encoding="utf-8-sig")
        print("已保存：d_outliers_removed.csv")
    else:
        print("没有检测到 IQR 极端值")
else:
    print("未启用极端值过滤（IQR）")


# =========================================================
# 在清洗后的样本基础上，再做 0-100 线性映射和分级
# =========================================================
df_d["D_100"] = minmax_0_100(df_d["D_raw"])
df_d["难度等级"] = grade_equal_width(df_d["D_100"])

# 方便检查排序
df_d = df_d.sort_values("D_100", ascending=True).reset_index(drop=True)

# =========================================================
# 4. 保存新表
# =========================================================
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

df_d[output_cols].to_csv("d_model_subtable.csv", index=False, encoding="utf-8-sig")
print("已保存：d_model_subtable.csv")


# %%
# =========================================================
# 5. 可视化 1：D_100 分布直方图 + 分级边界
# =========================================================
plt.figure(figsize=(8, 4.8))
sns.histplot(df_d["D_100"], bins=20, kde=False)

# 分级边界线
for x in [20, 40, 60, 80]:
    plt.axvline(x=x, linestyle="--", linewidth=1)

plt.xlabel("D值（0–100）", fontproperties=font_song, fontsize=11)
plt.ylabel("错误数量", fontproperties=font_song, fontsize=11)
plt.title("修复难度得分分布", fontproperties=font_song, fontsize=12)

plt.xticks(fontproperties=font_times, fontsize=10)
plt.yticks(fontproperties=font_times, fontsize=10)
plt.tight_layout()
plt.savefig("d_score_histogram.png", dpi=300, bbox_inches="tight")
plt.show()


# =========================================================
# 6. 可视化 2：难度分级计数柱状图
# =========================================================
grade_order = ["极低", "低", "中等", "高", "极高"]
grade_counts = df_d["难度等级"].value_counts().reindex(grade_order, fill_value=0)

plt.figure(figsize=(7.2, 4.8))
bars = plt.bar(grade_counts.index, grade_counts.values)

# 柱顶标数值
for bar, val in zip(bars, grade_counts.values):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        str(val),
        ha="center",
        va="bottom",
        fontproperties=font_times,
        fontsize=10
    )

plt.xlabel("难度等级", fontproperties=font_song, fontsize=11)
plt.ylabel("错误数量", fontproperties=font_song, fontsize=11)
plt.title("修复难度分级统计", fontproperties=font_song, fontsize=12)

plt.xticks(fontproperties=font_song, fontsize=10)
plt.yticks(fontproperties=font_times, fontsize=10)
plt.tight_layout()
plt.savefig("d_grade_counts.png", dpi=300, bbox_inches="tight")
plt.show()


# =========================================================
# 7. 可视化 3：难度分级占比柱状图
# =========================================================
grade_ratio = grade_counts / grade_counts.sum() * 100

plt.figure(figsize=(7.2, 4.8))
bars = plt.bar(grade_ratio.index, grade_ratio.values)

for bar, val in zip(bars, grade_ratio.values):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.3,
        f"{val:.1f}%",
        ha="center",
        va="bottom",
        fontproperties=font_times,
        fontsize=10
    )

plt.xlabel("难度等级", fontproperties=font_song, fontsize=11)
plt.ylabel("占比（%）", fontproperties=font_song, fontsize=11)
plt.title("修复难度分级占比", fontproperties=font_song, fontsize=12)

plt.xticks(fontproperties=font_song, fontsize=10)
plt.yticks(fontproperties=font_times, fontsize=10)
plt.tight_layout()
plt.savefig("d_grade_ratio.png", dpi=300, bbox_inches="tight")
plt.show()


# =========================================================
# 8. 输出分级统计表，方便你核对
# =========================================================
summary = pd.DataFrame({
    "难度等级": grade_order,
    "错误数量": grade_counts.values,
    "占比(%)": np.round(grade_ratio.values, 1)
})
print(summary)

summary.to_csv("d_grade_summary.csv", index=False, encoding="utf-8-sig")
print("已保存：d_grade_summary.csv")

# %%
# ========= 1. 抽取用于热力图的三列 =========
heatmap_df = df_people[[
    "tool_people_involved_count",
    "tool_total_comments_count",
    "tool_total_chars"
]].copy()

# 转成数值，非法值转 NaN
for col in heatmap_df.columns:
    heatmap_df[col] = pd.to_numeric(heatmap_df[col], errors="coerce")

# 删除缺失值
heatmap_df = heatmap_df.dropna().copy()

print("用于热力图的样本数：", len(heatmap_df))

# ========= 2. 改成论文中的中文列名 =========
heatmap_df.columns = ["参与讨论人数", "评论次数", "评论字数"]

# ========= 3. 计算 Pearson 相关系数矩阵 =========
corr_matrix = heatmap_df.corr(method="pearson")
print(corr_matrix)

# ========= 4. 绘制热力图 =========
plt.figure(figsize=(5, 4))

ax = sns.heatmap(
    corr_matrix,
    annot=True,           # 显示数值
    fmt=".3f",            # 保留 3 位小数
    cmap="coolwarm",      # 和你图里风格接近
    vmin=0, vmax=1,       # 你的图是 0 到 1
    square=True,
    linewidths=0.5,
    cbar=True,
    annot_kws={"size": 9}
)

plt.xticks(fontproperties=font_song, fontsize=9, rotation=45, ha="right")
plt.yticks(fontproperties=font_song, fontsize=9, rotation=0)

plt.tight_layout()
plt.savefig("fig_4_community_response_heatmap.png", dpi=300, bbox_inches="tight")
plt.show()

# %%
