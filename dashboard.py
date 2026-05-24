import streamlit as st
import json
import glob
from datetime import datetime
from collections import defaultdict, Counter
import pandas as pd
import re

st.set_page_config(page_title="博主起号分析", page_icon="📊", layout="wide")

# ── 赛道 & 博主定义 ────────────────────────────────────────────
NICHES = {
    "做饭": [
        "5940f32182ec3947cc227ebe",  # 日食记
        "5aabcb2d11be105d1a3c83b0",  # 鱼鱼食记
        "6300e2d8000000001501a130",  # 桃小姐美食记
        "64b3b15c000000001c02b369",  # 开心一点啦
        "5fc67ee70000000001002f7a",  # 小辰吾妮
    ]
}

CREATOR_NAMES = {
    "5940f32182ec3947cc227ebe": "日食记",
    "5fc67ee70000000001002f7a": "小辰吾妮",
    "64b3b15c000000001c02b369": "开心一点啦",
    "6300e2d8000000001501a130": "桃小姐美食记",
    "5aabcb2d11be105d1a3c83b0": "鱼鱼食记",
}

# 手写的起号策略总结（基于数据分析）
CREATOR_INSIGHTS = {
    "5940f32182ec3947cc227ebe": {
        "strategy": "成熟账号迁移型",
        "summary": "日食记是在小红书拥有历史积累的大号，数据中最早记录为 2025-01，起号期互动量已接近均值，说明带着老粉丝起步。内容方向稳定：家常菜+快手做法+下饭硬菜，标题强调时间短、食材少、结果感。",
        "title_formula": "动词+食材/场景+结果感受",
        "examples": ["5分钟学会这个做法，鲜掉眉毛", "方便面多做一步，油香入魂", "只需3种食材，解锁下饭硬菜"],
        "key_pattern": "标题强调「简单」「快手」「下饭」，结果描述感官化（香、鲜、软烂入味）",
        "start_difficulty": "难（需要已有受众或背景资源）",
    },
    "5aabcb2d11be105d1a3c83b0": {
        "strategy": "情绪标题 + 爆文起号型",
        "summary": "鱼鱼食记是最值得新人学习的起号案例。账号起步于 2024-12，起号期前两篇就各有10万+和30万+互动，爆文率极高。核心秘诀：标题情绪浓度极高，用叠词+感叹放大食物诱惑力，配合简单家常菜形成低门槛高预期的内容组合。",
        "title_formula": "这个[菜名]太太太[感受]了啊！[行动号召]",
        "examples": ["这一碗太太太下饭了啊 好吃快去做", "这一碗好吃哭了 好吃到停不下来 快去试试", "这个菜太太太好吃了啊！"],
        "key_pattern": "叠词放大情绪（太太太、嘎嘎香），句尾加行动号召（快去做/快去试试），内容本身是简单家常菜",
        "start_difficulty": "低（标题公式清晰，内容门槛不高）",
    },
    "6300e2d8000000001501a130": {
        "strategy": "单爆文带号型",
        "summary": "桃小姐美食记的起号路径非常典型：发了近10篇几百互动的普通帖后，靠一篇「9款家常炒菜大全」爆文（互动28万+）完成起号。爆文是合集形式，信息密度高，收藏动力强。账号整体互动均值不高（约5500），头部与腰部帖差距悬殊，是典型的靠单篇大爆拉动的结构。",
        "title_formula": "N款[菜系/场景]合集🔥[特点]❗️[结果]",
        "examples": ["9款家常炒菜大全🔥超下饭❗️一周不重样", "12款不重样下饭菜合集，谁吃谁爱！", "六款汤面做法🔥做法简单一锅不重样"],
        "key_pattern": "合集型内容收藏率高；标题用数字+合集触发「保存」心理；早期帖子标题高度模板化（❗️/🔥/巨好吃❗️）",
        "start_difficulty": "中（需要耐心持续发内容等待爆文）",
    },
    "64b3b15c000000001c02b369": {
        "strategy": "长期蛰伏 + 找准定位爆发型",
        "summary": "开心一点啦的起号最慢，从 2023-09 发帖到 2025-02 才出现第一篇爆文，蛰伏期超过一年。早期内容杂乱（北京咖啡、留学碎片），直到确立「留学生生活+做饭」的反差内容方向后迅速爆发。核心启示：内容定位不清时互动很难起来，找到独特角度（留学生的中国胃）才是关键。",
        "title_formula": "[身份标签]的[反差/情绪]场景",
        "examples": ["留子下厨🍝如何把一锅面做成异国恋 真香", "90块的青旅配500的早饭是什么体验", "纽约富人区的剩菜盲盒竟然这么甜美"],
        "key_pattern": "「留学生」身份标签制造反差感；做饭内容承载情感（思乡、异国生活对比）；标题有强画面感和好奇心触发",
        "start_difficulty": "高（需要找到独特身份/角度，周期长）",
    },
    "5fc67ee70000000001002f7a": {
        "strategy": "情侣内容 + 情感共鸣型",
        "summary": "小辰吾妮实际上不是做饭博主，而是情侣/感情方向的视频博主。起号于 2024-05，内容以情侣日常、感情心理学为主。爆文方向：情感共鸣（毕业/分离）、心理学干货、情侣互动视频。如果你做饭赛道，这个账号的内容方向参考意义有限，但其情绪共鸣标题思路可借鉴。",
        "title_formula": "情绪词/情境 + 反应/共鸣",
        "examples": ["人生的答卷成绩不是用分数评判", "本来就烦", "出门在外牵手的重要性…"],
        "key_pattern": "标题极简，强情绪触发；不解释内容，用悬念/情绪勾人点进去",
        "start_difficulty": "中（依赖情感共鸣，受众明确）",
    },
}

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

STOP_WORDS = {
    "了", "的", "是", "在", "我", "你", "他", "她", "它", "们",
    "这", "那", "有", "和", "与", "也", "都", "就", "不", "一",
    "什么", "怎么", "可以", "没有", "真的", "真是", "还是", "但是",
    "然后", "所以", "因为", "如果", "虽然", "但", "呢", "啊", "哦",
    "嗯", "哈", "吗", "吧", "呀", "哇", "哎", "哟", "喔", "哦",
}

# ── 工具函数 ───────────────────────────────────────────────────
def parse_time(ts):
    if not ts:
        return None
    try:
        t = int(ts)
        if t > 1e12:
            t /= 1000
        return datetime.fromtimestamp(t)
    except (ValueError, TypeError, OSError):
        pass
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(str(ts)[:19], fmt)
        except Exception:
            pass
    return None

def parse_num(val):
    if not val:
        return 0
    s = str(val).replace("+", "").replace(",", "").strip()
    if "万" in s:
        return int(float(s.replace("万", "")) * 10000)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0

def calc_eng(note):
    return (
        parse_num(note.get("liked_count"))
        + parse_num(note.get("collected_count")) * 2
        + parse_num(note.get("comment_count"))
    )

def extract_words(title):
    """简单中文分词：按字符切分，提取2-6字短语"""
    if not title:
        return []
    # 去掉 emoji、标点、话题标签
    clean = re.sub(r"[#\[\]【】「」『』《》\(\)（）!！?？。，、：；…~～·\s]", " ", title)
    clean = re.sub(r"[^\u4e00-\u9fff\u3040-\u30ffa-zA-Z0-9 ]", "", clean)
    words = []
    for part in clean.split():
        if not part:
            continue
        # 提取2-4字的中文片段
        for i in range(len(part)):
            for length in (2, 3, 4):
                w = part[i:i+length]
                if len(w) == length and all('\u4e00' <= c <= '\u9fff' for c in w):
                    if w not in STOP_WORDS:
                        words.append(w)
    return words

def extract_creator_id(text):
    """从URL或直接输入提取博主ID"""
    m = re.search(r'/user/profile/([a-z0-9]+)', text.strip())
    if m:
        return m.group(1)
    t = text.strip()
    if re.match(r'^[a-z0-9]{20,}$', t):
        return t
    return None

def extract_tags(note):
    """从笔记数据中提取话题标签"""
    tags = []
    tag_list = note.get("tag_list")
    if isinstance(tag_list, str) and tag_list:
        # 爬虫存储为逗号分隔字符串：e.g. "food,小零食,模特日常"
        tags.extend(t.strip() for t in tag_list.split(",") if t.strip())
    elif isinstance(tag_list, list):
        for item in tag_list:
            if isinstance(item, dict):
                name = item.get("name") or item.get("text") or ""
                if name:
                    tags.append(name)
            elif isinstance(item, str) and item:
                tags.append(item)
    # 兜底：从 desc 正文抽取 #话题
    desc = note.get("desc") or ""
    tags += re.findall(r'#([^\s#\[\]]+)', desc)
    return list(set(tags))

@st.cache_data
def load_creator_data(creator_id):
    """加载任意博主的数据（按ID匹配）"""
    notes, seen = [], set()
    for fp in sorted(glob.glob("data/**/*.json", recursive=True)):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            for item in (data if isinstance(data, list) else [data]):
                if item.get("user_id") == creator_id:
                    nid = item.get("note_id", "")
                    if nid not in seen:
                        seen.add(nid)
                        notes.append(item)
        except Exception:
            pass
    notes.sort(key=lambda n: parse_time(n.get("time")) or datetime.min)
    return notes

@st.cache_data
def load_all_creators():
    """扫描所有数据文件，返回 {creator_id: nickname} 字典"""
    creators = {}
    seen = set()
    for fp in sorted(glob.glob("data/**/*.json", recursive=True)):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            for item in (data if isinstance(data, list) else [data]):
                uid = item.get("user_id", "")
                nid = item.get("note_id", "")
                if uid and nid not in seen:
                    seen.add(nid)
                    if uid not in creators:
                        creators[uid] = item.get("nickname") or item.get("user_name") or uid[:8]
        except Exception:
            pass
    return creators

@st.cache_data
def load_notes():
    all_ids = {cid for ids in NICHES.values() for cid in ids}
    notes_by_creator = defaultdict(list)
    seen = set()
    for fp in sorted(glob.glob("data/**/*.json", recursive=True)):
        if "creator" not in fp:
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            for item in (data if isinstance(data, list) else [data]):
                uid = item.get("user_id", "")
                nid = item.get("note_id", "")
                if uid in all_ids and nid not in seen:
                    seen.add(nid)
                    notes_by_creator[uid].append(item)
        except Exception:
            pass
    for uid in notes_by_creator:
        notes_by_creator[uid].sort(
            key=lambda n: parse_time(n.get("time")) or datetime.min
        )
    return dict(notes_by_creator)

def to_df(notes):
    rows = []
    for i, n in enumerate(notes, 1):
        t = parse_time(n.get("time"))
        eng = calc_eng(n)
        rows.append({
            "序号": i,
            "日期": t.strftime("%Y-%m-%d") if t else "未知",
            "标题": (n.get("title") or n.get("desc") or "")[:50],
            "点赞": parse_num(n.get("liked_count")),
            "收藏": parse_num(n.get("collected_count")),
            "评论": parse_num(n.get("comment_count")),
            "互动总量": eng,
            "_time": t or datetime.min,
            "_url": n.get("note_url", ""),
            "_raw_title": n.get("title") or n.get("desc") or "",
        })
    return pd.DataFrame(rows)

# ── 加载数据 ───────────────────────────────────────────────────
all_notes = load_notes()

# ── 侧边栏 ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("博主起号分析")
    st.caption("互动总量 = 点赞 + 收藏×2 + 评论")
    st.markdown("---")
    page = st.radio("page", ["📊 赛道概览", "🎯 对标博主分析"], label_visibility="collapsed")
    st.markdown("---")
    if page == "📊 赛道概览":
        selected_niche = st.selectbox("赛道", list(NICHES.keys()))
        creator_ids = [cid for cid in NICHES[selected_niche] if cid in all_notes]
        options = ["全部博主"] + [CREATOR_NAMES[cid] for cid in creator_ids]
        selected_name = st.selectbox("博主", options)
        st.markdown("---")
    elif page == "🎯 对标博主分析":
        all_creators = load_all_creators()
        creator_name_to_id = {name: uid for uid, name in all_creators.items()}
        selected_target_name = st.selectbox("对标博主", list(creator_name_to_id.keys()))
        selected_target_id = creator_name_to_id[selected_target_name]
        topic_input = st.text_input("你要发的内容主题", placeholder="例如：虾肉馄饨")
        st.markdown("---")
    st.caption("数据来自小红书，仅供学习参考")

# ── 对标博主分析页 ─────────────────────────────────────────────
if page == "🎯 对标博主分析":
    st.title(f"🎯 对标博主分析")

    creator_id = selected_target_id
    topic_input = topic_input  # from sidebar
    target_notes = load_creator_data(creator_id)

    if not target_notes:
        st.warning("暂无数据，请先爬取该博主")
        st.stop()

    # ── 计算所有统计量 ──────────────────────────────────────────
    t_engs = [calc_eng(n) for n in target_notes]
    t_avg = int(sum(t_engs) / len(t_engs)) if t_engs else 0
    t_top10 = sorted(t_engs, reverse=True)[max(0, len(t_engs) // 10)] if len(t_engs) >= 10 else 0
    t_viral = [n for n, e in zip(target_notes, t_engs) if e >= t_top10]
    t_normal = [n for n, e in zip(target_notes, t_engs) if e < t_top10]
    t_name = (
        target_notes[0].get("nickname") or target_notes[0].get("user_name") or
        target_notes[0].get("author") or creator_id[:8]
    )
    t_first = parse_time(target_notes[0].get("time"))

    # 标题词频
    t_viral_wc = Counter()
    for n in t_viral:
        t_viral_wc.update(extract_words(n.get("title") or n.get("desc") or ""))

    # 话题标签
    t_all_tags = Counter()
    for n in (t_viral if t_viral else target_notes):
        t_all_tags.update(extract_tags(n))

    # 标题长度
    t_viral_lens  = [len(n.get("title") or n.get("desc") or "") for n in t_viral]
    t_normal_lens = [len(n.get("title") or n.get("desc") or "") for n in t_normal]

    # 时间数据
    t_timed = [(parse_time(n.get("time")), calc_eng(n)) for n in target_notes]
    t_timed = [(t, e) for t, e in t_timed if t is not None]
    t_viral_times = [t for t, e in t_timed if e >= t_top10]
    t_all_sorted  = sorted(t for t, e in t_timed)
    t_avg_intv, t_ppw = None, None
    if len(t_all_sorted) >= 2:
        t_intervals = [(t_all_sorted[i+1] - t_all_sorted[i]).days for i in range(len(t_all_sorted)-1)]
        t_avg_intv = sum(t_intervals) / len(t_intervals)
        t_ppw = round(7 / t_avg_intv, 1) if t_avg_intv > 0 else 0
    t_best_wd_names = []
    if t_viral_times:
        t_best_wd_names = [WEEKDAY_NAMES[i] for i, _ in Counter(t.weekday() for t in t_viral_times).most_common(2)]
    t_hour_eng = defaultdict(list)
    for t, e in t_timed:
        t_hour_eng[t.hour].append(e)
    t_hour_avg = {h: int(sum(v)/len(v)) for h, v in t_hour_eng.items()}
    t_hour_cnt = {h: len(v) for h, v in t_hour_eng.items()}

    # 内容类型
    t_video_notes = [n for n in target_notes if n.get("note_type") == "video"]
    t_img_notes   = [n for n in target_notes if n.get("note_type") != "video"]
    t_video_avg = int(sum(calc_eng(n) for n in t_video_notes) / len(t_video_notes)) if t_video_notes else 0
    t_img_avg   = int(sum(calc_eng(n) for n in t_img_notes)   / len(t_img_notes))   if t_img_notes   else 0
    t_v_desc_lens = [len(n.get("desc") or "") for n in t_viral]
    t_n_desc_lens = [len(n.get("desc") or "") for n in t_normal]

    # 推广信号
    t_sorted_engs = sorted(t_engs, reverse=True)
    t_top1_ratio = t_sorted_engs[0] / (t_sorted_engs[1] if len(t_sorted_engs) > 1 else 1) if len(t_sorted_engs) >= 2 else 1

    # ── 概览 ───────────────────────────────────────────────────
    st.subheader(f"📊 {t_name} 数据概览")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("笔记总数", len(target_notes))
    mc2.metric("平均互动", f"{t_avg:,}")
    mc3.metric("爆文门槛", f"{t_top10:,}")
    mc4.metric("爆文数量", f"{len(t_viral)} 篇")
    if t_first:
        st.caption(f"最早记录：{t_first.strftime('%Y-%m')}")
    st.markdown("---")

    ta, tb, tc, td = st.tabs(["📌 标题 & 标签", "⏰ 发布节奏", "📝 内容形式", "🎯 我的策略"])

    # ── Tab A ──────────────────────────────────────────────────
    with ta:
        col_w, col_t = st.columns(2)
        with col_w:
            st.markdown("**爆文标题高频词 (Top 20)**")
            if t_viral_wc:
                st.dataframe(
                    pd.DataFrame(t_viral_wc.most_common(20), columns=["词", "频次"]),
                    hide_index=True, use_container_width=True,
                )
            else:
                st.caption("暂无足够爆文数据")
        with col_t:
            label = "爆文" if t_viral else "全量"
            st.markdown(f"**{label}高频话题标签 (Top 20)**")
            if t_all_tags:
                st.dataframe(
                    pd.DataFrame(t_all_tags.most_common(20), columns=["标签", "次数"]),
                    hide_index=True, use_container_width=True,
                )
            else:
                st.caption("暂无标签（desc字段无#话题）")
        st.markdown("---")
        st.markdown("**标题长度对比**")
        if t_viral_lens:
            tl1, tl2 = st.columns(2)
            tl1.metric("爆文平均标题长度", f"{sum(t_viral_lens)//len(t_viral_lens)} 字")
            if t_normal_lens:
                tl2.metric("普通帖平均标题长度", f"{sum(t_normal_lens)//len(t_normal_lens)} 字")

    # ── Tab B ──────────────────────────────────────────────────
    with tb:
        if t_timed:
            t_viral_wd = Counter(t.weekday() for t in t_viral_times)
            st.markdown("**爆文发布日分布**")
            st.bar_chart(pd.DataFrame(
                {"爆文次数": [t_viral_wd.get(i, 0) for i in range(7)]},
                index=WEEKDAY_NAMES,
            ))
            if t_avg_intv is not None:
                bf1, bf2 = st.columns(2)
                bf1.metric("平均发帖间隔", f"{t_avg_intv:.1f} 天")
                bf2.metric("约每周发帖", f"{t_ppw} 篇")
            t_hour_df = pd.DataFrame({
                "发布篇数": [t_hour_cnt.get(h, 0) for h in range(24)],
                "平均互动": [t_hour_avg.get(h, 0) for h in range(24)],
            }, index=[f"{h}时" for h in range(24)])
            bh1, bh2 = st.columns(2)
            with bh1:
                st.markdown("**发布时段分布**")
                st.bar_chart(t_hour_df[["发布篇数"]])
            with bh2:
                st.markdown("**时段平均互动**")
                st.bar_chart(t_hour_df[["平均互动"]])

    # ── Tab C ──────────────────────────────────────────────────
    with tc:
        t_type_eng = defaultdict(list)
        for n, e in zip(target_notes, t_engs):
            t_type_eng[n.get("note_type", "normal")].append(e)
        ct1, ct2 = st.columns(2)
        with ct1:
            t_type_df = pd.DataFrame({"数量": Counter(n.get("note_type", "normal") for n in target_notes)})
            t_type_df.index = t_type_df.index.map(lambda x: "视频" if x == "video" else "图文")
            st.markdown("**笔记类型数量**")
            st.bar_chart(t_type_df)
        with ct2:
            t_type_avg_eng = {k: int(sum(v)/len(v)) for k, v in t_type_eng.items() if v}
            t_avg_eng_df = pd.DataFrame({"平均互动": t_type_avg_eng})
            t_avg_eng_df.index = t_avg_eng_df.index.map(lambda x: "视频" if x == "video" else "图文")
            st.markdown("**类型平均互动**")
            st.bar_chart(t_avg_eng_df)
        st.markdown("---")
        st.markdown("**正文长度（爆文 vs 普通）**")
        if t_v_desc_lens:
            dl1, dl2 = st.columns(2)
            dl1.metric("爆文平均正文", f"{sum(t_v_desc_lens)//len(t_v_desc_lens)} 字")
            if t_n_desc_lens:
                dl2.metric("普通帖平均正文", f"{sum(t_n_desc_lens)//len(t_n_desc_lens)} 字")
        st.markdown("---")
        st.markdown("**高收藏率内容 Top 8**（收藏/点赞比高 = 干货/合集属性强）")
        df_tc = to_df(target_notes)
        df_tc = df_tc[df_tc["点赞"] > 0].copy()
        df_tc["收藏点赞比"] = (df_tc["收藏"] / df_tc["点赞"]).round(2)
        st.dataframe(
            df_tc.nlargest(8, "收藏点赞比")[["日期", "标题", "点赞", "收藏", "收藏点赞比"]],
            hide_index=True, use_container_width=True,
        )

    # ── Tab D: 我的策略 ────────────────────────────────────────
    with td:
        topic = topic_input.strip() if topic_input else "你的内容"
        st.markdown(f"### 针对「{topic}」的完整发布策略")
        st.caption(f"基于 {t_name} 的 {len(target_notes)} 篇笔记数据分析")

        st.markdown("#### ① 标题怎么写")
        if t_viral_wc:
            top5_words = [w for w, _ in t_viral_wc.most_common(5)]
            st.success(
                f"该博主爆文标题高频词：**{'、'.join(top5_words)}**\n\n"
                f"**套用到你的内容：**\n"
                f"- 「这个{topic}太太太好吃了啊！快去做」\n"
                f"- 「{topic}这样做，香哭了！一口一个停不下来」\n"
                f"- 「学了{topic}这个做法，再也不想点外卖了」\n\n"
                f"**核心公式：叠词放大情绪（太太太/嘎嘎香）+ 结果描述 + 行动号召**"
            )
        else:
            st.info(f"建议参考套路：「这个{topic}太好吃了！」+ 情绪叠词 + 行动号召")

        st.markdown("#### ② 发哪些话题标签")
        if t_all_tags:
            top10_tags = [f"#{t}" for t, _ in t_all_tags.most_common(10)]
            st.info(
                f"直接复用该博主爆文高频标签：\n\n"
                f"{'  '.join(top10_tags)}\n\n"
                f"💡 额外加上精准标签：**#{topic}** 及相关细分标签（如 #馄饨 #家常做法 #下饭菜）"
            )

        st.markdown("#### ③ 发布频率")
        if t_avg_intv is not None:
            st.warning(
                f"该博主平均每 **{t_avg_intv:.1f} 天** 发一篇（约每周 {t_ppw} 篇）\n\n"
                f"**新号建议：** 每周至少 **{max(2, int(round(t_ppw)))} 篇**，"
                f"前3个月不能断更——平台需要持续信号才会给你贴标签、建立推流模型。"
            )
        else:
            st.warning("建议每周2-3篇，持续3个月再看数据。")

        st.markdown("#### ④ 图文 vs 视频")
        if t_video_avg >= t_img_avg and t_video_notes:
            st.success(
                f"该博主视频平均互动（{t_video_avg:,}）>= 图文（{t_img_avg:,}）\n\n"
                f"**建议做视频。** {topic} 适合展示烹饪过程，1-3分钟最佳，"
                f"剪辑节奏快，背景用欢快轻音乐，加字幕。"
            )
        elif t_img_notes:
            st.success(
                f"该博主图文平均互动（{t_img_avg:,}）{'>' if t_img_avg > t_video_avg else '>='} 视频（{t_video_avg:,}）\n\n"
                f"**图文也很有效。** 做4-9张图，第一张是封面，后面是步骤图+成品图。"
            )
        else:
            st.info("建议优先做视频，更容易被推流。")

        st.markdown("#### ⑤ 什么时候发")
        if t_best_wd_names:
            st.info(
                f"该博主爆文集中在 **{'、'.join(t_best_wd_names)}** 发布\n\n"
                f"**通用建议：晚18-21时**（晚饭后高峰）或 **午12时**（午休刷机峰值）"
            )
        else:
            st.info("**建议时段：晚18-21时**（晚饭后高峰）或 **午12时**（午休刷机峰值）")

        st.markdown("#### ⑥ 封面怎么做")
        st.info(
            f"**参考该博主 Top 爆文封面风格：**\n"
            f"- 食物/成品大近景，占画面 60-80%\n"
            f"- 叠加大字标题（例如「太好吃了」「{topic}的正确打开方式」）\n"
            f"- 色调偏暖（橙/黄/红），刺激食欲\n"
            f"- 视频封面：用最诱人的那帧成品镜头，不要用食材备料图"
        )

        st.markdown("#### ⑦ 要不要买薯条/推广")
        if t_top1_ratio > 5:
            st.warning(
                f"该博主最高单篇互动是第二名的 **{t_top1_ratio:.0f}x**，可能有推广加持。\n\n"
                f"**建议：** 先不买。把前5篇打磨好（标题+封面+内容），"
                f"等出现一篇自然流量好的帖子，再用薯条加热（¥50-200起），ROI 更高。"
            )
        else:
            st.success(
                f"该博主没有明显推广异常，靠自然流量起号。\n\n"
                f"**建议：暂不买推广**，专注内容质量。"
                f"若3个月后数据仍差，再考虑薯条测试单篇潜力。"
            )

        st.markdown("#### ⑧ 必看对标爆文（直接打开学习）")
        st.caption("学习：标题结构、封面风格、正文格式、标签选择")
        for n, e in sorted(zip(target_notes, t_engs), key=lambda x: x[1], reverse=True)[:5]:
            title = n.get("title") or n.get("desc") or "(无标题)"
            url   = n.get("note_url", "")
            t_dt  = parse_time(n.get("time"))
            ds    = t_dt.strftime("%Y-%m-%d") if t_dt else "未知"
            line  = f"**互动 {e:,}** · {ds} · {title[:45]}"
            if url:
                st.markdown(f"- [{title[:45]}]({url})  |  {ds}  |  互动 {e:,}")
            else:
                st.markdown(f"- {title[:45]}  |  {ds}  |  互动 {e:,}")

    st.stop()

# ── 概览页 ─────────────────────────────────────────────────────
if selected_name == "全部博主":
    st.title(f"{selected_niche} 赛道 · 博主概览")

    cols = st.columns(len(creator_ids))
    for col, cid in zip(cols, creator_ids):
        notes = all_notes[cid]
        engs = [calc_eng(n) for n in notes]
        avg_eng = int(sum(engs) / len(engs)) if engs else 0
        max_eng = max(engs) if engs else 0
        first_t = parse_time(notes[0].get("time")) if notes else None
        avatar = notes[0].get("avatar", "") if notes else ""
        insights = CREATOR_INSIGHTS.get(cid, {})

        with col:
            if avatar:
                st.image(avatar, width=80)
            st.subheader(CREATOR_NAMES[cid])
            st.metric("笔记数", len(notes))
            st.metric("平均互动", f"{avg_eng:,}")
            st.metric("最高单篇", f"{max_eng:,}")
            if first_t:
                st.caption(f"起号时间：{first_t.strftime('%Y-%m')}")
            if insights.get("strategy"):
                st.caption(f"类型：{insights['strategy']}")
            if insights.get("start_difficulty"):
                st.caption(f"起号难度：{insights['start_difficulty']}")

    st.markdown("---")
    st.subheader("平均互动量对比")
    compare = {
        CREATOR_NAMES[cid]: int(sum(calc_eng(n) for n in all_notes[cid]) / len(all_notes[cid]))
        for cid in creator_ids if all_notes[cid]
    }
    st.bar_chart(pd.DataFrame.from_dict({"平均互动": compare}, orient="columns"))

# ── 博主详情页 ─────────────────────────────────────────────────
else:
    cid = next(c for c in creator_ids if CREATOR_NAMES[c] == selected_name)
    notes = all_notes[cid]
    df = to_df(notes)
    insights = CREATOR_INSIGHTS.get(cid, {})

    engs = df["互动总量"].tolist()
    avg_eng = int(sum(engs) / len(engs)) if engs else 0
    top10_threshold = sorted(engs, reverse=True)[max(0, len(engs) // 10)] if len(engs) >= 10 else 0

    # 头部
    avatar = notes[0].get("avatar", "") if notes else ""
    h1, h2 = st.columns([1, 7])
    with h1:
        if avatar:
            st.image(avatar, width=80)
    with h2:
        st.title(selected_name)
        st.caption(
            f"共 {len(notes)} 篇笔记  ·  平均互动 {avg_eng:,}  ·  爆文门槛 (top 10%) {top10_threshold:,}"
        )
        if insights.get("strategy"):
            st.markdown(f"**起号类型：** {insights['strategy']}　　**起号难度：** {insights.get('start_difficulty','')}")

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 起号期", "📈 全期趋势", "🏆 Top 爆文", "💡 内容规律", "⏰ 发布策略"])

    # ── 起号期 ─────────────────────────────────────────────────
    with tab1:
        early = df.head(20).copy()
        early_avg = int(early["互动总量"].mean()) if len(early) else 0
        viral_count = int((early["互动总量"] >= top10_threshold).sum())
        first_t = early.iloc[0]["_time"] if len(early) else None

        c1, c2, c3 = st.columns(3)
        c1.metric("起号期均互动", f"{early_avg:,}")
        c2.metric("起号期爆文数", f"{viral_count} / 20")
        if first_t and first_t != datetime.min:
            c3.metric("起号时间", first_t.strftime("%Y-%m"))

        st.markdown("##### 前20篇互动量")
        st.bar_chart(early.set_index("序号")[["互动总量"]])

        st.markdown("##### 前20篇明细")
        display = early[["序号", "日期", "标题", "互动总量", "点赞", "收藏", "评论"]].copy()
        display.insert(0, "🔥", early["互动总量"].apply(lambda x: "🔥" if x >= top10_threshold else ""))
        st.dataframe(display, use_container_width=True, hide_index=True)

        if insights.get("summary"):
            st.markdown("---")
            st.markdown("##### 起号策略解读")
            st.info(insights["summary"])

    # ── 全期趋势 ───────────────────────────────────────────────
    with tab2:
        st.markdown("##### 每篇互动量（按发布顺序）")
        st.line_chart(df.set_index("序号")[["互动总量"]])

        df2 = df.copy()
        df2["年月"] = df2["_time"].apply(
            lambda t: t.strftime("%Y-%m") if t != datetime.min else "未知"
        )
        monthly = df2.groupby("年月").agg(
            月均互动=("互动总量", "mean"),
            发布篇数=("序号", "count")
        ).reset_index()
        monthly["月均互动"] = monthly["月均互动"].astype(int)

        if len(monthly) > 1:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("##### 月均互动")
                st.bar_chart(monthly.set_index("年月")[["月均互动"]])
            with col_b:
                st.markdown("##### 每月发布篇数")
                st.bar_chart(monthly.set_index("年月")[["发布篇数"]])

        # 互动分布
        st.markdown("##### 互动量分布")
        bins = [0, 1000, 5000, 20000, 50000, 100000, float("inf")]
        labels = ["<1k", "1k-5k", "5k-2w", "2w-5w", "5w-10w", ">10w"]
        bucket = pd.cut(df["互动总量"], bins=bins, labels=labels)
        dist = bucket.value_counts().sort_index()
        st.bar_chart(dist)

    # ── Top 爆文 ───────────────────────────────────────────────
    with tab3:
        top_n = df.nlargest(10, "互动总量")
        for _, row in top_n.iterrows():
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f"**{row['标题']}**")
                st.caption(
                    f"{row['日期']}  ·  互动 {int(row['互动总量']):,}"
                    f"  ·  点赞 {int(row['点赞']):,}"
                    f"  ·  收藏 {int(row['收藏']):,}"
                    f"  ·  评论 {int(row['评论']):,}"
                )
            with c2:
                if row["_url"]:
                    st.link_button("查看原帖", row["_url"])
            st.divider()

    # ── 内容规律 ───────────────────────────────────────────────
    with tab4:
        # 标题公式
        if insights.get("title_formula"):
            st.markdown("##### 标题公式")
            st.success(f"**{insights['title_formula']}**")

        if insights.get("examples"):
            st.markdown("##### 典型爆文标题示例")
            for ex in insights["examples"]:
                st.markdown(f"- {ex}")

        if insights.get("key_pattern"):
            st.markdown("##### 核心规律")
            st.warning(insights["key_pattern"])

        st.markdown("---")

        # 爆文 vs 普通帖高频词对比
        st.markdown("##### 爆文 vs 普通帖标题高频词")
        viral_posts = df[df["互动总量"] >= top10_threshold]["_raw_title"].tolist()
        normal_posts = df[df["互动总量"] < top10_threshold]["_raw_title"].tolist()

        viral_words = Counter()
        for t in viral_posts:
            viral_words.update(extract_words(t))

        normal_words = Counter()
        for t in normal_posts:
            normal_words.update(extract_words(t))

        col_v, col_n = st.columns(2)
        with col_v:
            st.markdown(f"**爆文（{len(viral_posts)}篇）高频词**")
            if viral_words:
                top_v = pd.DataFrame(viral_words.most_common(15), columns=["词", "频次"])
                st.dataframe(top_v, hide_index=True, use_container_width=True)
            else:
                st.caption("暂无足够爆文数据")

        with col_n:
            st.markdown(f"**普通帖（{len(normal_posts)}篇）高频词**")
            if normal_words:
                top_n_words = pd.DataFrame(normal_words.most_common(15), columns=["词", "频次"])
                st.dataframe(top_n_words, hide_index=True, use_container_width=True)
            else:
                st.caption("暂无数据")

        st.markdown("---")
        st.markdown("##### 收藏/点赞比（内容收藏价值）")
        df3 = df.copy()
        df3 = df3[df3["点赞"] > 0].copy()
        df3["收藏点赞比"] = (df3["收藏"] / df3["点赞"]).round(2)
        top_save = df3.nlargest(8, "收藏点赞比")[["日期", "标题", "点赞", "收藏", "收藏点赞比"]]
        st.caption("收藏/点赞比越高，说明内容「干货/合集」属性越强，更容易被保存反复查看")
        st.dataframe(top_save, hide_index=True, use_container_width=True)

    # ── 发布策略 ───────────────────────────────────────────────
    with tab5:
        timed = [(parse_time(n.get("time")), calc_eng(n)) for n in notes]
        timed = [(t, e) for t, e in timed if t is not None]

        if not timed:
            st.info("暂无时间数据")
        else:
            viral_times  = [t for t, e in timed if e >= top10_threshold]
            normal_times = [t for t, e in timed if e < top10_threshold]
            all_times    = [t for t, e in timed]

            # ── 星期分布 ──────────────────────────────────────
            st.markdown("##### 发布日分布（爆文 vs 普通帖）")
            viral_wd  = Counter(t.weekday() for t in viral_times)
            normal_wd = Counter(t.weekday() for t in normal_times)
            wd_df = pd.DataFrame({
                "爆文":  [viral_wd.get(i, 0)  for i in range(7)],
                "普通帖": [normal_wd.get(i, 0) for i in range(7)],
            }, index=WEEKDAY_NAMES)
            st.bar_chart(wd_df)

            # 爆文率最高的日子
            all_wd = Counter(t.weekday() for t in all_times)
            best_days = sorted(
                [(WEEKDAY_NAMES[i], viral_wd.get(i, 0), all_wd.get(i, 0))
                 for i in range(7) if all_wd.get(i, 0) >= 2],
                key=lambda x: x[1] / x[2],
                reverse=True,
            )

            # ── 小时分布 ──────────────────────────────────────
            st.markdown("---")
            st.markdown("##### 发布时段分析（小时维度）")
            hour_eng = defaultdict(list)
            for t, e in timed:
                hour_eng[t.hour].append(e)
            hour_avg   = {h: int(sum(v) / len(v)) for h, v in hour_eng.items()}
            hour_count = {h: len(v) for h, v in hour_eng.items()}

            hour_df = pd.DataFrame({
                "发布篇数": [hour_count.get(h, 0) for h in range(24)],
                "平均互动": [hour_avg.get(h, 0)   for h in range(24)],
            }, index=[f"{h}时" for h in range(24)])

            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown("**各时段发布数量**")
                st.bar_chart(hour_df[["发布篇数"]])
            with col_h2:
                st.markdown("**各时段平均互动**")
                st.bar_chart(hour_df[["平均互动"]])

            # ── 起号期节奏 ────────────────────────────────────
            st.markdown("---")
            st.markdown("##### 起号期发布节奏（前20篇）")
            early_times = sorted(t for t, e in timed[:20])
            if len(early_times) >= 2:
                intervals = [(early_times[i+1] - early_times[i]).days
                             for i in range(len(early_times) - 1)]
                avg_interval  = sum(intervals) / len(intervals)
                posts_per_week = round(7 / avg_interval, 1) if avg_interval > 0 else 0
                span_days = (early_times[-1] - early_times[0]).days

                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("平均发帖间隔", f"{avg_interval:.1f} 天")
                col_f2.metric("折合每周篇数", f"{posts_per_week} 篇")
                col_f3.metric("前20篇跨越", f"{span_days} 天")
            else:
                avg_interval = posts_per_week = None

            # ── 综合建议 ──────────────────────────────────────
            st.markdown("---")
            st.markdown("##### 📋 发布建议（基于该博主数据）")

            lines = []

            if best_days:
                top2 = " / ".join(d[0] for d in best_days[:2])
                lines.append(f"**📅 优先发布日：{top2}** — 该博主爆文在这些天发布比例最高")

            good_hours = sorted(
                [(h, avg) for h, avg in hour_avg.items() if hour_count[h] >= 2],
                key=lambda x: x[1], reverse=True
            )
            if good_hours:
                top_hrs = " / ".join(f"{h}时" for h, _ in good_hours[:3])
                lines.append(f"**⏰ 高互动时段：{top_hrs}** — 这些时段发布的帖子平均互动最高")

            if avg_interval is not None:
                if posts_per_week >= 5:
                    freq_tip = f"高频日更（该博主每 {avg_interval:.1f} 天一篇）"
                elif posts_per_week >= 3:
                    freq_tip = f"每周3-4篇稳定更新（该博主每 {avg_interval:.1f} 天一篇）"
                else:
                    freq_tip = f"每周约 {posts_per_week} 篇（该博主每 {avg_interval:.1f} 天一篇）"
                lines.append(f"**📊 发布频率：{freq_tip}**")

            creator_tips = {
                "5aabcb2d11be105d1a3c83b0": "鱼鱼食记的爆文靠标题情绪，不靠时间点——先把「太太太好吃了啊」系列标题公式练熟，时间选对了但标题平淡也不会爆。",
                "6300e2d8000000001501a130": "桃小姐的高收藏合集内容适合周末发（用户有时间浏览和收藏），工作日发相对简单的单菜内容。",
                "64b3b15c000000001c02b369": "开心一点啦蛰伏一年多才爆——说明在找到「留学生做饭」这个独特角度之前，时间策略意义不大。先确定内容差异化方向。",
                "5940f32182ec3947cc227ebe": "日食记是大号，发布时间高度规律，适合作为参考，但起号期不需要这么严格。",
                "5fc67ee70000000001002f7a": "小辰吾妮是情感类博主，其时间规律对做饭赛道参考价值有限。",
            }
            if cid in creator_tips:
                lines.append(f"**💡 特别提示：** {creator_tips[cid]}")

            lines.append("**🎯 小红书通用高峰：** 早7-9时（上班路上）、午12时（午休）、晚18-21时（饭后）— 建议在这三个窗口内选时发布")

            for line in lines:
                st.markdown(f"- {line}")
