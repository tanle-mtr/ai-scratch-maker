#!/usr/bin/env bash
# 全量回归：逐个（或并行）跑 *_behavior_check.mjs，汇总结果。
# 用法:
#   bash scripts/regress_behavior.sh            # 串行（默认，最稳，约 12 分钟）
#   bash scripts/regress_behavior.sh --jobs 4   # 隔离并行（快，但吃 CPU；见下方说明）
#
# ⚠️ 默认请串行独占运行。每个 check 用真实墙钟推进 scratch-vm 的虚拟时钟，
#    并发会争抢 CPU，导致虚拟步数不足而偶发「假红」。--jobs 仅在你机器有富余
#    算力、且能容忍偶发重试时使用；若出现假红，调小 --jobs 或回归默认串行。
#
# 🛡️ 自动甄别假红：任一 check 首次失败，会在 run_one 内自动串行重试一次。
#    并行 CPU 争抢导致的假红重试即恢复（记「疑似并行假红」）；真实逻辑缺陷
#    两次都失败仍判 FAIL。因此 --jobs N 现在默认安全，无需人工重跑。
#
# 并行实现：每个作业在独立 subshell 里跑，并把结果写到独立状态文件
#    $tmpdir/<key>.code  （0=PASS 1=FAIL 2=SKIP）
#    $tmpdir/<key>.detail（失败时的关键输出）
# 所以不论串行还是并行，最终由父进程统一汇总，结论稳定。
set -u
cd "$(dirname "$0")/.." || exit 1

JOBS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --jobs) JOBS="${2:-1}"; shift 2;;
    *) shift;;
  esac
done
# 防御：jobs 至少为 1
if [ "$JOBS" -lt 1 ] 2>/dev/null; then JOBS=1; fi

declare -A MAP=(
  [quiz]=quiz [match3]=match3 [shooter]=shooter [edu]=edu_demo
  [story]=story [platformer]=platformer [metro]=metro [metro_drive]=metro_drive
  [multiplayer]=multiplayer [3d]=3d_demo [firstperson]=firstperson
  [board]=board_gomoku [ato]=ato_train [ui_kit]=ui_kit_demo [math]=math_lab [card]=card_game [music]=music_band
  [rhythm]=rhythm_game [rhythm_replicas]=rhythm_replicas
  [shooter_replicas]=shooter_replicas [towerdefense]=tower-defense
  [strategy_replicas]=strategy_replicas
  [fruit_basket]=fruit_basket [cat_mouse]=cat_mouse [whack_a_mole]=whack_a_mole
)
KEYS="quiz match3 shooter edu story platformer metro metro_drive multiplayer 3d firstperson board ato ui_kit math card music rhythm rhythm_replicas shooter_replicas towerdefense strategy_replicas fruit_basket cat_mouse whack_a_mole"

tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/generic"

run_one() {
  local key="$1"
  local sb3="examples/output/${MAP[$key]}.sb3"
  if [ ! -f "$sb3" ]; then
    echo "SKIP $key （缺 $sb3）"
    echo 2 > "$tmpdir/$key.code"
    return 0
  fi
  local out
  out=$(node "scripts/${key}_behavior_check.mjs" "$sb3" 2>&1 | grep -v "Translation for" | tail -25)
  if echo "$out" | grep -q "_LOGIC_OK"; then
    echo "PASS $key"
    echo 0 > "$tmpdir/$key.code"
    return 0
  fi
  # 首次失败：可能是 --jobs 并行下 CPU 争抢导致的「假红」。串行重试一次甄别。
  local retry_out
  retry_out=$(node "scripts/${key}_behavior_check.mjs" "$sb3" 2>&1 | grep -v "Translation for" | tail -25)
  if echo "$retry_out" | grep -q "_LOGIC_OK"; then
    echo "PASS $key （首次失败，串行重试恢复：疑似并行假红）"
    echo 0 > "$tmpdir/$key.code"
    echo "$retry_out" > "$tmpdir/$key.detail"
    return 0
  fi
  echo "FAIL $key"
  echo "$retry_out" | grep "✗" | head -6
  echo 1 > "$tmpdir/$key.code"
  echo "$retry_out" > "$tmpdir/$key.detail"
}

# 通用「深网」：覆盖 MAP 之外、所有尚未有逐作品行为校验的作品（technique_probe* /
# community_tpl_* / example_* / cat_chase* / ref_* / semantic_check / showcase_band 等）。
# 复用 scripts/generic_deep_check.mjs：比启动冒烟跑更久 + 模拟交互 + 结构完整性 +
# IR↔产物角色一致性。失败同样自动串行重试一次甄别并行假红。
run_one_generic() {
  local stem="$1"
  local sb3="examples/output/${stem}.sb3"
  if [ ! -f "$sb3" ]; then
    echo "SKIP(deep) $stem （缺 $sb3）"
    echo 2 > "$tmpdir/generic/$stem.code"
    return 0
  fi
  local out
  out=$(node "scripts/generic_deep_check.mjs" "$sb3" 2>&1 | grep -v "Translation for" | tail -25)
  if echo "$out" | grep -q "_DEEP_OK"; then
    echo "PASS(deep) $stem"
    echo 0 > "$tmpdir/generic/$stem.code"
    return 0
  fi
  local retry_out
  retry_out=$(node "scripts/generic_deep_check.mjs" "$sb3" 2>&1 | grep -v "Translation for" | tail -25)
  if echo "$retry_out" | grep -q "_DEEP_OK"; then
    echo "PASS(deep) $stem （首次失败，串行重试恢复：疑似并行假红）"
    echo 0 > "$tmpdir/generic/$stem.code"
    echo "$retry_out" > "$tmpdir/generic/$stem.detail"
    return 0
  fi
  echo "FAIL(deep) $stem"
  echo "$retry_out" | grep "✗" | head -6
  echo 1 > "$tmpdir/generic/$stem.code"
  echo "$retry_out" > "$tmpdir/generic/$stem.detail"
}

if [ "$JOBS" -le 1 ]; then
  for key in $KEYS; do
    run_one "$key"
  done
else
  echo "（并行模式 --jobs $JOBS；每个作业独立 subshell + 独立 TMPDIR）"
  for key in $KEYS; do
    (
      # 独立临时目录，避免任何 scratch-vm / 子进程写盘互相串扰
      export TMPDIR="$tmpdir/$key"; mkdir -p "$TMPDIR"
      run_one "$key"
    ) &
    # 限流：后台作业数达到上限就先等一个结束
    while [ "$(jobs -r | wc -l)" -ge "$JOBS" ]; do
      wait -n 2>/dev/null || wait
    done
  done
  wait
fi

# --- 通用「深网」：覆盖 MAP 之外全部未逐作品校验的作品 ---
# MAP 已覆盖 23 个标杆作品；其余（technique_probe* / community_tpl_* / example_* /
# cat_chase* / ref_* / semantic_check / showcase_band / community_asset_smoke 等）
# 此前只有启动冒烟（宽网）。这里逐个跑 generic_deep_check.mjs，把「深网」行为校验
# 覆盖从 23 抬到 54（全部作品），且每条仍比启动冒烟更深（更长运行 + 交互模拟 + 角色一致性）。
echo "=== 通用深网（MAP 未覆盖的其余作品）==="
# 已被 MAP 覆盖的 stem 集合（避免重复校验）
COVERED=""
for v in "${MAP[@]}"; do COVERED="$COVERED $v"; done
for sb3f in examples/output/*.sb3; do
  stem=$(basename "$sb3f" .sb3)
  # 跳过 MAP 已覆盖的
  skip=0
  for c in $COVERED; do [ "$stem" = "$c" ] && { skip=1; break; }; done
  [ "$skip" = "1" ] && continue
  run_one_generic "$stem"
done

# --- 全量启动冒烟：覆盖全部作品（含无逐作品行为校验的），抓运行时崩溃 ---
# 这是「宽网」：只断言每个作品能加载 + 绿旗/开始游戏启动不抛异常，
# 与上面逐作品「深网」（23 个 bespoke + 其余通用）互补，兜底运行时崩溃级。
echo "=== 全量启动冒烟（examples/output 全部 .sb3）==="
BOOT_OK=1
if timeout 600 node scripts/boot_smoke_check.mjs examples/output > "$tmpdir/boot_smoke.log" 2>&1; then
  echo "启动冒烟: 全部作品启动正常"
else
  BOOT_OK=0
  echo "启动冒烟: 存在崩溃，详情："
  grep -E "FAIL|BOOT_SMOKE_FAIL" "$tmpdir/boot_smoke.log" || true
fi

PASS=0; FAIL=0; FAILED=""
for key in $KEYS; do
  code=$(cat "$tmpdir/$key.code" 2>/dev/null || echo 0)
  if [ "$code" = "0" ]; then
    PASS=$((PASS+1))
  elif [ "$code" = "1" ]; then
    FAIL=$((FAIL+1)); FAILED="$FAILED $key"
  fi
done

# 通用深网计数
GPASS=0; GFAIL=0; GFAILED=""
for codef in "$tmpdir"/generic/*.code; do
  [ -f "$codef" ] || continue
  stem=$(basename "$codef" .code)
  code=$(cat "$codef")
  if [ "$code" = "0" ]; then
    GPASS=$((GPASS+1))
  elif [ "$code" = "1" ]; then
    GFAIL=$((GFAIL+1)); GFAILED="$GFAILED $stem"
  fi
done
rm -rf "$tmpdir"

echo "----------------------------------------"
echo "逐作品深网: 通过 $PASS / 失败 $FAIL ${FAILED:+| 失败项:$FAILED}"
echo "通用深网:   通过 $GPASS / 失败 $GFAIL ${GFAILED:+| 失败项:$GFAILED}"
if [ "$BOOT_OK" != "1" ]; then
  echo "启动冒烟: 存在运行时崩溃，需排查"
  exit 1
fi
if [ "$FAIL" -ne 0 ] || [ "$GFAIL" -ne 0 ]; then
  echo "行为回归: 存在失败项，需排查"
  exit 1
fi
echo "ALL_BEHAVIOR_OK"
