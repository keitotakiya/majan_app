import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import warnings
import os
from flask import send_from_directory

# 警告非表示（任意）
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ------------------------------
# 色の設定（明るめな麻雀デザイン）
# ------------------------------
BRIGHT_GREEN = "#90EE90"   # ライトグリーン：全体背景（テーブルフェルト風）
IVORY        = "#FFFFF0"   # アイボリー：カードやセクション背景
DARK_GREEN   = "#006400"   # ダークグリーン：テキスト・ボーダー・アクセント

# ==============================
# 1) CSV の読み込み & 前処理
# ==============================
CSV_FILE = "mahjong_scores.csv"  # CSVファイル名
BAPP_FILE = "bapp.csv"           # 罰符ファイル

# CSVデータの読み込み
df = pd.read_csv(CSV_FILE)
df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d")
df.reset_index(inplace=True)
df.rename(columns={"index": "GameID"}, inplace=True)

# wide 形式 → long 形式へ変換
long_df = df.melt(
    id_vars=["GameID", "Date"],
    var_name="Player",
    value_name="Score"
)

# ウマの値（4人想定）
rank2uma = {1: 20, 2: 10, 3: -10, 4: -20}

def compute_uma_and_rank(group):
    group = group.sort_values("Score", ascending=False).reset_index(drop=True)
    group["Rank"] = group.index + 1
    group["UmaScore"] = group.apply(lambda row: row["Score"] + rank2uma[row["Rank"]], axis=1)
    group["UmaScore_x50"] = group["UmaScore"] * 50
    return group

long_df = long_df.groupby(["GameID", "Date"], group_keys=False).apply(compute_uma_and_rank)
min_date = long_df["Date"].min().strftime("%Y-%m-%d")
max_date = long_df["Date"].max().strftime("%Y-%m-%d")

# === 罰符ファイル (bapp.csv) の読み込み & 辞書化 ===
bapp_df = pd.read_csv(BAPP_FILE)
bapp_dict = bapp_df.loc[0].to_dict()

# ==============================
# 2) Dash アプリ設定
# ==============================
# Bootstrapテーマは利用しつつ、個別に配色を上書き
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "麻雀スコアダッシュボード"

# --- 静的画像の配信用ルート ---
# ※ 画像フォルダのパスはご利用環境に合わせて調整してください
IMAGE_FOLDER = r"S:\dash\dash\m\figre"

@app.server.route('/figre/<path:filename>')
def serve_figure(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

# ==============================
# 3) レイアウト
# ==============================
app.layout = dbc.Container(
    fluid=True,
    style={
        "maxWidth": "1200px",
        "margin": "0 auto",
        "backgroundColor": BRIGHT_GREEN,  # 全体背景：ライトグリーン
        "padding": "20px"
    },
    children=[
        # --- ヘッダーセクション ---
        dbc.Card(
            dbc.CardBody([
                html.H1(
                    "麻雀スコアダッシュボード",
                    className="text-center display-4",
                    style={"fontWeight": "bold", "color": DARK_GREEN}
                ),
                html.P(
                    "Taji League 2024-2025 Season",
                    className="text-center lead",
                    style={"color": DARK_GREEN}
                ),
                dbc.Row(
                    dbc.Col(
                        dcc.DatePickerRange(
                            id="date-picker-range",
                            start_date=min_date,
                            end_date=max_date,
                            min_date_allowed=min_date,
                            max_date_allowed=max_date,
                            display_format="YYYY-MM-DD",
                            className="mx-auto"
                        ),
                        width=6
                    ),
                    justify="center",
                    className="mt-3"
                ),
            ]),
            className="mb-4",
            style={
                "backgroundColor": IVORY,      # ヘッダー背景：アイボリー
                "color": DARK_GREEN,
                "border": f"3px solid {DARK_GREEN}",
                "borderRadius": "10px",
                "boxShadow": "0 4px 8px rgba(0,0,0,0.3)",
                "padding": "40px"
            }
        ),
        # --- ランキングセクション ---
        dbc.Card(
            dbc.CardBody(
                html.Div(id="ranking-tables-area")
            ),
            className="mb-4 shadow",
            style={
                "backgroundColor": IVORY,      # セクション背景：アイボリー
                "color": DARK_GREEN,
                "border": f"2px solid {DARK_GREEN}",
                "borderRadius": "8px",
                "padding": "20px"
            }
        ),
        # --- グラフセクション ---
        dbc.Card(
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H4("ゲームIDごとの推移", className="text-center", style={"color": DARK_GREEN}),
                        html.Label("表示指標", className="fw-bold text-center", style={"color": DARK_GREEN}),
                        dcc.Dropdown(
                            id="metric-dropdown",
                            options=[
                                {"label": "生スコア(Score)", "value": "Score"},
                                {"label": "ウマ込みスコア(UmaScore)", "value": "UmaScore"},
                                {"label": "順位(Rank)", "value": "Rank"},
                            ],
                            value="Score",
                            clearable=False,
                        ),
                        dcc.Graph(id="score-graph", style={"height": "300px"}),
                    ], width=6),
                    dbc.Col([
                        html.H4("日付ごとの累積ウマアリスコア", className="text-center", style={"color": DARK_GREEN}),
                        # 左側にドロップダウンなどがあるため、右側のグラフ上部に同等の高さのスペーサーを挿入
                        html.Div(style={"height": "55px"}),
                        dcc.Graph(id="daily-uma-graph", style={"height": "300px"}),
                    ], width=6),
                ])
            ]),
            className="mb-4 shadow",
            style={
                "backgroundColor": IVORY,
                "color": DARK_GREEN,
                "border": f"2px solid {DARK_GREEN}",
                "borderRadius": "8px",
                "padding": "20px"
            }
        ),
        # --- 集計結果セクション ---
        dbc.Card(
            dbc.CardBody([
                html.H3("集計結果", className="text-center", style={"color": DARK_GREEN}),
                html.Div(id="summary-table-area"),
            ]),
            className="mb-4 shadow",
            style={
                "backgroundColor": IVORY,
                "color": DARK_GREEN,
                "border": f"2px solid {DARK_GREEN}",
                "borderRadius": "8px",
                "padding": "20px"
            }
        )
    ]
)

# ==============================
# 4) コールバック: ランキングセクション更新
# ==============================
@app.callback(
    Output("ranking-tables-area", "children"),
    [Input("date-picker-range", "start_date"), Input("date-picker-range", "end_date")]
)
def update_ranking_tables(start_date, end_date):
    mask = (long_df["Date"] >= start_date) & (long_df["Date"] <= end_date)
    dff = long_df.loc[mask].copy()

    # ① 生スコア合計ランキング (Point Ranking)
    point_summary = dff.groupby("Player")["Score"].sum().reset_index()
    point_summary.rename(columns={"Score": "Pt"}, inplace=True)
    point_summary = point_summary.sort_values("Pt", ascending=False).reset_index(drop=True)
    top_pt = point_summary.iloc[0]["Pt"] if not point_summary.empty else 0
    point_summary["PT差"] = top_pt - point_summary["Pt"]
    point_summary["順位"] = point_summary.index + 1
    point_summary = point_summary[["順位", "Player", "Pt", "PT差"]]

    point_ranking_table = dbc.Table(
        [html.Thead(html.Tr([
            html.Th("順位"),
            html.Th("名前"),
            html.Th("Pt"),
            html.Th("PT差")
        ]))] +
        [html.Tbody([
            html.Tr([
                html.Td(row["順位"]),
                html.Td(
                    html.Div([
                        html.Img(
                            src=f"/figre/{row['Player']}.jpg",
                            style={
                                "width": "120px",
                                "height": "120px",
                                "objectFit": "cover",
                                "borderRadius": "50%",
                                "marginRight": "8px"
                            }
                        ),
                        html.Span(row["Player"])
                    ], style={"display": "flex", "alignItems": "center"})
                ),
                html.Td(f"{row['Pt']:.2f}" if isinstance(row['Pt'], float) else str(row['Pt'])),
                html.Td(f"{row['PT差']:.2f}" if isinstance(row['PT差'], float) else str(row['PT差'])),
            ]) for _, row in point_summary.iterrows()
        ])],
        borderless=True,
        hover=True,
        responsive=True,
        className="mb-4",
        style={"color": "black"}
    )

    # ② (a) 最高スコアランキング
    highest_score = dff.groupby("Player")["UmaScore"].max().reset_index()
    highest_score = highest_score.sort_values("UmaScore", ascending=False).reset_index(drop=True)
    highest_score["順位"] = highest_score.index + 1
    highest_score = highest_score[["順位", "Player", "UmaScore"]]
    highest_score_table = dbc.Table(
        [html.Thead(html.Tr([html.Th("順位"), html.Th("名前"), html.Th("点")]))] +
        [html.Tbody([
            html.Tr([
                html.Td(row["順位"]),
                html.Td(row["Player"]),
                html.Td(f"{row['UmaScore']:.2f}" if isinstance(row['UmaScore'], float) else str(row['UmaScore']))
            ]) for _, row in highest_score.iterrows()
        ])],
        borderless=True,
        hover=True,
        responsive=True,
        className="mb-2",
        style={"color": "black"}
    )

    # ② (b) 4着回避率ランキング
    total_games = dff.groupby("Player").size().reset_index(name="games")
    rank4 = dff[dff["Rank"] == 4].groupby("Player").size().reset_index(name="rank4")
    avoidance = pd.merge(total_games, rank4, on="Player", how="left")
    avoidance["rank4"] = avoidance["rank4"].fillna(0)
    avoidance["4着回避率"] = ((avoidance["games"] - avoidance["rank4"]) / avoidance["games"]) * 100
    avoidance = avoidance.sort_values("4着回避率", ascending=False).reset_index(drop=True)
    avoidance["順位"] = avoidance.index + 1
    avoidance = avoidance[["順位", "Player", "4着回避率"]]
    avoidance_table = dbc.Table(
        [html.Thead(html.Tr([html.Th("順位"), html.Th("名前"), html.Th("点")]))] +
        [html.Tbody([
            html.Tr([
                html.Td(row["順位"]),
                html.Td(row["Player"]),
                html.Td(f"{row['4着回避率']:.2f}%")
            ]) for _, row in avoidance.iterrows()
        ])],
        borderless=True,
        hover=True,
        responsive=True,
        className="mb-2",
        style={"color": "black"}
    )

    # ② (c) Yeeeen
    uma50 = dff.groupby("Player")["UmaScore_x50"].sum().reset_index()
    uma50["Adjusted"] = uma50.apply(lambda row: row["UmaScore_x50"] + bapp_dict.get(row["Player"], 0), axis=1)
    uma50 = uma50.sort_values("Adjusted", ascending=False).reset_index(drop=True)
    uma50["順位"] = uma50.index + 1
    uma50 = uma50[["順位", "Player", "Adjusted"]]
    uma50_table = dbc.Table(
        [html.Thead(html.Tr([html.Th("順位"), html.Th("名前"), html.Th("点")]))] +
        [html.Tbody([
            html.Tr([
                html.Td(row["順位"]),
                html.Td(row["Player"]),
                html.Td(f"{row['Adjusted']:.2f}" if isinstance(row['Adjusted'], float) else str(row['Adjusted']))
            ]) for _, row in uma50.iterrows()
        ])],
        borderless=True,
        hover=True,
        responsive=True,
        className="mb-2",
        style={"color": "black"}
    )

    three_rankings_row = dbc.Row([
        dbc.Col([
            html.H5("最高スコアランキング", className="text-center", style={"color": DARK_GREEN}),
            highest_score_table
        ], width=4),
        dbc.Col([
            html.H5("4着回避率ランキング", className="text-center", style={"color": DARK_GREEN}),
            avoidance_table
        ], width=4),
        dbc.Col([
            html.H5("Yeeeen", className="text-center", style={"color": DARK_GREEN}),
            uma50_table
        ], width=4)
    ], className="mb-4")

    ranking_section = html.Div([
        html.H2(
            "総合ポイントランキング",
            className="text-center",
            style={"fontSize": "4rem", "fontWeight": "bold", "padding": "20px 0", "color": DARK_GREEN}
        ),
        html.Div(
            point_ranking_table,
            style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px", "fontSize": "1.5rem"}
        ),
        three_rankings_row
    ], style={"padding": "40px 0"})
    
    return ranking_section

# ==============================
# 5) コールバック: グラフ①（GameID×指標）
# ==============================
@app.callback(
    Output("score-graph", "figure"),
    [Input("date-picker-range", "start_date"),
     Input("date-picker-range", "end_date"),
     Input("metric-dropdown", "value")]
)
def update_graph(start_date, end_date, selected_metric):
    mask = (long_df["Date"] >= start_date) & (long_df["Date"] <= end_date)
    dff = long_df.loc[mask].copy()
    fig = px.line(
        dff,
        x="GameID",
        y=selected_metric,
        color="Player",
        markers=True,
        title=f"{selected_metric} の推移 (GameID順)"
    )
    fig.update_layout(
        legend_title_text="プレイヤー",
        plot_bgcolor=IVORY,
        paper_bgcolor=IVORY,
        margin=dict(l=50, r=30, t=50, b=50),
        font_color=DARK_GREEN
    )
    return fig

# ==============================
# 6) コールバック: グラフ②（累積ウマアリスコア）
# ==============================
@app.callback(
    Output("daily-uma-graph", "figure"),
    [Input("date-picker-range", "start_date"),
     Input("date-picker-range", "end_date")]
)
def update_daily_uma_graph(start_date, end_date):
    mask = (long_df["Date"] >= start_date) & (long_df["Date"] <= end_date)
    dff = long_df.loc[mask].copy()
    daily_sum_df = dff.groupby(["Date", "Player"], as_index=False)["UmaScore"].sum()
    daily_sum_df = daily_sum_df.sort_values("Date")
    daily_sum_df["UmaScore_cumsum"] = daily_sum_df.groupby("Player")["UmaScore"].cumsum()
    fig = px.line(
        daily_sum_df,
        x="Date",
        y="UmaScore_cumsum",
        color="Player",
        markers=True,
        title="日付ごとの累積ウマアリスコア"
    )
    fig.update_layout(
        legend_title_text="プレイヤー",
        plot_bgcolor=IVORY,
        paper_bgcolor=IVORY,
        margin=dict(l=50, r=30, t=50, b=50),
        font_color=DARK_GREEN
    )
    return fig

# ==============================
# 7) コールバック: 集計結果テーブル
# ==============================
@app.callback(
    Output("summary-table-area", "children"),
    [Input("date-picker-range", "start_date"),
     Input("date-picker-range", "end_date")]
)
def update_summary_table(start_date, end_date):
    mask = (long_df["Date"] >= start_date) & (long_df["Date"] <= end_date)
    dff = long_df.loc[mask].copy()
    summary = dff.groupby("Player").agg(
        生スコア合計=("Score", "sum"),
        ウマ込み合計=("UmaScore", "sum"),
        平均順位=("Rank", "mean"),
        Yeeeen=("UmaScore_x50", "sum"),
        最高スコア=("UmaScore", "max"),
        最低スコア=("UmaScore", "min"),
        平均スコア=("UmaScore", "mean"),
    ).reset_index()
    # 罰符補正
    summary["Yeeeen"] = summary.apply(
        lambda row: row["Yeeeen"] + bapp_dict.get(row["Player"], 0),
        axis=1
    )
    # 転置して各指標を行に
    summary_pivot = summary.set_index("Player").T

    # 各順位率の算出
    rank_ct = pd.crosstab(dff["Player"], dff["Rank"])
    rank_rate = (rank_ct.div(rank_ct.sum(axis=1), axis=0) * 100).round(2)
    rank_rate.columns = [f"{col}位率" for col in rank_rate.columns]
    rank_rate_T = rank_rate.transpose()

    # summary_pivot と 各順位率を結合
    combined_pivot = pd.concat([summary_pivot, rank_rate_T], axis=0)

    # 希望の順序：
    # ① 最高スコア, ② 最低スコア, ③ 平均スコア,
    # ④ 各順位率（1位率～4位率を昇順に）,
    # ⑤ 平均順位, ⑥ 生スコア合計, ⑦ ウマ込み合計, ⑧ Yeeeen
    sorted_rank_rate = sorted(
        [idx for idx in combined_pivot.index if "位率" in idx],
        key=lambda x: int(x.replace("位率", ""))
    )
    desired_order = ["最高スコア", "最低スコア", "平均スコア"] + sorted_rank_rate + ["平均順位", "生スコア合計", "ウマ込み合計", "Yeeeen"]

    # reindex（存在しない指標はNaNになりますが、表示時は空文字などに変換可能です）
    combined_pivot = combined_pivot.reindex(desired_order)

    # テーブル作成
    table_header = [
        html.Thead(html.Tr(
            [html.Th("項目 / プレイヤー")] +
            [html.Th(player) for player in combined_pivot.columns]
        ))
    ]
    table_body = []
    for row_name in combined_pivot.index:
        row_cells = [html.Td(row_name)]
        for player in combined_pivot.columns:
            val = combined_pivot.loc[row_name, player]
            cell_str = f"{val:.2f}" if isinstance(val, float) else (str(val) if pd.notnull(val) else "")
            row_cells.append(html.Td(cell_str))
        table_body.append(html.Tr(row_cells))
    table_body = [html.Tbody(table_body)]
    table = dbc.Table(
        table_header + table_body,
        borderless=True,
        hover=True,
        responsive=True,
        style={"color": "black"}
    )
    return table

# ==============================
# 8) アプリ実行
# ==============================
if __name__ == "__main__":
    # app.run_server(debug=True)
    port = int(os.environ.get("PORT", 8050))  # Render などのクラウドサービスでは PORT 環境変数が設定される
    app.run_server(host='0.0.0.0', port=port, debug=False)
