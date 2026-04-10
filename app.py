import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.title("シフト最適化（OR-Tools版）")

# ---------------------------
# 基本設定
# ---------------------------
num_staff = st.number_input("スタッフ人数", 1, 20, 6)
staff_names = [f"スタッフ{i+1}" for i in range(num_staff)]
hours = list(range(24))

# ---------------------------
# 必要人数
# ---------------------------
st.subheader("必要人数")
required = {h: st.number_input(f"{h}時", 0, num_staff, 3, key=f"req_{h}") for h in hours}

# ---------------------------
# 希望入力
# ---------------------------
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

st.subheader("希望入力")

for s in staff_names:
    st.write(f"### {s}")
    c1, c2 = st.columns(2)

    with c1:
        st.write("勤務希望")
        for h in hours:
            work_df.loc[s, h] = st.checkbox(f"{h}時勤務", key=f"w_{s}_{h}")

    with c2:
        st.write("休憩希望")
        for h in hours:
            break_df.loc[s, h] = st.checkbox(f"{h}時休憩", key=f"b_{s}_{h}")

# ---------------------------
# 実行
# ---------------------------
if st.button("最適化実行"):

    model = cp_model.CpModel()

    # x[s,h] = 1なら勤務
    x = {}
    for s in staff_names:
        for h in hours:
            x[(s, h)] = model.NewBoolVar(f"x_{s}_{h}")

    # ---------------------------
    # ① 必要人数制約（絶対）
    # ---------------------------
    for h in hours:
        model.Add(sum(x[(s, h)] for s in staff_names) == required[h])

    # ---------------------------
    # ② 休憩希望は絶対OFF
    # ---------------------------
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                model.Add(x[(s, h)] == 0)

    # ---------------------------
    # ③ ご飯休憩（強制OFF + 分散）
    # ---------------------------
    lunch1 = [11, 12, 13]
    lunch2 = [17, 18, 19, 20]

    for group in [lunch1, lunch2]:
        # 各時間最低1人は必ず休憩（=勤務人数制限）
        for h in group:
            model.Add(sum(x[(s, h)] for s in staff_names) <= num_staff - 1)

    # ---------------------------
    # ④ 単発禁止（超重要）
    # x[s,h]=1なら前後どちらかも1である必要
    # ---------------------------
    for s in staff_names:
        for h in hours:
            if 0 < h < 23:
                model.Add(x[(s, h)] <= x[(s, h-1)] + x[(s, h+1)])

    # ---------------------------
    # ⑤ 勤務希望（できるだけ反映）
    # ---------------------------
    score_terms = []
    for s in staff_names:
        for h in hours:
            if work_df.loc[s, h] == 1:
                score_terms.append(x[(s, h)])

    model.Maximize(sum(score_terms))

    # ---------------------------
    # 解く
    # ---------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)

    # ---------------------------
    # 結果表示
    # ---------------------------
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

        schedule = pd.DataFrame(0, index=staff_names, columns=hours)

        for s in staff_names:
            for h in hours:
                schedule.loc[s, h] = int(solver.Value(x[(s, h)]))

        st.subheader("シフト表")

        st.dataframe(schedule)

        st.subheader("勤務時間")
        st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    else:
        st.error("解が見つかりません（制約が厳しすぎます）") 
