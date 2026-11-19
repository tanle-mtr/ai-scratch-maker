#!/usr/bin/env bash
# 统一验收编排器：把「全量构建 + 八层校验 + 铁律检查器 + 语义回归 + 全量启动冒烟
# + 逐作品行为回归 + 质量门禁 + 增量嗅觉」串成一条命令，给出统一的 PASS/FAIL 与退出码。
#
# 设计原则：
#   - 不中途 abort（不用 set -e）：任一层失败只记一笔，继续跑完，最后统一汇总。
#   - 每一层都是「宽/深网」的一环，缺哪一层都会漏掉一类缺陷。
#   - 退出码：0 = 全部通过；1 = 存在任意一层失败。
#
# 用法：
#   bash scripts/verify_project.sh
#   bash scripts/verify_project.sh --no-cache        # 全量重建（默认即重建）
#   bash scripts/verify_project.sh --skip-build      # 跳过构建（用现有 examples/output）
#   bash scripts/verify_project.sh --jobs 4          # 行为回归并行（见 regress_behavior.sh）
#   bash scripts/verify_project.sh --with-playtest   # 阶段6 额外跑抽样 VM 试玩（较慢）
#   bash scripts/verify_project.sh --strict-advisory # 阶段6 的建议项也计入 FAIL（CI 用）
#   bash scripts/verify_project.sh --only-advisory   # 只跑阶段6（秒级，调试建议层用）
set -u
cd "$(dirname "$0")/.." || exit 1

NO_CACHE=1
SKIP_BUILD=0
SKIP_REGRESS=0
WITH_PLAYTEST=0
STRICT_ADVISORY=0
ONLY_ADVISORY=0
JOBS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --no-cache)   NO_CACHE=1; shift;;
    --skip-build) SKIP_BUILD=1; shift;;
    --skip-regress) SKIP_REGRESS=1; shift;;
    --with-playtest) WITH_PLAYTEST=1; shift;;
    --strict-advisory) STRICT_ADVISORY=1; shift;;
    --only-advisory) ONLY_ADVISORY=1; shift;;
    --jobs)       JOBS="${2:-1}"; shift 2;;
    *) shift;;
  esac
done
if [ "$JOBS" -lt 1 ] 2>/dev/null; then JOBS=1; fi

OUT=examples/output
# 用 Python 生成临时目录，并直接把反斜杠换成斜杠（Windows 上 python/node 都认 /，
# 但反斜杠嵌进 `python -c` 字符串字面量会被当成 \U 等转义而 SyntaxError，必须转掉）。
EXTRACT=$(python -c "import tempfile,os; print(tempfile.mkdtemp(prefix='verify_').replace(chr(92),'/'))")
trap 'rm -rf "$EXTRACT"' EXIT

PASS_SECTIONS=0
FAIL_SECTIONS=0
report() {  # $1=名称 $2=OK/FAIL
  if [ "$2" = "OK" ]; then
    echo "  ✅ $1"
    PASS_SECTIONS=$((PASS_SECTIONS+1))
  else
    echo "  ❌ $1"
    FAIL_SECTIONS=$((FAIL_SECTIONS+1))
  fi
}

echo "=================================================="
echo "  ai-scratch-maker 统一验收"
echo "  时间: $(date '+%H:%M:%S')"
echo "=================================================="

# --only-advisory 时跳过阶段 0–5，直接到阶段 6（调试建议层无需等 40 分钟结构校验）
if [ "$ONLY_ADVISORY" != "1" ]; then

# --- 阶段 0：全量构建（保证 examples/output 与源 IR 一致）---
echo
echo ">>> 阶段 0：全量构建 examples/*.{yaml,json} -> $OUT"
if [ "$SKIP_BUILD" = "1" ]; then
  echo "  （--skip-build，跳过）"
  report "全量构建" "OK"
else
  if [ "$NO_CACHE" = "1" ]; then
    python scripts/build_all.py --no-cache > "$EXTRACT/build.log" 2>&1
  else
    python scripts/build_all.py > "$EXTRACT/build.log" 2>&1
  fi
  if grep -q "BUILD_ALL_OK" "$EXTRACT/build.log"; then
    report "全量构建" "OK"
  else
    report "全量构建" "FAIL"
    tail -20 "$EXTRACT/build.log"
  fi
fi

# --- 阶段 0.5：生成管线自检（generate_staged 端到端，证明十件套链路健康）---
# 每轮全量验收都跑一次「脚手架→构建→门禁→评分卡」的编排，确保新工具链本身没坏；
# 用完即清理，不污染 57 个作品与规格表统计。
echo
echo ">>> 阶段 0.5：生成管线自检（generate_staged：脚手架→构建→门禁→评分卡）"
SELFTEST_SLUG=_staged_selftest
if python scripts/generate_staged.py --genre catch --name 验收自检样例 --slug "$SELFTEST_SLUG" --skip-hard-rules > "$EXTRACT/staged.log" 2>&1 \
   && grep -q "GENERATE_STAGED_OK" "$EXTRACT/staged.log"; then
  report "生成管线自检" "OK"
else
  report "生成管线自检" "FAIL"
  tail -25 "$EXTRACT/staged.log"
fi
# 清理自检产物（脚手架/规格表/构建产物/.assets.md 等，凡以该 slug 命名的都删），避免污染后续阶段统计
rm -f "examples/$SELFTEST_SLUG".* "examples/output/$SELFTEST_SLUG".*

# --- 阶段 1：八层结构校验（L1 / L2 / L3 / L4 跑全 54 作品）---
echo
echo ">>> 阶段 1：八层结构校验（L1 结构 / L2 schema / L3 parser / L4 runtime）"
l1=0; l2=0; l3=0; l4=0; l1f=""; l2f=""; l3f=""; l4f=""
n=0
for f in "$OUT"/*.sb3; do
  [ -e "$f" ] || continue
  n=$((n+1))
  base=$(basename "$f" .sb3)
  pj="$EXTRACT/$base.project.json"
  python -c "import zipfile,sys; zipfile.ZipFile('$f').extract('project.json','$EXTRACT')" >/dev/null 2>&1 \
    && mv "$EXTRACT/project.json" "$pj" 2>/dev/null
  # L1 结构校验
  if python scripts/validate_sb3.py --sb3 "$f" 2>/dev/null | grep -q "全部校验通过"; then
    l1=$((l1+1)); else l1f="$l1f $base"; fi
  # L2 schema
  if [ -f "$pj" ] && node scripts/validate_schema.mjs "$pj" 2>/dev/null | grep -q "SCHEMA_OK"; then
    l2=$((l2+1)); else l2f="$l2f $base"; fi
  # L3 parser
  if node scripts/validate_parser.mjs "$f" 2>/dev/null | grep -q "PARSER_OK"; then
    l3=$((l3+1)); else l3f="$l3f $base"; fi
  # L4 runtime
  if [ -f "$pj" ] && node scripts/validate_runtime.mjs "$pj" 2>/dev/null | grep -q "RUNTIME_OK"; then
    l4=$((l4+1)); else l4f="$l4f $base"; fi
done
echo "  L1 结构: $l1/$n  ${l1f:+失败:$l1f}"
echo "  L2 schema: $l2/$n  ${l2f:+失败:$l2f}"
echo "  L3 parser: $l3/$n  ${l3f:+失败:$l3f}"
echo "  L4 runtime: $l4/$n  ${l4f:+失败:$l4f}"
report "L1 结构校验" "$([ "$l1" = "$n" ] && echo OK || echo FAIL)"
report "L2 schema 校验" "$([ "$l2" = "$n" ] && echo OK || echo FAIL)"
report "L3 parser 校验" "$([ "$l3" = "$n" ] && echo OK || echo FAIL)"
report "L4 runtime 校验" "$([ "$l4" = "$n" ] && echo OK || echo FAIL)"

# --- 阶段 2：铁律检查器（机器可检的硬信号）---
echo
echo ">>> 阶段 2：铁律检查器（check_hard_rules，WARN 不致命，! 致命）"
if node scripts/check_hard_rules.mjs "$OUT" 2>&1 | tee "$EXTRACT/hard.log" | grep -q "HARD_RULES_OK"; then
  report "铁律检查器" "OK"
else
  # HARD_RULES_OK 只在无 ! 致命项时打印；有致命项则检查退出码或 ! 行
  if grep -q "!" "$EXTRACT/hard.log"; then
    report "铁律检查器" "FAIL"
    grep "!" "$EXTRACT/hard.log" | head -20
  else
    report "铁律检查器" "OK"
  fi
fi

# --- 阶段 3：语义回归（L7，积木算出来的值对不对）---
echo
echo ">>> 阶段 3：语义回归（semantic_check，L7）"
if python scripts/semantic_check.py 2>&1 | tee "$EXTRACT/sem.log" | grep -q "SEMANTIC_OK"; then
  report "L7 语义回归" "OK"
else
  report "L7 语义回归" "FAIL"
  tail -20 "$EXTRACT/sem.log"
fi

# --- 阶段 4：全量启动冒烟 + 逐作品行为回归（复用 regress_behavior.sh）---
echo
echo ">>> 阶段 4：启动冒烟 + 行为回归（深网+宽网，约 $([ "$JOBS" -le 1 ] && echo 12 分钟 || echo 并行)）"
if [ "$SKIP_REGRESS" = "1" ]; then
  echo "  （--skip-regress，跳过；如需深网/宽网覆盖请去掉该选项）"
  report "启动冒烟+行为回归" "OK"
else
  if bash scripts/regress_behavior.sh $([ "$JOBS" -gt 1 ] && echo --jobs "$JOBS") 2>&1 | tee "$EXTRACT/regress.log" | grep -q "ALL_BEHAVIOR_OK"; then
    report "启动冒烟+行为回归" "OK"
  else
    report "启动冒烟+行为回归" "FAIL"
    grep -E "FAIL|BOOT_SMOKE_FAIL|启动冒烟: 存在" "$EXTRACT/regress.log" | head -20
  fi
fi

# --- 阶段 5：质量门禁（仅对带规格表的工作）---
echo
echo ">>> 阶段 5：质量门禁（有 *.quality.json 规格表的工作）"
qg_ok=1; qg_list=""
for spec in "$OUT"/*.quality.json examples/*.quality.json; do
  [ -e "$spec" ] || continue
  # 规格表命名 <name>.quality.json -> 对应 <name>.sb3
  name=$(basename "$spec" .quality.json)
  sb3="$OUT/$name.sb3"
  [ -f "$sb3" ] || { echo "  （规格 $name 无对应 $sb3，跳过）"; continue; }
  qg_list="$qg_list $name"
  if python scripts/quality_gate.py --sb3 "$sb3" --spec "$spec" --strict > "$EXTRACT/qg_$name.log" 2>&1 \
     && grep -q "QUALITY_GATE_OK" "$EXTRACT/qg_$name.log"; then
    echo "  ✅ $name 质量门禁通过"
  else
    qg_ok=0
    echo "  ❌ $name 质量门禁未通过"
    tail -8 "$EXTRACT/qg_$name.log"
  fi
done
[ -z "$qg_list" ] && echo "  （无带规格表的工作）"
report "质量门禁" "$([ "$qg_ok" = "1" ] && echo OK || echo FAIL)"
fi  # /--only-advisory

# --- 阶段 6：增量嗅觉（性能预算 / 可访问性 / 抽样试玩）---
# 定位：这是「建议层」，不是「门禁层」。前三层（八层/铁律/门禁）判断对错，
# 这一层判断「有没有更好的写法」。默认 advisory（不影响退出码），
# 用 --strict-advisory 才纳入 FAIL，供 CI 收紧时使用。
echo
echo ">>> 阶段 6：增量嗅觉（性能预算 / 可访问性$( [ "$WITH_PLAYTEST" = "1" ] && echo ' / 抽样 VM 试玩' )，默认 advisory）"
adv_hits=0; adv_bad=0

python scripts/check_perf_budget.py "$OUT" > "$EXTRACT/perf.log" 2>&1 \
  && echo "  ✓ 性能预算：$(grep -oE 'OK [0-9]+ / WARN [0-9]+' "$EXTRACT/perf.log" | tail -1)" \
  || echo "  ！ 性能预算脚本异常（跳过）"
if grep -q "PERF_BUDGET_WARN" "$EXTRACT/perf.log"; then
  adv_hits=$((adv_hits+1))
  grep -E "^  · " "$EXTRACT/perf.log" | head -8 | sed 's/^/     /'
fi

python scripts/check_a11y.py "$OUT" > "$EXTRACT/a11y.log" 2>&1 \
  && echo "  ✓ 可访问性：$(grep -oE 'OK [0-9]+ / WARN [0-9]+' "$EXTRACT/a11y.log" | tail -1)" \
  || echo "  ！ 可访问性脚本异常（跳过）"
if grep -q "A11Y_WARN" "$EXTRACT/a11y.log"; then
  adv_hits=$((adv_hits+1))
  grep -oE "其中致命项 [0-9]+ 个" "$EXTRACT/a11y.log" | tail -1 | sed 's/^/     /'
fi

if [ "$WITH_PLAYTEST" = "1" ]; then
  for n in fruit_basket platformer whack_a_mole; do
    [ -f "$OUT/$n.sb3" ] || continue
    if node scripts/playtest_bot.mjs "$OUT/$n.sb3" 150 > "$EXTRACT/pt_$n.log" 2>&1 \
       && grep -q "PLAYTEST_LIVENESS_OK" "$EXTRACT/pt_$n.log"; then
      echo "  ✓ 试玩 $n：$(grep -oE '运行线程峰值=[0-9]+' "$EXTRACT/pt_$n.log" | tail -1)"
    else
      adv_bad=$((adv_bad+1))
      echo "  ！ 试玩 $n：$(grep -oE 'PLAYTEST_(FAIL|WARN)[^ ]*' "$EXTRACT/pt_$n.log" | tail -1)"
    fi
  done
fi

if [ "$STRICT_ADVISORY" = "1" ]; then
  report "增量嗅觉（strict）" "$([ "$adv_hits" = "0" ] && [ "$adv_bad" = "0" ] && echo OK || echo FAIL)"
else
  [ "$adv_hits" -gt 0 ] && echo "  （advisory：$adv_hits 类建议命中，不阻断；--strict-advisory 可升级为 FAIL）"
  report "增量嗅觉（advisory）" "OK"
fi

# --- 汇总 ---
echo
echo "=================================================="
echo "  验收汇总：通过 $PASS_SECTIONS 项 / 失败 $FAIL_SECTIONS 项"
echo "=================================================="
if [ "$FAIL_SECTIONS" -eq 0 ]; then
  echo "VERIFY_PROJECT_OK"
  exit 0
else
  echo "VERIFY_PROJECT_FAIL"
  exit 1
fi
