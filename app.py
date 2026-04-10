import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.title("シフト最適化（OR-Tools 完全版）")

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

required = {}
cols = st.columns(6)
for i, h in enumerate(hours):
    with cols[i % 6]:
        required[h] = st.number_input(f"{h}時", 0, num_staff, 3, key=f"req_{h}")

# ---------------------------
# 希望入力
# ---------------------------
st.subheader("希望入力")

work_input = {}
break_input = {}

tabs = st.tabs(staff_names)

for i, s in enumerate(staff_names):
    with tabs[i]:
        st.write(f"### {s}")

        c1, c2 = st.columns(2)

        with c1:
            st.write("勤務希望")
            for h in hours:
                work_input[(s, h)] = st.checkbox(f"{h}時勤務", key=f"w_{s}_{h}")

        with c2:
            st.write("休憩希望")
            for h in hours:
                break_input[(s, h)] = st.checkbox(f"{h}時休憩", key=f"b_{s}_{h}")

# ---------------------------
# 実行
# ---------------------------
if st.button("最適化実行"):

    model = cp_model.CpModel()

    # 変数
    x = {(s, h): model.NewBoolVar(f"x_{s}_{h}") for s in staff_names for h in hours}

    # ---------------------------
    # ① 必要人数（絶対）
    # ---------------------------
    for h in hours:
        model.Add(sum(x[(s, h)] for s in staff_names) == required[h])

    # ---------------------------
    # ② 休憩希望は絶対休み
    # ---------------------------
    for s in staff_names:
        for h in hours:
            if break_input[(s, h)]:
                model.Add(x[(s, h)] == 0)

    # ---------------------------
    # ③ ご飯休憩（各スタッフ必須）
    # ---------------------------
    lunch1 = [11, 12, 13]
    lunch2 = [17, 18, 19, 20]

    for s in staff_names:
        # 昼に必ず1時間休憩
        model.Add(sum(1 - x[(s, h)] for h in lunch1) >= 1)

        # 夜に必ず1時間休憩
        model.Add(sum(1 - x[(s, h)] for h in lunch2) >= 1)

    # ---------------------------
    # ④ 単発禁止（超重要）
    # ---------------------------
    for s in staff_names:
        for h in hours:
            if 0 < h < 23:
                model.Add(x[(s, h)] <= x[(s, h-1)] + x[(s, h+1)])

    # ---------------------------
    # ⑤ 勤務希望最大化
    # ---------------------------
    model.Maximize(
        sum(x[(s, h)] for s in staff_names for h in hours if work_input[(s, h)])
    )

    # ---------------------------
    # 解く
    # ---------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    # ---------------------------
    # 結果
    # ---------------------------
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

        schedule = pd.DataFrame(0, index=staff_names, columns=hours)

        for s in staff_names:
            for h in hours:
                schedule.loc[s, h] = int(solver.Value(x[(s, h)]))

        # 勤務時間
        st.subheader("勤務時間")
        st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

        # ---------------------------
        # ビジュアルシフト表
        # ---------------------------
        st.subheader("シフト表")

        display_df = schedule.copy()
        display_df.columns = [f"{h:02d}" for h in hours]
        display_df.index.name = "スタッフ"

        def color_map(val):
            return "background-color: #F6A068" if val == 1 else "background-color: #FFEEDB"

        styled = display_df.style.map(color_map)
        styled = styled.format(lambda x: "")
        styled = styled.set_properties(**{
            "border": "2px solid #999",
            "text-align": "center"
        })

        st.dataframe(styled, use_container_width=True)

    else:
        st.error("❌ 解が見つかりません（条件が厳しすぎます）")
