#!/bin/bash
# 固定流程，保证可复现：保留设计结构，不做 ABC 重组
MOD=$1
yowasp-yosys -q -l ${MOD}_final.log -p "
read_verilog ${MOD}.v
hierarchy -top ${MOD}
proc
opt_expr
opt_clean
techmap
opt -fast
flatten
stat
ltp -noff
" >/dev/null 2>&1
CELLS=$(sed -n '/=== '"$MOD"' ===/,$p' ${MOD}_final.log | grep -E "^ +[0-9]+ +cells$" | head -1 | awk '{print $1}')
GATES=$(sed -n '/=== '"$MOD"' ===/,$p' ${MOD}_final.log | grep -cE "^ +[0-9]+ +\$_")
PATH=$(grep -oE "^ *[0-9]+:" ${MOD}_final.log | tail -1 | tr -d ' :')
echo "$MOD|cells=$CELLS|path=$PATH"
