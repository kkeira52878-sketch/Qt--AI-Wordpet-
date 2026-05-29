# -*- coding: utf-8 -*-
"""
单词数据模块
包含50个单词，分为2个单词本，用于测试
"""

# 测试用单词本1：日常词汇
VOCABULARY_BOOK_1 = {
    "name": "日常词汇",
    "words": [
        {
            "id": 1,
            "english": "serendipity",
            "chinese": "意外发现美好事物的运气",
            "pronunciation": "/ˌserənˈdɪpəti/",
            "example": "Finding that bookshop was pure serendipity.",
            "memory": "serendiptiy = seem + ready + pickup，暗示在街上似乎看到准备好被捡起来的东西，结果是宝贝",
            "image": None  # 图片可选
        },
        {
            "id": 2,
            "english": "ephemeral",
            "chinese": "短暂的，转瞬即逝的",
            "pronunciation": "/ɪˈfemərəl/",
            "example": "Fame can be ephemeral in the entertainment industry.",
            "memory": "e-出 + phem-出现 + -al → 出现后就消失 → 短暂的",
            "image": None
        },
        {
            "id": 3,
            "english": "eloquent",
            "chinese": "雄辩的，口才好的",
            "pronunciation": "/ˈeləkwənt/",
            "example": "She gave an eloquent speech that moved the audience.",
            "memory": "e-出 + loqu-说 + -ent → 说出的话很有力量 → 雄辩的",
            "image": None
        },
        {
            "id": 4,
            "english": "meticulous",
            "chinese": "极仔细的，一丝不苟的",
            "pronunciation": "/məˈtɪkjələs/",
            "example": "His meticulous attention to detail ensured quality work.",
            "memory": "meticulus = micro + meticulous，小东西特别仔细",
            "image": None
        },
        {
            "id": 5,
            "english": "ubiquitous",
            "chinese": "无处不在的，普遍存在的",
            "pronunciation": "/juːˈbɪkwɪtəs/",
            "example": "Smartphones have become ubiquitous in modern society.",
            "memory": "ubiquitous = everywhere，像到处飞的精灵",
            "image": None
        },
        {
            "id": 6,
            "english": "resilient",
            "chinese": "有弹性的，能恢复活力的",
            "pronunciation": "/rɪˈzɪliənt/",
            "example": "Children are often more resilient than adults.",
            "memory": "re-再 + silient = silient(安静的) → 再次安静下来 → 恢复平静 → 有弹性的",
            "image": None
        },
        {
            "id": 7,
            "english": "pragmatic",
            "chinese": "务实的，实际的",
            "pronunciation": "/præɡˈmætɪk/",
            "example": "We need a pragmatic approach to solve this problem.",
            "memory": "pragma = practical，做事讲究实际",
            "image": None
        },
        {
            "id": 8,
            "english": "tenacious",
            "chinese": "顽强的，坚持不懈的",
            "pronunciation": "/təˈneɪʃəs/",
            "example": "Her tenacious spirit helped her overcome obstacles.",
            "memory": "ten-拿住 + acious = 紧紧拿住 → 顽强的",
            "image": None
        },
        {
            "id": 9,
            "english": "ambiguous",
            "chinese": "模糊不清的，含糊的",
            "pronunciation": "/æmˈbɪɡjuəs/",
            "example": "The contract contained ambiguous wording.",
            "memory": "ambiguous = aim + big + you + sex，漫无目的地大步走，结果模糊不清",
            "image": None
        },
        {
            "id": 10,
            "english": "profound",
            "chinese": "深刻的，意义深远的",
            "pronunciation": "/prəˈfaʊnd/",
            "example": "The book had a profound impact on my thinking.",
            "memory": "pro-前面 + found-基础 → 有根基的 → 深刻的",
            "image": None
        },
        {
            "id": 11,
            "english": "concise",
            "chinese": "简明的，简洁的",
            "pronunciation": "/kənˈsaɪs/",
            "example": "Please give a concise summary of your proposal.",
            "memory": "con-完全 + cise-切 → 切掉多余的部分 → 简洁的",
            "image": None
        },
        {
            "id": 12,
            "english": "diligent",
            "chinese": "勤勉的，勤奋的",
            "pronunciation": "/ˈdɪlɪdʒənt/",
            "example": "A diligent student always completes homework on time.",
            "memory": "diligently = diary + li(里) + gent，做事像写日记一样认真",
            "image": None
        },
        {
            "id": 13,
            "english": "candid",
            "chinese": "坦白的，直率的",
            "pronunciation": "/ˈkændɪd/",
            "example": "I appreciate your candid feedback on my work.",
            "memory": "candid = can + did，能够直说 → 坦白的",
            "image": None
        },
        {
            "id": 14,
            "english": "coherent",
            "chinese": "连贯的，一致的",
            "pronunciation": "/kəʊˈhɪərənt/",
            "example": "She presented a coherent argument in the debate.",
            "memory": "co-一起 + here-粘着 + nt → 粘在一起 → 连贯的",
            "image": None
        },
        {
            "id": 15,
            "english": "versatile",
            "chinese": "多才多艺的，多功能的",
            "pronunciation": "/ˈvɜːsətaɪl/",
            "example": "He is a versatile actor who can play many roles.",
            "memory": "vers-转 + atile = 随时转向的 → 多才多艺的",
            "image": None
        },
        {
            "id": 16,
            "english": "inevitable",
            "chinese": "不可避免的，必然的",
            "pronunciation": "/ɪnˈevɪtəbl/",
            "example": "Change is inevitable in life.",
            "memory": "in-不 + evit-避免 + able → 不可避免的",
            "image": None
        },
        {
            "id": 19,
            "english": "innovation",
            "chinese": "创新，革新",
            "pronunciation": "/ˌɪnəˈveɪʃn/",
            "example": "Technology innovation drives progress.",
            "memory": "in-进入 + nov-新 + ation → 创新",
            "image": None
        },
        {
            "id": 20,
            "english": "sustainable",
            "chinese": "可持续的",
            "pronunciation": "/səˈsteɪnəbl/",
            "example": "We must develop sustainable practices for the future.",
            "memory": "sustain-支撑 + able → 能够支撑的 → 可持续的",
            "image": None
        },
        {
            "id": 21,
            "english": "paradigm",
            "chinese": "范式，模式",
            "pronunciation": "/ˈpærədaɪm/",
            "example": "This discovery represents a new paradigm in science.",
            "memory": "para-旁边 + digm = diagram → 旁边的图 → 模式",
            "image": None
        },
        {
            "id": 22,
            "english": "leverage",
            "chinese": "利用，杠杆作用",
            "pronunciation": "/ˈliːvərɪdʒ/",
            "example": "We can leverage technology to improve efficiency.",
            "memory": "lev-升 + erage → 升上去 → 杠杆",
            "image": None
        },
        {
            "id": 23,
            "english": "holistic",
            "chinese": "整体的，全面的",
            "pronunciation": "/həˈlɪstɪk/",
            "example": "She takes a holistic approach to healthcare.",
            "memory": "holist = whole + ist → 整体的",
            "image": None
        },
        {
            "id": 24,
            "english": "empathy",
            "chinese": "同理心，移情",
            "pronunciation": "/ˈempəθi/",
            "example": "Good leaders show empathy towards their team.",
            "memory": "em-进入 + pathy-感情 → 进入别人的感情 → 同理心",
            "image": None
        },
        {
            "id": 25,
            "english": "synergy",
            "chinese": "协同作用",
            "pronunciation": "/ˈsɪnədʒi/",
            "example": "The synergy between departments improved productivity.",
            "memory": "syn-一起 + ergy = energy → 一起发力 → 协同",
            "image": None
        }
    ]
}

# 测试用单词本2：学术词汇
VOCABULARY_BOOK_2 = {
    "name": "学术词汇",
    "words": [
        {
            "id": 26,
            "english": "paradigm shift",
            "chinese": "范式转变",
            "pronunciation": "/ˈpærədaɪm ʃɪft/",
            "example": "The internet caused a paradigm shift in communication.",
            "memory": "paradigm(范式) + shift(转变) → 整个模式的转变",
            "image": None
        },
        {
            "id": 27,
            "english": "methodology",
            "chinese": "方法论",
            "pronunciation": "/ˌmeθəˈdɒlədʒi/",
            "example": "The research methodology needs improvement.",
            "memory": "method(方法) + ology(学科) → 关于方法的学科 → 方法论",
            "image": None
        },
        {
            "id": 28,
            "english": "correlation",
            "chinese": "相关性",
            "pronunciation": "/ˌkɒrəˈleɪʃn/",
            "example": "There is a strong correlation between exercise and health.",
            "memory": "cor-一起 + relation(关系) → 共同关联 → 相关性",
            "image": None
        },
        {
            "id": 29,
            "english": "qualitative",
            "chinese": "定性的，质量的",
            "pronunciation": "/ˈkwɒlɪtətɪv/",
            "example": "Qualitative analysis focuses on quality rather than quantity.",
            "memory": "qualit(y) + ative → 关于质量的 → 定性的",
            "image": None
        },
        {
            "id": 30,
            "english": "quantitative",
            "chinese": "定量的，数量的",
            "pronunciation": "/ˈkwɒntɪtətɪv/",
            "example": "Quantitative research uses numerical data.",
            "memory": "quantit(y) + ative → 关于数量的 → 定量的",
            "image": None
        },
        {
            "id": 31,
            "english": "hypothesis",
            "chinese": "假设",
            "pronunciation": "/haɪˈpɒθəsɪs/",
            "example": "The experiment tests a specific hypothesis.",
            "memory": "hypo-下面 + thesis(论文) → 在论文下面放一个假设",
            "image": None
        },
        {
            "id": 32,
            "english": "empirical",
            "chinese": "经验主义的，实证的",
            "pronunciation": "/emˈpɪrɪkəl/",
            "example": "The study provides empirical evidence for the theory.",
            "memory": "empiric = experience + ic → 基于经验的 → 经验主义的",
            "image": None
        },
        {
            "id": 33,
            "english": "triangulation",
            "chinese": "三角定位",
            "pronunciation": "/ˌtraɪæŋɡjʊˈleɪʃn/",
            "example": "The researchers used triangulation to verify findings.",
            "memory": "tri-三 + angul-角 + ation → 变成三个角 → 三角定位",
            "image": None
        },
        {
            "id": 34,
            "english": "generalization",
            "chinese": "概括，归纳",
            "pronunciation": "/ˌdʒenərəlaɪˈzeɪʃn/",
            "example": "Avoid hasty generalization in your analysis.",
            "memory": "general + ize + ation → 变成一般的 → 概括",
            "image": None
        },
        {
            "id": 35,
            "english": "substantiate",
            "chinese": "证实，证明",
            "pronunciation": "/səbˈstænʃieɪt/",
            "example": "You need to substantiate your claims with evidence.",
            "memory": "substant = substance(物质) + iate → 赋予物质 → 证实",
            "image": None
        },
        {
            "id": 36,
            "english": "theoretical",
            "chinese": "理论上的",
            "pronunciation": "/ˌθɪəˈretɪkəl/",
            "example": "This is a theoretical framework, not yet tested.",
            "memory": "theor(y) + et + ical → 关于理论的 → 理论上的",
            "image": None
        },
        {
            "id": 37,
            "english": "annotation",
            "chinese": "注释，注解",
            "pronunciation": "/ˌænəʊˈteɪʃn/",
            "example": "Add annotations to explain complex concepts.",
            "memory": "annotat(e) + ion → 做注解 → 注释",
            "image": None
        },
        {
            "id": 38,
            "english": "synthesis",
            "chinese": "综合，合成",
            "pronunciation": "/ˈsɪnθəsɪs/",
            "example": "The report is a synthesis of multiple studies.",
            "memory": "syn-一起 + thesis-放 → 放在一起 → 综合",
            "image": None
        },
        {
            "id": 39,
            "english": "classification",
            "chinese": "分类",
            "pronunciation": "/ˌklæsɪfɪˈkeɪʃn/",
            "example": "The classification system helps organize data.",
            "memory": "class + ific + ation → 做成等级 → 分类",
            "image": None
        },
        {
            "id": 40,
            "english": "verification",
            "chinese": "验证",
            "pronunciation": "/ˌverɪfɪˈkeɪʃn/",
            "example": "The theory requires experimental verification.",
            "memory": "verif(y) + ic + ation → 确认真实 → 验证",
            "image": None
        },
        {
            "id": 41,
            "english": "rationale",
            "chinese": "理由，基本原理",
            "pronunciation": "/ˌræʃəˈnɑːl/",
            "example": "Explain the rationale behind your decision.",
            "memory": "ration = reason + ale → 原因的理由",
            "image": None
        },
        {
            "id": 42,
            "english": "parameter",
            "chinese": "参数，变量",
            "pronunciation": "/pəˈræmɪtə/",
            "example": "We need to adjust several parameters in the model.",
            "memory": "para-旁边 + meter(测量) → 旁边用来测量的 → 参数",
            "image": None
        },
        {
            "id": 43,
            "english": "coefficient",
            "chinese": "系数",
            "pronunciation": "/ˌkəʊɪˈfɪʃənt/",
            "example": "The coefficient of friction affects movement.",
            "memory": "co-一起 + efficient → 一起有效率的数 → 系数",
            "image": None
        },
        {
            "id": 44,
            "english": "probability",
            "chinese": "概率",
            "pronunciation": "/ˌprɒbəˈbɪləti/",
            "example": "The probability of success is about 70%.",
            "memory": "probable + ility → 可能性的程度 → 概率",
            "image": None
        },
        {
            "id": 45,
            "english": "distribution",
            "chinese": "分布",
            "pronunciation": "/ˌdɪstrɪˈbjuːʃn/",
            "example": "The data shows a normal distribution curve.",
            "memory": "distribute + ion → 分发出去的状态 → 分布",
            "image": None
        },
        {
            "id": 46,
            "english": "regression",
            "chinese": "回归",
            "pronunciation": "/rɪˈɡreʃn/",
            "example": "Regression analysis predicts future trends.",
            "memory": "re-回 + gress-走 + ion → 往回走 → 回归",
            "image": None
        },
        {
            "id": 47,
            "english": "variable",
            "chinese": "变量",
            "pronunciation": "/ˈveəriəbl/",
            "example": "There are many variables to consider in this experiment.",
            "memory": "vari = vary(变化) + able → 会变化的东西 → 变量",
            "image": None
        },
        {
            "id": 48,
            "english": "significance",
            "chinese": "意义，重要性",
            "pronunciation": "/sɪɡˈnɪfɪkəns/",
            "example": "The study has great significance for the field.",
            "memory": "sign + ific + ance → 做出标记的性质 → 意义",
            "image": None
        },
        {
            "id": 49,
            "english": "modification",
            "chinese": "修改，改变",
            "pronunciation": "/ˌmɒdɪfɪˈkeɪʃn/",
            "example": "The plan requires some modifications.",
            "memory": "modif(y) + ic + ation → 改变样式 → 修改",
            "image": None
        },
        {
            "id": 50,
            "english": "implementation",
            "chinese": "实施，执行",
            "pronunciation": "/ˌɪmplɪmenˈteɪʃn/",
            "example": "The implementation phase will begin next month.",
            "memory": "implement + ation → 把工具用起来 → 实施",
            "image": None
        }
    ]
}

# 所有单词本列表
ALL_VOCABULARY_BOOKS = [VOCABULARY_BOOK_1, VOCABULARY_BOOK_2]

# 获取单词本 by 名称
def get_vocabulary_book_by_name(name):
    for book in ALL_VOCABULARY_BOOKS:
        if book["name"] == name:
            return book
    return None

# 获取所有单词本名称
def get_all_book_names():
    return [book["name"] for book in ALL_VOCABULARY_BOOKS]

# 测试用：获取所有单词（合并所有单词本）
def get_all_words():
    all_words = []
    for book in ALL_VOCABULARY_BOOKS:
        all_words.extend(book["words"])
    return all_words